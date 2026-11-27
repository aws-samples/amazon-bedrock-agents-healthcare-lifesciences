#!/usr/bin/env python3
"""Knowledge Bases for Amazon Bedrock — helper (S3 Vectors + Titan v2).

Adapted from `agentcore_template/prerequisite/knowledge_base.py`. Creates (or retrieves) a
customer-managed Bedrock Knowledge Base backed by **Amazon S3 Vectors** (serverless; no OpenSearch
to run) with **Titan Text Embeddings v2** (1024-dim, cosine), an S3 data source, IAM execution role
+ policies, ingestion, and clean deletion.

Differences from the template:
  * No `retrying`/`yaml` dependencies (manual retry loop; driver passes config directly).
  * Stable `suffix` so re-runs retrieve existing resources instead of duplicating them.

This module is a library used by `create_kb.py`; it is not a CLI.
"""
import json
import os
import time
import boto3

VALID_EMBEDDING_MODELS = [
    "cohere.embed-multilingual-v3",
    "cohere.embed-english-v3",
    "amazon.titan-embed-text-v1",
    "amazon.titan-embed-text-v2:0",
]

# Vector dimension per embedding model — the S3 Vectors index dimension MUST match (review fix M2).
EMBED_DIMS = {
    "cohere.embed-multilingual-v3": 1024,
    "cohere.embed-english-v3": 1024,
    "amazon.titan-embed-text-v1": 1536,
    "amazon.titan-embed-text-v2:0": 1024,
}


def _sleep(seconds: int):
    time.sleep(seconds)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)


