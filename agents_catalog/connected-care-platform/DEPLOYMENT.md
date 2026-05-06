# Deployment Guide

Deploy the Connected Care Platform to your own AWS account.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| AWS CLI | Configured with credentials (`aws sts get-caller-identity`) |
| Node.js | 18+ |
| Python | 3.12+ |
| Docker | Running |
| Bedrock access | Claude Sonnet/Opus + Titan Embed V2 enabled in your target region |
| CDK bootstrap | `cdk bootstrap aws://ACCOUNT_ID/REGION` |
| Python packages | `pip install bedrock-agentcore boto3` |

## Quick Start (Default)

```bash
git clone <repo-url>
cd connected-care-platform
./scripts/deploy.sh
```

This deploys with prefix `connected-care` in `us-east-1`. Open the printed URL, create an account, sign in.

## Custom Deployment

```bash
./scripts/deploy.sh --prefix=acme-health --region=us-west-2
```

| Flag | Default | Description |
|------|---------|-------------|
| `--prefix=NAME` | `connected-care` | Resource naming prefix (tables, functions, buckets) |
| `--region=REGION` | `us-east-1` | AWS region |
| `--with-memory` | off | Enable AgentCore Memory (conversation continuity) |
| `--with-kb` | off | Enable Knowledge Base (37K clinical guidelines) |
| `--full` | off | Enable both Memory + KB |

Example full deployment with custom prefix:

```bash
./scripts/deploy.sh --full --prefix=mercy-hospital --region=eu-west-1
```

## What Gets Deployed

- 7 CDK stacks (DynamoDB tables, Lambda functions, EventBridge, Cognito, CloudFront, AgentCore Runtimes)
- Demo seed data (5 patients, 20 devices)
- React frontend (auto-configured from CDK outputs)
- Optional: AgentCore Memory, Bedrock Knowledge Base

All resources are named `<prefix>-<resource>`, e.g. `mercy-hospital-patients`, `mercy-hospital-agent-api`.

## CDK-Only Deployment

If you prefer to deploy via CDK directly:

```bash
cd infrastructure
npm install

# Default prefix
npx cdk deploy --all --require-approval never

# Custom prefix
npx cdk deploy --all --require-approval never -c resourcePrefix=acme-health
```

Or set the default in `infrastructure/cdk.json`:

```json
{
  "context": {
    "resourcePrefix": "acme-health"
  }
}
```

## Configuration

### Resource Prefix

The prefix controls all AWS resource names. Set it via:

1. **CLI flag**: `./scripts/deploy.sh --prefix=my-org`
2. **CDK context**: `cdk deploy -c resourcePrefix=my-org`
3. **cdk.json**: Edit `context.resourcePrefix`

### Region

Set via:

1. **CLI flag**: `./scripts/deploy.sh --region=eu-west-1`
2. **Environment**: `export CDK_DEFAULT_REGION=eu-west-1`
3. **AWS CLI profile**: Region from your configured profile

### Bedrock Models

Models are configurable via environment variables on the AgentCore runtimes. Defaults:

- Domain agents: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
- Orchestrator: `us.anthropic.claude-opus-4-6-v1`

## Multiple Environments

Deploy dev/staging/prod in the same account using different prefixes:

```bash
./scripts/deploy.sh --prefix=cc-dev
./scripts/deploy.sh --prefix=cc-staging
./scripts/deploy.sh --prefix=cc-prod
```

Each deployment is fully isolated — separate tables, functions, event buses, and auth.

## Cleanup

```bash
cd infrastructure
npx cdk destroy --all --force

# If you deployed with --with-memory:
python scripts/utils/reset-memory.py

# If you deployed with --with-kb:
# Delete Knowledge Base via Bedrock console
# Delete S3 bucket: aws s3 rb s3://<prefix>-guidelines-<account-id> --force
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CDK bootstrap error | Run `cdk bootstrap aws://ACCOUNT_ID/REGION` |
| Bedrock access denied | Enable model access in Bedrock console for your region |
| Docker build fails | Ensure Docker daemon is running |
| S3 bucket exists | Bucket names are globally unique; use a different prefix |
| KB ingestion slow | Normal — 37K docs takes 30-60 min. Agent works without KB. |
