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
from agent.prompts import SYSTEM_PROMPT

runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")
host, port = "0.0.0.0", 9000


# Sonnet recommended for cost efficiency (~$3/M input vs ~$15/M for Opus).
# Override: BEDROCK_MODEL_ID=us.anthropic.claude-opus-4-6-v1
model = BedrockModel(
    model_id=os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-20250514-v1:0'),
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
