# Variant S3 Tables Pipeline — Deployment Guide

## Overview

Automated pipeline that annotates VCF files with VEP (Ensembl Variant Effect Predictor) via HealthOmics, then loads the annotated variants into S3 Tables (Apache Iceberg) for querying via Athena and a Strands AI agent.

```
VCF Upload → S3 → Trigger Lambda → HealthOmics VEP → EventBridge → Import Lambda → S3 Tables → Athena → AI Agent
```

## Prerequisites

- AWS CLI configured with appropriate permissions
- Docker (for building container images)
- Python 3.10+
- Access to: S3, S3 Tables, HealthOmics, Lambda, ECR, EventBridge, DynamoDB, IAM, Athena

---

## Step 1: Deploy Prerequisites (`deploy-unified.sh`)

Sets up VEP cache, Docker image, ClinVar data, and HealthOmics reference store.

```bash
cd variant-s3tables-interpreter-agent-main
chmod +x deploy-unified.sh
./deploy-unified.sh
```

This script:
- Pulls the VEP Docker image (`ensemblorg/ensembl-vep:release_113.4`) with `--platform linux/amd64`
- Pushes it to ECR
- Downloads and uploads VEP cache files to S3
- Creates the HealthOmics reference store
- Generates `deployment-config.env`

**Time:** ~30-60 minutes (VEP cache download is large)

---

## Step 2: Deploy Orchestration (`deploy-orchestration.sh`)

Creates the workflow trigger Lambda, EventBridge rules, S3 notifications, DynamoDB table, and IAM roles.

```bash
chmod +x deploy-orchestration.sh
./deploy-orchestration.sh
```

This script creates:
- **Workflow Trigger Lambda** (`genomics-vep-s3tables-workflow-trigger`) — zip-based, triggers on VCF upload to S3
- **EventBridge Rule** (`genomics-vep-s3tables-workflow-completion`) — catches HealthOmics run completion
- **S3 Tables Import Lambda** (`genomics-vep-s3tables-s3tables-import`) — initially zip-based (replaced in Step 3)
- **DynamoDB Table** (`genomics-vep-s3tables-dynamotable`) — tracks processing status
- **IAM Roles** with S3, HealthOmics, DynamoDB, and S3 Tables permissions

**Time:** ~5 minutes

---

## Step 3: Deploy Container-Based Import Lambda (`deploy-s3tables-import-lambda.sh`)

Replaces the zip-based import Lambda with a container-based version that has pyiceberg, pyarrow, and smart_open for streaming VCF processing.

```bash
# Authenticate to public ECR (needed for Lambda base image)
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws

chmod +x deploy-s3tables-import-lambda.sh
./deploy-s3tables-import-lambda.sh
```

This script:
1. Creates ECR repo `genomics-s3tables-import`
2. Builds container image (amd64, `--provenance=false` for Lambda compatibility)
3. Pushes to ECR
4. Deletes the old zip-based Lambda and recreates as container-based
5. Re-adds EventBridge invoke permission

**Lambda configuration:** 10 GB memory, 15-minute timeout, container image

**Time:** ~5 minutes

---

## Step 4: Verify IAM Permissions

The import Lambda role needs these S3 Tables permissions. Verify they're present:

```bash
aws iam get-role-policy \
  --role-name genomics-vep-s3tables-lambda-execution-role-v3 \
  --policy-name GenomicsLambdaPolicy \
  --query 'PolicyDocument.Statement[?Action[?contains(@,`s3tables`)]]' \
  --output json
```

Required `s3tables:*` actions:
- `GetTableBucket`, `GetTable`, `PutTableData`, `GetTableData`, `ListTables`, `ListNamespaces`
- `CreateNamespace`, `GetNamespace`, `CreateTable`, `GetTableMetadataLocation`, `UpdateTableMetadataLocation`

If any are missing, update the inline policy via the IAM console or CLI.

---

## Step 5: Test the Pipeline

### 5a. Upload a VCF to trigger the pipeline

```bash
source deployment-config.env

aws s3 cp your-sample.vcf.gz \
  s3://${VCF_INPUT_BUCKET}/samples/your-sample.vcf.gz
```

This triggers: S3 notification → Trigger Lambda → HealthOmics VEP → EventBridge → Import Lambda → S3 Tables.

### 5b. Monitor progress

```bash
# Check HealthOmics run
aws omics list-runs --region us-west-2 --query 'items[0]' --output table

# Check DynamoDB status
aws dynamodb scan --table-name genomics-vep-s3tables-dynamotable --region us-west-2

# Check import Lambda logs
aws logs tail /aws/lambda/genomics-vep-s3tables-s3tables-import --follow --region us-west-2
```

### 5c. Manual test invoke (skip VEP, test import only)

```bash
aws lambda invoke \
  --function-name genomics-vep-s3tables-s3tables-import \
  --invocation-type Event \
  --cli-binary-format raw-in-base64-out \
  --payload '{"detail-type":"Run Status Change","source":"aws.omics","detail":{"runId":"YOUR_RUN_ID","status":"COMPLETED","runOutputUri":"s3://YOUR_OUTPUT_BUCKET/output/path","workflowId":"YOUR_WORKFLOW_ID"}}' \
  --region us-west-2 /tmp/response.json
```

### 5d. Query data in Athena

```sql
SELECT COUNT(*) as total_rows, COUNT(DISTINCT sample_name) as samples
FROM variant_db_3.genomic_variants_fixed;

SELECT chrom, pos, ref, alt, genotype, info
FROM variant_db_3.genomic_variants_fixed
WHERE sample_name = 'HG00096'
LIMIT 10;
```

---

## Step 6: Deploy AI Agent (`deploy-agent.sh`)

```bash
chmod +x deploy-agent.sh
./deploy-agent.sh
source .agent-venv/bin/activate && source .agent-config
streamlit run app.py
```

---

## Key Configuration Files

| File | Purpose |
|------|---------|
| `deployment-config.env` | All resource IDs — sourced by every deploy script |
| `orchestration-config.env` | Orchestration layer ARNs |
| `.agent-config` | Agent environment variables |

---

## Streaming VCF Processing

The import Lambda uses streaming to handle large multi-sample VCFs within Lambda's 10 GB memory limit:

- **smart_open** for true S3 streaming (no full-file download)
- **Dynamic chunk sizing**: `BATCH_SIZE // num_vcf_columns` (min 10,000 rows)
- **Per-sample processing**: each chunk is written to Iceberg one sample at a time
- **table.refresh()** before each Iceberg append to avoid commit conflicts

Performance on 1000 Genomes chr22 (177MB, 2504 samples, 1M variants):
- Duration: ~9 minutes
- Memory: ~2.5 GB of 10 GB
- 106 Iceberg commits

---

## Troubleshooting

### Import Lambda OOM
Increase memory (max 10,240 MB). If still OOM, reduce `BATCH_SIZE` in `load_vcf_schema3.py`.

### Iceberg CommitFailedException
The retry logic handles this automatically (up to 10 retries with `table.refresh()`). If persistent, check for concurrent writers.

### Docker build 403 on public ECR
```bash
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
```

### Lambda image manifest not supported
Ensure `--provenance=false` is in the `docker build` command (already in the deploy script).

### VEP workflow fails with exit code 255
Ensure the ECR image is `linux/amd64`, not `linux/arm64`. See `deploy-unified.sh`.

---

**Last Updated:** April 12, 2026
