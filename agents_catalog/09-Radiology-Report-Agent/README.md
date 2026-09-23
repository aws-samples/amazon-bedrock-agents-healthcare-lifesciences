# Radiology Report Validator Agent

Validates radiology reports against American College of Radiology (ACR) guidance
documents. In many radiology departments, senior radiologists must review and
validate reports written by junior colleagues — a critical but time-consuming
bottleneck. This agent evaluates a report against the relevant ACR guideline
document and returns terse, actionable feedback: whether the report adheres to
ACR guidelines, is detailed enough to support a diagnosis, is missing key
anatomical structures, and meets ACR quality standards.

It does document-grounded validation, not clinical diagnosis. Clinical questions
should be referred to qualified healthcare professionals.

## Implementation

This agent runs on the **Amazon Bedrock AgentCore runtime** using the **Strands
SDK**. See [`agentcore/`](./agentcore/) for the implementation, deployment, and
tests.

```mermaid
flowchart LR
    User([Radiologist]) -->|report| Runtime[AgentCore Runtime<br/>Strands Agent]
    Runtime -->|1. download_guidance_document| S3[(S3 bucket<br/>ACR guideline PDFs)]
    S3 -->|guideline PDF| Runtime
    Runtime -->|2. run_validator<br/>converse + PDF| Bedrock[Amazon Bedrock<br/>Claude Sonnet 5]
    Bedrock -->|actionable feedback| Runtime
    Runtime -->|validation feedback| User
```

| Tool | Purpose |
|------|---------|
| `download_guidance_document(anatomical_structure)` | Downloads the ACR guidance PDF(s) matching a modality/anatomical structure (e.g. `Chest`) from S3. |
| `run_validator(report)` | Grounds an Amazon Bedrock `converse` call on the staged ACR guideline PDF and returns actionable validation feedback. |

## Guidance documents

The ACR guideline PDFs live in [`ACRdocs/`](./ACRdocs/). Upload them to the S3
bucket the agent reads from (see [`agentcore/README.md`](./agentcore/README.md)
for bucket configuration and IAM requirements), keying each object so the
anatomical structure appears in the key (e.g. `Chest/ACR_Chest.pdf`).

## Deploy

Full deployment steps — S3 setup, `agentcore configure` / `deploy`, execution-role
IAM, and `agentcore invoke` — are documented in
[`agentcore/README.md`](./agentcore/README.md#deploy).

## Migration note

This agent was migrated from a notebook-driven Amazon Bedrock Agent with a Lambda
action group to Strands + AgentCore (issue #370). The original Lambda instantiated
SageMaker and AWS Batch clients and read `BATCH_JOB_*` environment variables that
its implemented functions never used; that dead wiring was dropped in the
migration. The previous `create_agent.ipynb` notebook and `lambda/` action group
have been removed in favor of the `agentcore/` implementation.
