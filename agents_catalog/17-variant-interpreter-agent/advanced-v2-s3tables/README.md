# Variant Interpreter Agent — VEP + S3 Tables + Strands AI Agent

An AI-powered genomics variant interpretation pipeline. VCF files are annotated with Ensembl VEP via AWS HealthOmics, loaded into Amazon S3 Tables (Apache Iceberg), and queried through a natural-language agent deployed on Amazon Bedrock AgentCore.

**Pipeline:** VCF → VEP annotation → S3 Tables (Iceberg) → Athena SQL → AI interpretation

**Agent:** Strands SDK + Claude Opus 4.6 → A2A protocol → AgentCore Runtime → Agent Registry

## Why S3 Tables?

This version replaces AWS HealthOmics variant/annotation stores (no longer available to new customers) with **Amazon S3 Tables**, which provides:

| Capability | S3 Tables (this version) | Previous (HealthOmics stores) |
|-----------|--------------------------|-------------------------------|
| **Storage format** | Apache Iceberg (open standard) | Proprietary HealthOmics format |
| **Query engine** | Amazon Athena (standard SQL) | HealthOmics-specific API |
| **Scale** | Billions of rows, auto-compaction | Limited by store quotas |
| **Cost** | S3 pricing + Athena per-query | HealthOmics store pricing |
| **Partitioning** | By sample + chromosome for fast queries | Fixed by store |
| **Interoperability** | Any Iceberg-compatible tool (Spark, Trino, pandas) | HealthOmics SDK only |
| **Table maintenance** | Automatic compaction, snapshot management | Manual |
| **Availability** | GA, all regions | Closed to new customers |

### Running at Scale — Multi-Patient Cohorts

The pipeline is designed for scale. To process a cohort of hundreds or thousands of patients:

1. **Upload VCFs to S3** — Each `.vcf.gz` triggers the pipeline automatically via S3 Event Notification
2. **Parallel VEP annotation** — Each VCF runs as a separate HealthOmics workflow (~65 min per whole-genome)
3. **Streaming Iceberg import** — Container Lambda loads annotated VCFs into S3 Tables via pyiceberg with smart_open streaming (no intermediate files)
4. **Partitioned storage** — Data is partitioned by `sample_name` + `chrom`, so queries on specific patients or chromosomes scan only relevant partitions
5. **Athena at scale** — Queries across the full cohort use Athena's distributed engine; partition pruning keeps costs low

The Iceberg table handles concurrent writes from multiple Lambda invocations. S3 Tables provides automatic compaction to optimize query performance as data grows.

```
Patient 1 VCF ──┐
Patient 2 VCF ──┤──▶ HealthOmics VEP (parallel) ──▶ S3 Tables (Iceberg) ──▶ Athena ──▶ AI Agent
Patient 3 VCF ──┤                                    Partitioned by
  ...           │                                    sample + chrom
Patient N VCF ──┘
```

## Solution Architecture

See [docs/architecture.html](docs/architecture.html) for an interactive diagram.

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────────┐
│ Patient VCFs │────▶│ AWS HealthOmics  │────▶│ S3 Tables          │
│ (.vcf.gz)    │     │ VEP v113.4       │     │ (Apache Iceberg)   │
│              │     │ GRCh38           │     │ 12-col schema      │
└──────────────┘     └──────────────────┘     │ Partitioned by     │
       │ S3 Event         │ EventBridge       │ sample + chrom     │
       ▼                  ▼                   └─────────┬──────────┘
  Trigger Lambda    Import Lambda                       │
                    (pyiceberg)                         ▼
                                              ┌────────────────────┐
                                              │ Amazon Athena      │
                                              │ s3tablescatalog    │
                                              └─────────┬──────────┘
                                                        │ Dynamic SQL
                                                        ▼
                                              ┌────────────────────┐
                                              │ AI Agent (Strands) │
                                              │ Claude Sonnet 4.5  │
                                              │ 3 tools            │
                                              └─────────┬──────────┘
                                                        │ A2A Protocol
                                                        ▼
                                              ┌────────────────────┐
                                              │ AgentCore Runtime  │──▶ Streamlit UI
                                              │ Agent Registry     │──▶ CLI Runner
                                              └────────────────────┘──▶ Other A2A Agents
