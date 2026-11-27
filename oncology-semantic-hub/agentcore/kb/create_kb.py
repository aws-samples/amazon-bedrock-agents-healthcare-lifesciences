#!/usr/bin/env python3
"""Create (or delete) the Oncology Semantic Hub hybrid-search knowledge base.

Driver around `knowledge_base.KnowledgeBasesForAmazonBedrock`:
  1. create/retrieve a Bedrock KB (S3 Vectors + Titan v2) with a dedicated corpus bucket,
  2. upload the local corpus (built by build_corpus.py) to that bucket,
  3. run an ingestion job,
  4. store `kb_id` / `ds_id` in SSM for the L3 agent to read.

Dedicated corpus bucket (not the shared data lake) so the data source ingests only our documents.

Usage:
    python agentcore/kb/create_kb.py                 # create + ingest + SSM
    python agentcore/kb/create_kb.py --delete         # tear down KB + vectors + IAM
"""
import argparse
import sys
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).parent))
from knowledge_base import KnowledgeBasesForAmazonBedrock  # noqa: E402

KB_NAME = "oncology-semantic-hub-kb"
KB_DESCRIPTION = ("Oncology Semantic Hub hybrid-search corpus: TCGA project descriptions + curated "
                  "PubMed abstracts (glioblastoma/EGFR + immune-checkpoint resistance).")
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
SSM_KB_ID = "/app/oncology-hub/knowledge_base/kb_id"
SSM_DS_ID = "/app/oncology-hub/knowledge_base/ds_id"


def main():
    ap = argparse.ArgumentParser(description="Create/delete the hybrid-search KB.")
    ap.add_argument("--region", default=None)
    ap.add_argument("--corpus", default=str(Path(__file__).parent / "corpus"))
    ap.add_argument("--kb-name", default=KB_NAME)
    ap.add_argument("--suffix", default="v1")
    ap.add_argument("--delete", action="store_true", help="tear down the KB and all its resources")
    args = ap.parse_args()

    kb = KnowledgeBasesForAmazonBedrock(suffix=args.suffix, region_name=args.region)
    region = kb.region_name
    ssm = boto3.client("ssm", region_name=region)
    bucket = f"{args.kb_name}-corpus-{kb.account_number}-{region}"

    if args.delete:
        kb.delete_kb(args.kb_name)
        for name in (SSM_KB_ID, SSM_DS_ID):
            try:
                ssm.delete_parameter(Name=name)
            except ssm.exceptions.ParameterNotFound:
                pass
        print("Deleted SSM parameters. (Corpus S3 bucket left intact.)")
        return

    corpus = Path(args.corpus)
    docs = list(corpus.glob("*.txt"))
    if not docs:
        print(f"ERROR: no corpus documents in {corpus} — run build_corpus.py first", file=sys.stderr)
        sys.exit(1)
    print(f"Corpus: {len(docs)} documents in {corpus}")
    print(f"Region: {region}  Account: {kb.account_number}  Bucket: {bucket}")

    kb_id, ds_id = kb.create_or_retrieve_knowledge_base(
        args.kb_name, KB_DESCRIPTION, data_bucket_name=bucket, embedding_model=EMBEDDING_MODEL)
    print(f"KB: {kb_id}  DataSource: {ds_id}")

    kb.upload_directory(str(corpus), bucket)
    print("Starting ingestion job ...")
    job = kb.synchronize_data(kb_id, ds_id)

    ssm.put_parameter(Name=SSM_KB_ID, Value=kb_id, Type="String", Overwrite=True,
                      Description="Oncology hub hybrid-search KB id")
    ssm.put_parameter(Name=SSM_DS_ID, Value=ds_id, Type="String", Overwrite=True,
                      Description="Oncology hub hybrid-search data source id")
    print(f"\nStored SSM {SSM_KB_ID}={kb_id}")
    print(f"Ingestion status: {job['status']}")
    if job["status"] != "COMPLETE":
        sys.exit(2)


if __name__ == "__main__":
    main()
