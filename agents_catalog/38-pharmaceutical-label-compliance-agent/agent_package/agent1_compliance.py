import boto3
import json
import uuid
import os
import logging
from datetime import datetime
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve
from steering_hooks import ComplianceWorkflowPlugin

# Logger respects LOG_LEVEL (default WARNING).
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "WARNING").upper())

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")

if KNOWLEDGE_BASE_ID:
    logger.info("Amazon Bedrock knowledge base ID configured: %s", KNOWLEDGE_BASE_ID)
else:
    logger.warning("KNOWLEDGE_BASE_ID not set; Amazon Bedrock knowledge base queries will fail")

RESULTS_BUCKET = os.environ['RESULTS_BUCKET']

# Amazon S3 client for storing compliance reports
aws_region = boto3.Session().region_name
amazon_s3 = boto3.client('s3')

# Bedrock Guardrail applied to every agent model call (identifiers injected by the deployment).
_GUARDRAIL_KWARGS = {
    "guardrail_id": os.environ.get("GUARDRAIL_ID", ""),
    "guardrail_version": os.environ.get("GUARDRAIL_VERSION", "DRAFT"),
}

@tool
def store_compliance_report(report: str, violations: str, source_file: str) -> str:
    """Store compliance report and structured violations in Amazon S3 results bucket."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = str(uuid.uuid4())[:8]
    key = f"compliance-report-{timestamp}-{session_id}.json"

    # Parse violations JSON string into a list
    try:
        violations_list = json.loads(violations) if isinstance(violations, str) else violations
    except (json.JSONDecodeError, TypeError):
        violations_list = []

    report_data = {
        'timestamp': timestamp,
        'session_id': session_id,
        'source_file': source_file,
        'compliance_report': report,
        'violations': violations_list,
        'analysis_date': datetime.now().isoformat()
    }

    amazon_s3.put_object(
        Bucket=RESULTS_BUCKET,
        Key=key,
        Body=json.dumps(report_data, indent=2),
        ContentType='application/json'
    )

    return f"s3://{RESULTS_BUCKET}/{key}"

# Create list of tools (including built-in retrieve tool)
compliance_analysis_tools = [retrieve, store_compliance_report]

agent_instructions = """Act as an FDA/MHRA compliance expert for OTC medicine labels.

The system provides the medicine label image directly as visual input. Read the label using vision: transcribe text, identify panels (e.g. Drug Facts), note warnings, directions, ingredient lists, marketing claims, and any missing standard sections.

Workflow: Examine the attached label image, retrieve relevant regulations from the knowledge base with the retrieve tool, analyze compliance, and then call store_compliance_report. Tool ordering is enforced automatically — retrieve must be called before store_compliance_report.

For compliance analysis, check against regulations based on the region:
- US FDA: 21 CFR Part 201 requirements (warning statements, ingredient disclosure, marketing claims, dosage directions, labeling format)
- UK MHRA: Human Medicines Regulations 2012 requirements (patient information leaflet, product characteristics, labeling requirements)

Always cite specific regulations from the knowledge base in the analysis.

STRUCTURED VIOLATIONS OUTPUT:
Produce a structured JSON array of all violations found. Each violation object must have:
- "title": A brief, clear violation title (e.g., "Missing Drug Facts Panel")
- "description": A detailed description with regulatory references
- "severity": One of "high", "medium", or "low"

SEVERITY RULES:
- "high": Missing essential safety elements, critical regulatory violations, missing required sections
- "medium": Formatting violations, unsubstantiated marketing claims, incomplete information
- "low": Clear but minor regulatory deviations (not recommendations, not stylistic preferences)

Do NOT include suggestions, best-practice recommendations, or cosmetic concerns as violations. The violations array is for actual non-compliance only.

MATERIALITY GUIDANCE:
- Only report violations that a reasonable FDA/MHRA reviewer would cite in a warning letter or compliance action.
- Do not flag stylistic preferences, minor wording variations, or issues that don't affect consumer safety or regulatory standing.
- If a requirement is substantially met (even if not phrased identically to the regulation), do not flag it.
- When in doubt between two severity levels, choose the lower one.
- When in doubt whether something is a violation at all, do not include it.
- It is acceptable and expected for compliant labels to return an empty violations array.

The store_compliance_report tool requires three parameters:
- report: The full narrative analysis text
- violations: A JSON string of the violations array, e.g. '[{"title":"...","description":"...","severity":"high"},...]'
- source_file: The Amazon S3 key of the analyzed image (provided in the user message)

If the label is fully compliant with no violations, pass an empty array: '[]'"""

def get_compliance_agent(regulatory_region='US_FDA'):
    """Get compliance agent configured for specific regulatory region"""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-6",
        region_name=aws_region,
        temperature=0.1,
        streaming=False,
        **_GUARDRAIL_KWARGS
    )

    agent = Agent(
        model=model,
        tools=compliance_analysis_tools,
        system_prompt=agent_instructions,
        plugins=[ComplianceWorkflowPlugin()]  # steering hook
    )
    agent.name = f"Compliance_Analysis_Agent_{regulatory_region}"
    return agent
