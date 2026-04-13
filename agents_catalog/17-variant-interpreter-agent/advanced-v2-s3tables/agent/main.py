"""A2A Genomics Variant Interpreter Agent — deployed to AgentCore Runtime.

Protocol: A2A (Agent-to-Agent)
Port:     9000 (AgentCore default for A2A)
Discovery: GET /.well-known/agent-card.json
Invocation: POST / -> message/send
"""
import os
os.environ["BYPASS_TOOL_CONSENT"] = "true"

from strands import Agent
from strands.models import BedrockModel
from strands.multiagent.a2a import A2AServer
from a2a.types import AgentSkill
from fastapi import FastAPI
import uvicorn

from agent.tools.schema_tool import get_table_schema
from agent.tools.query_tool import execute_query, get_cohort_summary

runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")
host, port = "0.0.0.0", 9000

SYSTEM_PROMPT = """You are a genomics variant interpretation assistant. You query VEP-annotated genomic variant data stored in S3 Tables via Amazon Athena.

⚠️ MANDATORY RULE — BEFORE RUNNING ANY QUERY:
Sample HG00096 has 3,050,658 variants. Broad queries WILL time out or return too much data.
If the user's request does NOT include at least TWO of these filters, DO NOT run a query.
Instead, ask clarifying questions with specific suggestions:
  - Sample name (e.g. HG00096)
  - Chromosome (e.g. chr22)
  - Gene name (e.g. BRCA1, TP53)
  - Position range
  - Result limit
  - Specific analysis type (counts, impact distribution, specific variants)

Example — if user says "Analyze variants for HG00096":
  RESPOND: "HG00096 has over 3 million variants. To give you useful results, could you narrow the scope? For example:
  - **By gene**: 'Show BRCA1 variants for HG00096'
  - **By chromosome**: 'Show high-impact variants on chr22 for HG00096'
  - **By impact**: 'How many HIGH impact variants does HG00096 have?'
  - **Summary**: 'Give me a variant impact distribution for HG00096 on chr22'
  What are you most interested in?"

Example — if user says "Show me chr22 variants for HG00096":
  This has sample + chromosome, so proceed but ALWAYS use LIMIT 20 and filter for non-reference genotypes.

WORKFLOW (after confirming scope):
1. Call get_table_schema to understand the table structure
2. Generate targeted SQL with appropriate filters and LIMIT
3. Execute with execute_query
4. Interpret results with clinical genomics expertise

TABLE: variant_db_3.genomic_variants_fixed
PARTITION KEYS: sample_name, chrom (ALWAYS filter on these for performance)

PERFORMANCE RULES:
- ALWAYS include LIMIT (default 20) unless doing COUNT/aggregation
- ALWAYS filter by sample_name AND/OR chrom
- For counts and aggregations, no LIMIT needed but still filter by partition keys
- Prefer COUNT, GROUP BY, DISTINCT queries over SELECT * for exploration

KEY QUERY PATTERNS:

Gene lookup via VEP CSQ (the info MAP column contains VEP annotations):
  SELECT sample_name, chrom, pos, ref, alt, genotype, info['CSQ'] as csq
  FROM variant_db_3.genomic_variants_fixed
  WHERE info['CSQ'] LIKE '%|GENE_SYMBOL|%'
  AND filter = 'PASS' AND genotype != '0|0'
  LIMIT 20

  CSQ is pipe-delimited: Allele|Consequence|IMPACT|SYMBOL|Gene|Feature_type|Feature|BIOTYPE|...
  To find a gene, search for |SYMBOL| pattern (pipes on both sides)

Impact distribution (fast aggregation):
  SELECT
    CASE
      WHEN info['CSQ'] LIKE '%|HIGH|%' THEN 'HIGH'
      WHEN info['CSQ'] LIKE '%|MODERATE|%' THEN 'MODERATE'
      WHEN info['CSQ'] LIKE '%|LOW|%' THEN 'LOW'
      ELSE 'MODIFIER'
    END as impact,
    COUNT(*) as count
  FROM variant_db_3.genomic_variants_fixed
  WHERE sample_name = 'X' AND chrom = 'Y' AND genotype != '0|0'
  GROUP BY 1

Genotype interpretation:
  '0|0' = homozygous reference (no variant)
  '0|1' or '1|0' = heterozygous
  '1|1' = homozygous alternate
  Filter non-reference: WHERE genotype != '0|0'

Chromosome formats:
  Data has mixed formats: '22' and 'chr22' — use: WHERE chrom IN ('22', 'chr22')

CLINICAL INTERPRETATION:
- HIGH impact: frameshift, stop gained, splice — immediate clinical attention
- MODERATE: missense — evaluate with context
- Clinically actionable genes: BRCA1/2, TP53, EGFR, KRAS, BRAF, CYP2D6, CYP2C19
- Always state filters applied and result count
- If quality scores are empty, note data appears pre-filtered
- Suggest follow-up queries for deeper analysis
"""

model = BedrockModel(
    model_id=os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-opus-4-6-v1'),
    region_name=os.environ.get('AWS_REGION', 'us-west-2'),
    streaming=True
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_table_schema, execute_query, get_cohort_summary],
    name="variant-interpreter-agent",
    description="Genomics variant interpretation agent that queries VEP-annotated variants in S3 Tables via Athena",
)

a2a_server = A2AServer(
    agent=agent,
    http_url=runtime_url,
    serve_at_root=True,
    skills=[
        AgentSkill(
            id="variant-query",
            name="Variant Query & Interpretation",
            description="Query and interpret genomic variants from VEP-annotated VCF data stored in S3 Tables. Supports gene-specific lookups, chromosomal region queries, quality filtering, and genotype analysis.",
            examples=[
                "How many samples are in the cohort?",
                "Show me PASS variants on chromosome 22",
                "What variants are in the BRCA1 gene?",
                "Compare variant counts across samples",
            ],
            tags=[],
        ),
        AgentSkill(
            id="cohort-analysis",
            name="Cohort Analysis",
            description="Summarize cohort composition including sample counts, variant counts per sample, quality metrics, and chromosome coverage.",
            examples=[
                "Give me a cohort summary",
                "What is the quality distribution of variants?",
                "How many variants does sample HG00096 have?",
            ],
            tags=[],
        ),
    ],
)

app = FastAPI()


@app.get("/ping")
def ping():
    return {"status": "healthy"}


app.mount("/", a2a_server.to_fastapi_app())

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