```

## Table Schema

Single unified table: `variant_db_3.genomic_variants_fixed`

| Column | Type | Notes |
|--------|------|-------|
| `sample_name` ⚷ | STRING | Partition key |
| `chrom` ⚷ | STRING | Partition key |
| `pos` | LONG | Genomic position |
| `ref` | STRING | Reference allele |
| `alt` | LIST\<STRING\> | Alternate allele(s) |
| `qual` | DOUBLE | Quality score |
| `filter` | STRING | PASS or filter reason |
| `genotype` | STRING | 0\|0, 0\|1, 1\|1 |
| `info` | MAP\<STRING,STRING\> | VEP CSQ + population frequencies (AF, EAS/EUR/AFR/AMR/SAS) |
| `attributes` | MAP\<STRING,STRING\> | FORMAT fields (GT, DP, GQ) |
| `variant_name` | STRING | VCF ID field |
| `is_reference_block` | BOOLEAN | gVCF reference blocks |

**VEP annotations** are stored in `info['CSQ']` as pipe-delimited fields: `Allele|Consequence|IMPACT|SYMBOL|Gene|Feature_type|Feature|BIOTYPE|EXON|INTRON|...` (23 fields, GRCh38 reference).

**Population frequencies** from 1000 Genomes are in the info MAP: `AF`, `EAS_AF`, `EUR_AF`, `AFR_AF`, `AMR_AF`, `SAS_AF`.

## Sample Data — 1000 Genomes Project

This solution uses publicly available whole-genome sequencing data from the [1000 Genomes Project](https://www.internationalgenome.org/) as sample input. The 1000 Genomes dataset is ideal for demonstrating the pipeline because:

- **Publicly available** — no patient consent or data access agreements needed
- **Realistic scale** — ~3M variants per sample (whole-genome), representative of production workloads
- **Population diversity** — 2,504 samples across 26 populations, enabling cohort and population frequency analysis
- **Well-characterized** — extensively validated, with population allele frequencies (AF, EAS_AF, EUR_AF, AFR_AF, AMR_AF, SAS_AF) embedded in the VCF INFO field

The current deployment includes chromosome 22 data for sample HG00096 (1,059,079 variants). VCF files are sourced from the 1000 Genomes public S3 bucket:

```
s3://1000genomes/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz
```

To load additional samples or chromosomes, upload VCF files to the S3 input bucket — the pipeline processes them automatically.

## Quick Start

### Prerequisites

- Python 3.10+
- AWS account with Bedrock model access (Claude Opus 4.6)
- Pipeline deployed (see [Deployment Guide](DEPLOYMENT_GUIDE.md))

### 1. Install dependencies

```bash
pip install strands-agents a2a-sdk fastapi uvicorn pyiceberg boto3 pandas streamlit
```

### 2. Configure

```bash
cp .agent-config.example .agent-config
# Edit .agent-config with your AWS account details
source .agent-config
```

### 3. Run locally (interactive CLI)

```bash
source .agent-config
python run-agent-local.py
```

### 4. Run locally (Streamlit UI — direct agent, no deployment needed)

```bash
source .agent-config
streamlit run app-local.py
```

### 5. Deploy to AgentCore Runtime

```bash
source .agent-config
python -c "
from bedrock_agentcore_starter_toolkit import Runtime
import os
runtime = Runtime()
runtime.configure(
    agent_name='variant_interpreter_a2a',
    protocol='A2A',
    entrypoint='agent/main.py',
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file='agent-requirements.txt',
    region=os.environ.get('AWS_REGION', 'us-west-2')
)
result = runtime.launch()
print(f'Agent ARN: {result.agent_arn}')
"
```

### 6. Run Streamlit UI (connected to deployed agent)

```bash
source .agent-config
streamlit run app.py
```

## Dynamic SQL Generation

A key differentiator of this agent is **schema-aware dynamic SQL generation**. Unlike traditional approaches with hardcoded query functions, this agent:

1. **Retrieves the live table schema** from the S3 Tables catalog at runtime
2. **Generates SQL dynamically** based on the user's natural-language question and the actual schema
3. **Executes via Athena** with input validation (DDL/DML blocked, LIMIT enforced)
4. **Interprets results** with clinical genomics expertise

This means the agent adapts automatically to schema changes — add a column to the Iceberg table and the agent can query it immediately without code changes.

```
User: "Show me HIGH impact variants in the BRCA1 gene for HG00096"
                    │
                    ▼
        ┌───────────────────────┐
        │ 1. get_table_schema   │  → Fetches 12-column schema from S3 Tables catalog
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │ 2. Claude Sonnet 4.5  │  → Generates SQL:
        │    generates SQL      │    SELECT pos, ref, alt, genotype, info['CSQ']
        │                       │    FROM variant_db_3.genomic_variants_fixed
        │                       │    WHERE sample_name = 'HG00096'
        │                       │    AND info['CSQ'] LIKE '%|BRCA1|%'
        │                       │    AND info['CSQ'] LIKE '%|HIGH|%'
        │                       │    AND genotype != '0|0' LIMIT 20
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │ 3. execute_query      │  → Runs on Athena against S3 Tables (Iceberg)
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │ 4. Clinical           │  → "Found 3 HIGH impact variants in BRCA1:
        │    interpretation     │     stop_gained at pos 41,244,000 (heterozygous)..."
        └───────────────────────┘
