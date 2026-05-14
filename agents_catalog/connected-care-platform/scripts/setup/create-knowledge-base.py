"""Create a Bedrock Knowledge Base with S3 Vectors (no OpenSearch)."""

import boto3
import json
import time

REGION = "us-east-1"
ACCOUNT_ID = boto3.client("sts").get_caller_identity()["Account"]
KB_NAME = "connected-care-clinical-guidelines"
S3_DATA_BUCKET = f"connected-care-guidelines-{ACCOUNT_ID}"
S3_PREFIX = "guidelines/"
VECTOR_BUCKET_NAME = "connected-care-vectors"
INDEX_NAME = "clinical-guidelines-index"
ROLE_NAME = "ConnectedCareKBRole"

s3v = boto3.client("s3vectors", region_name=REGION)
bedrock = boto3.client("bedrock-agent", region_name=REGION)
iam = boto3.client("iam")

# 1. Create S3 Vector Bucket
print("Creating S3 Vector Bucket...")
try:
    s3v.create_vector_bucket(vectorBucketName=VECTOR_BUCKET_NAME)
    print(f"  Created: {VECTOR_BUCKET_NAME}")
except Exception as e:
    if "already exists" in str(e).lower() or "BucketAlreadyExists" in str(e):
        print(f"  Exists: {VECTOR_BUCKET_NAME}")
    else:
        print(f"  Error: {e}")

# Wait for bucket
time.sleep(3)

# Get vector bucket ARN
vb = s3v.get_vector_bucket(vectorBucketName=VECTOR_BUCKET_NAME)
vector_bucket_arn = vb["vectorBucket"]["vectorBucketArn"]
print(f"  ARN: {vector_bucket_arn}")

# 2. Create Index (1024 dimensions for Titan Embed V2)
print("Creating vector index...")
try:
    s3v.create_index(
        vectorBucketName=VECTOR_BUCKET_NAME,
        indexName=INDEX_NAME,
        dimension=1024,
        distanceMetric="cosine",
        dataType="float32",
    )
    print(f"  Created: {INDEX_NAME}")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"  Exists: {INDEX_NAME}")
    else:
        print(f"  Error: {e}")

# Wait for index to be ready
print("Waiting for index...")
for i in range(20):
    try:
        idx = s3v.get_index(vectorBucketName=VECTOR_BUCKET_NAME, indexName=INDEX_NAME)
        status = idx["index"]["status"]
        if status == "ACTIVE":
            print(f"  Index ACTIVE")
            index_arn = idx["index"]["indexArn"]
            print(f"  Index ARN: {index_arn}")
            break
        print(f"  Status: {status} ({i+1}/20)")
    except Exception as e:
        print(f"  Waiting... {e}")
    time.sleep(5)

# 3. Update IAM role with S3 Vectors permissions
print("Updating IAM role...")
policy_doc = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"],
         "Resource": [f"arn:aws:s3:::{S3_DATA_BUCKET}", f"arn:aws:s3:::{S3_DATA_BUCKET}/*"]},
        {"Effect": "Allow", "Action": ["bedrock:InvokeModel"], "Resource": ["*"]},
        {"Effect": "Allow", "Action": ["s3vectors:QueryVectors", "s3vectors:PutVectors",
                                        "s3vectors:GetVectors", "s3vectors:DeleteVectors",
                                        "s3vectors:ListVectors"],
         "Resource": ["*"]},
    ],
}
iam.put_role_policy(RoleName=ROLE_NAME, PolicyName="ConnectedCareKBPolicy",
                    PolicyDocument=json.dumps(policy_doc))
print("  Role updated")
time.sleep(5)

# 4. Create Knowledge Base
role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/{ROLE_NAME}"
print("Creating Knowledge Base...")

kb_id = None
kbs = bedrock.list_knowledge_bases()
for kb in kbs.get("knowledgeBaseSummaries", []):
    if kb["name"] == KB_NAME:
        kb_id = kb["knowledgeBaseId"]
        print(f"  Found existing: {kb_id}")
        break

if not kb_id:
    kb_response = bedrock.create_knowledge_base(
        name=KB_NAME,
        description="37K clinical practice guidelines from WHO, CDC, NICE, PubMed",
        roleArn=role_arn,
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0",
            },
        },
        storageConfiguration={
            "type": "S3_VECTORS",
            "s3VectorsConfiguration": {
                "vectorBucketArn": vector_bucket_arn,
                "indexArn": index_arn,
            },
        },
    )
    kb_id = kb_response["knowledgeBase"]["knowledgeBaseId"]
    print(f"  Created: {kb_id}")

# Wait for KB active
print("Waiting for KB...")
for i in range(30):
    kb = bedrock.get_knowledge_base(knowledgeBaseId=kb_id)
    status = kb["knowledgeBase"]["status"]
    if status == "ACTIVE":
        print(f"  KB ACTIVE")
        break
    print(f"  Status: {status}")
    time.sleep(10)

# 5. Create data source + start ingestion
print("Creating data source...")
ds_id = None
try:
    sources = bedrock.list_data_sources(knowledgeBaseId=kb_id)
    for s in sources.get("dataSourceSummaries", []):
        ds_id = s["dataSourceId"]
        print(f"  Found existing: {ds_id}")
        break
except Exception:
    pass

if not ds_id:
    ds_response = bedrock.create_data_source(
        knowledgeBaseId=kb_id,
        name="clinical-guidelines-s3",
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration": {
                "bucketArn": f"arn:aws:s3:::{S3_DATA_BUCKET}",
                "inclusionPrefixes": [S3_PREFIX],
            },
        },
    )
    ds_id = ds_response["dataSource"]["dataSourceId"]
    print(f"  Created: {ds_id}")

print("Starting ingestion (37K docs — this takes a while)...")
ingestion = bedrock.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)
job_id = ingestion["ingestionJob"]["ingestionJobId"]
print(f"  Job: {job_id}")

print(f"\n{'='*50}")
print(f"KNOWLEDGE_BASE_ID: {kb_id}")
print(f"{'='*50}")
print(f"\nDeploy:")
print(f"  npx cdk deploy ConnectedCareAgentCoreStack \\")
print(f"    -c memoryId='ConnectedCareMemory-55HxcwAdJA' \\")
print(f"    -c knowledgeBaseId='{kb_id}' \\")
print(f"    --require-approval never")
print(f"\nCheck ingestion:")
print(f"  aws bedrock-agent get-ingestion-job --knowledge-base-id {kb_id} --data-source-id {ds_id} --ingestion-job-id {job_id}")