class KnowledgeBasesForAmazonBedrock:
    """Create / ingest / delete a Bedrock KB backed by S3 Vectors."""

    def __init__(self, suffix: str = "v1", region_name: str | None = None):
        session = boto3.session.Session()
        self.region_name = region_name or session.region_name or "us-west-2"
        self.suffix = suffix
        self.iam_client = session.client("iam", region_name=self.region_name)
        self.account_number = boto3.client(
            "sts", region_name=self.region_name).get_caller_identity()["Account"]
        self.s3_vectors_client = session.client("s3vectors", region_name=self.region_name)
        self.s3_client = session.client("s3", region_name=self.region_name)
        self.bedrock_agent_client = session.client("bedrock-agent", region_name=self.region_name)
        self.data_bucket_name = None
        self.vector_bucket_name = None
        self.index_name = None

    # ── top-level create/retrieve ──────────────────────────────────────────────
    def create_or_retrieve_knowledge_base(
        self,
        kb_name: str,
        kb_description: str,
        data_bucket_name: str,
        embedding_model: str = "amazon.titan-embed-text-v2:0",
        inclusion_prefixes: list | None = None,
    ):
        """Return (kb_id, ds_id), creating all prerequisites if the KB does not yet exist."""
        if embedding_model not in VALID_EMBEDDING_MODELS:
            raise ValueError(f"embedding_model must be one of {VALID_EMBEDDING_MODELS}")

        # Retrieve if it already exists (idempotent).
        for kb in self.bedrock_agent_client.list_knowledge_bases(maxResults=100)["knowledgeBaseSummaries"]:
            if kb["name"] == kb_name:
                kb_id = kb["knowledgeBaseId"]
                ds = self.bedrock_agent_client.list_data_sources(
                    knowledgeBaseId=kb_id, maxResults=100)["dataSourceSummaries"]
                ds_id = ds[0]["dataSourceId"] if ds else None
                self.data_bucket_name = data_bucket_name
                print(f"KB '{kb_name}' already exists → {kb_id} (ds {ds_id})")
                return kb_id, ds_id

        print(f"Creating KB '{kb_name}' ...")
        role_name = f"AmazonBedrockExecutionRoleForKB_{self.suffix}"
        fm_policy = f"AmazonBedrockFMPolicyForKB_{self.suffix}"
        s3_policy = f"AmazonBedrockS3PolicyForKB_{self.suffix}"
        s3v_policy = f"AmazonBedrockS3VectorsPolicyForKB_{self.suffix}"
        vector_bucket = f"{kb_name}-vec-{self.suffix}"
        index_name = f"{kb_name}-idx-{self.suffix}"

        print(f"[1/5] data bucket {data_bucket_name}")
        self.create_s3_bucket(data_bucket_name)
        print(f"[2/5] execution role {role_name}")
        role = self.create_execution_role(embedding_model, data_bucket_name, fm_policy, s3_policy, role_name)
        _sleep(10)
        print("[3/5] S3 Vectors bucket + index")
        vec_arn, idx_arn = self.create_s3_vectors_bucket_and_index(
            vector_bucket, index_name, dimension=EMBED_DIMS[embedding_model])
        print("[4/5] S3 Vectors policy")
        self.create_s3_vectors_policy(s3v_policy, vec_arn, role)
        print("[5/5] knowledge base + data source")
        kb, ds = self.create_knowledge_base(
            vec_arn, idx_arn, data_bucket_name, embedding_model, kb_name, kb_description, role,
            inclusion_prefixes)
        _sleep(30)
        return kb["knowledgeBaseId"], ds["dataSourceId"]

    # ── S3 data bucket ─────────────────────────────────────────────────────────
    def create_s3_bucket(self, bucket_name: str):
        self.data_bucket_name = bucket_name
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            print(f"    bucket {bucket_name} exists")
        except Exception:  # noqa: BLE001 — not found or no access; try to create/own it
            print(f"    creating bucket {bucket_name}")
            try:
                if self.region_name == "us-east-1":
                    self.s3_client.create_bucket(Bucket=bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": self.region_name})
            except self.s3_client.exceptions.BucketAlreadyOwnedByYou:
                print(f"    bucket {bucket_name} already owned by you")
        # Security: block all public access on the corpus bucket (idempotent).
        self.s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True, "IgnorePublicAcls": True,
                "BlockPublicPolicy": True, "RestrictPublicBuckets": True})

    def upload_directory(self, path: str, bucket_name: str, prefix: str = ""):
        count = 0
        for root, _, files in os.walk(path):
            for file in files:
                local = os.path.join(root, file)
                key = f"{prefix}{file}" if prefix else file
                self.s3_client.upload_file(local, bucket_name, key)
                count += 1
        print(f"    uploaded {count} files to s3://{bucket_name}/{prefix}")
        return count

    # ── IAM ────────────────────────────────────────────────────────────────────
    def create_execution_role(self, embedding_model, bucket_name, fm_policy_name,
                              s3_policy_name, role_name):
        fm_doc = {"Version": "2012-10-17", "Statement": [{
            "Effect": "Allow", "Action": ["bedrock:InvokeModel"],
            "Resource": [f"arn:aws:bedrock:{self.region_name}::foundation-model/{embedding_model}"]}]}
        s3_doc = {"Version": "2012-10-17", "Statement": [{
            "Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": [f"arn:aws:s3:::{bucket_name}", f"arn:aws:s3:::{bucket_name}/*"],
            "Condition": {"StringEquals": {"aws:ResourceAccount": self.account_number}}}]}
        trust = {"Version": "2012-10-17", "Statement": [{
            "Effect": "Allow", "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {"StringEquals": {"aws:SourceAccount": self.account_number},
                          "ArnLike": {"aws:SourceArn":
                                      f"arn:aws:bedrock:{self.region_name}:{self.account_number}:knowledge-base/*"}}}]}
        fm_arn = self._ensure_policy(fm_policy_name, fm_doc, "FM access")
        s3_arn = self._ensure_policy(s3_policy_name, s3_doc, "S3 read")
        try:
            role = self.iam_client.create_role(
                RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust),
                Description="Bedrock KB execution role (S3 Vectors)", MaxSessionDuration=3600)
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            role = self.iam_client.get_role(RoleName=role_name)
        for arn in (fm_arn, s3_arn):
            self.iam_client.attach_role_policy(RoleName=role["Role"]["RoleName"], PolicyArn=arn)
        return role

    def _ensure_policy(self, name, document, description):
        try:
            return self.iam_client.create_policy(
                PolicyName=name, PolicyDocument=json.dumps(document),
                Description=description)["Policy"]["Arn"]
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            return f"arn:aws:iam::{self.account_number}:policy/{name}"

    # ── S3 Vectors ───────────────────────────────────────────────────────────────
    def create_s3_vectors_bucket_and_index(self, vector_bucket_name, index_name, dimension=1024):
        self.vector_bucket_name = vector_bucket_name
        self.index_name = index_name
        try:
            self.s3_vectors_client.create_vector_bucket(
                vectorBucketName=vector_bucket_name,
                encryptionConfiguration={"sseType": "AES256"})
            vec_arn = self.s3_vectors_client.get_vector_bucket(
                vectorBucketName=vector_bucket_name)["vectorBucket"]["vectorBucketArn"]
            print(f"    created vector bucket {vector_bucket_name}")
        except self.s3_vectors_client.exceptions.ConflictException:
            # Idempotent recovery: read the real ARN from the API (do not synthesize).
            vec_arn = self.s3_vectors_client.get_vector_bucket(
                vectorBucketName=vector_bucket_name)["vectorBucket"]["vectorBucketArn"]
            print(f"    vector bucket {vector_bucket_name} exists")
        try:
            self.s3_vectors_client.create_index(
                vectorBucketName=vector_bucket_name, indexName=index_name,
                dataType="float32", dimension=dimension, distanceMetric="cosine",
                metadataConfiguration={"nonFilterableMetadataKeys": ["AMAZON_BEDROCK_TEXT"]})
            _sleep(10)
            idx_arn = self.s3_vectors_client.get_index(
                vectorBucketName=vector_bucket_name, indexName=index_name)["index"]["indexArn"]
            print(f"    created index {index_name} (dim={dimension})")
        except self.s3_vectors_client.exceptions.ConflictException:
            idx_arn = self.s3_vectors_client.get_index(
                vectorBucketName=vector_bucket_name, indexName=index_name)["index"]["indexArn"]
            print(f"    index {index_name} exists")
        return vec_arn, idx_arn

    def create_s3_vectors_policy(self, policy_name, vector_bucket_arn, role):
        doc = {"Version": "2012-10-17", "Statement": [{
            "Sid": "S3VectorsPermissions", "Effect": "Allow",
            "Action": ["s3vectors:GetIndex", "s3vectors:QueryVectors", "s3vectors:PutVectors",
                       "s3vectors:GetVectors", "s3vectors:DeleteVectors"],
            "Resource": f"{vector_bucket_arn}/index/*",
            "Condition": {"StringEquals": {"aws:ResourceAccount": self.account_number}}}]}
        arn = self._ensure_policy(policy_name, doc, "S3 Vectors access")
        self.iam_client.attach_role_policy(RoleName=role["Role"]["RoleName"], PolicyArn=arn)

    # ── KB + data source ──────────────────────────────────────────────────────────
    def create_knowledge_base(self, vec_arn, idx_arn, bucket_name, embedding_model,
                              kb_name, kb_description, role, inclusion_prefixes=None):
        emb_arn = f"arn:aws:bedrock:{self.region_name}::foundation-model/{embedding_model}"
        chunking = {"chunkingStrategy": "FIXED_SIZE",
                    "fixedSizeChunkingConfiguration": {"maxTokens": 512, "overlapPercentage": 20}}
        s3_conf = {"bucketArn": f"arn:aws:s3:::{bucket_name}"}
        if inclusion_prefixes:
            s3_conf["inclusionPrefixes"] = inclusion_prefixes

        kb = None
        last = None
        for attempt in range(7):  # IAM/role propagation can lag KB creation
            try:
                kb = self.bedrock_agent_client.create_knowledge_base(
                    name=kb_name, description=kb_description, roleArn=role["Role"]["Arn"],
                    knowledgeBaseConfiguration={
                        "type": "VECTOR",
                        "vectorKnowledgeBaseConfiguration": {"embeddingModelArn": emb_arn}},
                    storageConfiguration={
                        "type": "S3_VECTORS",
                        "s3VectorsConfiguration": {"vectorBucketArn": vec_arn, "indexArn": idx_arn}},
                )["knowledgeBase"]
                break
            except self.bedrock_agent_client.exceptions.ConflictException:
                for k in self.bedrock_agent_client.list_knowledge_bases(
                        maxResults=100)["knowledgeBaseSummaries"]:
                    if k["name"] == kb_name:
                        kb = self.bedrock_agent_client.get_knowledge_base(
                            knowledgeBaseId=k["knowledgeBaseId"])["knowledgeBase"]
                break
            except Exception as e:  # noqa: BLE001 — retry transient validation on fresh role
                last = e
                _sleep(5 * (attempt + 1))
        if kb is None:
            raise RuntimeError(f"create_knowledge_base failed: {last}")

        try:
            ds = self.bedrock_agent_client.create_data_source(
                name=kb_name, description=kb_description, knowledgeBaseId=kb["knowledgeBaseId"],
                dataDeletionPolicy="RETAIN",
                dataSourceConfiguration={"type": "S3", "s3Configuration": s3_conf},
                vectorIngestionConfiguration={"chunkingConfiguration": chunking},
            )["dataSource"]
        except self.bedrock_agent_client.exceptions.ConflictException:
            ds_id = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=kb["knowledgeBaseId"], maxResults=100)["dataSourceSummaries"][0]["dataSourceId"]
            ds = self.bedrock_agent_client.get_data_source(
                dataSourceId=ds_id, knowledgeBaseId=kb["knowledgeBaseId"])["dataSource"]
        return kb, ds

    # ── ingestion ──────────────────────────────────────────────────────────────
    def synchronize_data(self, kb_id, ds_id, timeout: int = 1800):
        deadline = time.time() + timeout
        while self.bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=kb_id)["knowledgeBase"]["status"] in ("CREATING", "UPDATING", "DELETING"):
            if time.time() > deadline:
                raise TimeoutError(f"KB {kb_id} not ready within {timeout}s")
            _sleep(5)
        job = self.bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=kb_id, dataSourceId=ds_id)["ingestionJob"]
        while job["status"] not in ("COMPLETE", "FAILED"):
            if time.time() > deadline:
                raise TimeoutError(f"ingestion job {job['ingestionJobId']} not done within {timeout}s")
            _sleep(5)
            job = self.bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=kb_id, dataSourceId=ds_id,
                ingestionJobId=job["ingestionJobId"])["ingestionJob"]
        print(f"    ingestion {job['status']}: {json.dumps(job.get('statistics', {}), default=str)}")
        return job

    def get_kb(self, kb_id):
        return self.bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)

    # ── deletion (cleanup) ─────────────────────────────────────────────────────
    def delete_kb(self, kb_name):
        kb_id = None
        for kb in self.bedrock_agent_client.list_knowledge_bases(maxResults=100)["knowledgeBaseSummaries"]:
            if kb["name"] == kb_name:
                kb_id = kb["knowledgeBaseId"]
        if not kb_id:
            print(f"KB '{kb_name}' not found")
            return
        details = self.bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]
        role_name = details["roleArn"].split("/")[-1]
        store = details["storageConfiguration"]["s3VectorsConfiguration"]
        for ds in self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=kb_id, maxResults=100)["dataSourceSummaries"]:
            self.bedrock_agent_client.delete_data_source(
                dataSourceId=ds["dataSourceId"], knowledgeBaseId=kb_id)
        self.bedrock_agent_client.delete_knowledge_base(knowledgeBaseId=kb_id)
        try:
            self.s3_vectors_client.delete_index(indexArn=store["indexArn"])
            self.s3_vectors_client.delete_vector_bucket(vectorBucketArn=store["vectorBucketArn"])
        except Exception as e:  # noqa: BLE001
            print(f"    vector cleanup warning: {e}")
        self._delete_role(role_name)
        print(f"Deleted KB '{kb_name}' ({kb_id})")

    def _delete_role(self, role_name):
        try:
            for p in self.iam_client.list_attached_role_policies(
                    RoleName=role_name)["AttachedPolicies"]:
                self.iam_client.detach_role_policy(RoleName=role_name, PolicyArn=p["PolicyArn"])
                self.iam_client.delete_policy(PolicyArn=p["PolicyArn"])
            self.iam_client.delete_role(RoleName=role_name)
        except Exception as e:  # noqa: BLE001
            print(f"    role cleanup warning: {e}")