```

## Example Queries

**Quick (< 15s):**
- "How many samples are in the cohort?"
- "How many HIGH impact variants does HG00096 have on chr22?"

**Analysis (15-60s):**
- "Show me the variant impact distribution for HG00096 on chr22"
- "Show me 10 HIGH impact variants on chr22 for HG00096 with gene names"
- "Are there any BRCA1 or BRCA2 variants in HG00096?"

**The agent asks clarifying questions for broad queries** like "Analyze variants for HG00096" — it suggests narrowing by gene, chromosome, impact level, or analysis type.

## Project Structure

```
├── agent/                      # AI Agent
│   ├── main.py                 # A2A server (Strands + FastAPI + AgentCore)
│   └── tools/
│       ├── schema_tool.py      # get_table_schema — S3 Tables catalog API
│       └── query_tool.py       # execute_query + get_cohort_summary — Athena
│
├── app.py                      # Streamlit UI (deployed agent via A2A)
├── app-local.py                # Streamlit UI (local agent, no deployment)
├── run-agent-local.py          # Interactive CLI runner
├── agent-requirements.txt      # Agent Python dependencies
│
├── deploy-unified.sh           # Step 1: VEP cache, Docker image, ClinVar, reference
├── deploy-orchestration.sh     # Step 2: Trigger Lambda, EventBridge, DynamoDB, IAM
├── deploy-s3tables-import-lambda.sh  # Step 3: Import Lambda (container)
│
├── lambda_s3tables_import.py   # Lambda handler: EventBridge → VEP output → S3 Tables
├── load_vcf_schema3.py         # Streaming VCF parser + Iceberg writer
├── schema_3.py                 # Iceberg table schema definition
├── utils.py                    # S3 Tables catalog utilities
├── Dockerfile.s3tables-import  # Import Lambda container image
├── infrastructure.yaml         # CloudFormation template (reference)
│
├── DEPLOYMENT_GUIDE.md         # Step-by-step deployment instructions
├── docs/architecture.html      # Interactive architecture diagram
└── .agent-config.example       # Template for environment configuration
```

## Agent Tools

| Tool | Purpose | Data Source |
|------|---------|-------------|
| `get_table_schema` | Retrieve table schema dynamically | S3 Tables catalog API (pyiceberg), hardcoded fallback |
| `execute_query` | Run agent-generated SQL with input validation | Amazon Athena via s3tablescatalog |
| `get_cohort_summary` | Sample counts, variant counts, quality stats | Fixed Athena aggregation query |

The agent generates SQL dynamically based on the schema and user question. It uses the VEP CSQ annotations for gene lookups, impact classification, and clinical interpretation.

## Deployment Pipeline

| Step | Script | What it does |
|------|--------|-------------|
| 1 | `deploy-unified.sh` | VEP cache, Docker image (amd64), ClinVar data, reference store |
| 2 | `deploy-orchestration.sh` | Trigger Lambda, EventBridge rules, S3 notifications, DynamoDB, IAM |
| 3 | `deploy-s3tables-import-lambda.sh` | Build container image, push to ECR, deploy import Lambda |
| 4 | AgentCore toolkit (see Quick Start §5) | Deploy A2A agent to AgentCore Runtime |

## A2A Agent Registration

The agent is registered in the HCLS Agent Registry for discovery by other agents:

```python
# Registry: hcls-agentcore-tools-registry (IaX7zUB3GzYZGWHr)
# Record: variant_interpreter_a2a
# Skills: Variant Query & Interpretation, Cohort Analysis
# Protocol: A2A (Agent-to-Agent)
```

Other agents can discover this agent via semantic search and invoke it through the A2A protocol.

## License

MIT-0
