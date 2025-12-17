import json
import logging
import os
from datetime import date

import boto3
import botocore
from strands import tool

# Dynamo DB Configuration
EVIDENCE_TABLE_NAME = os.getenv("EVIDENCE_TABLE_NAME", "deep-research-evidence")

# Configure logging
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("generate_report")
logger.level = logging.INFO

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb")

# Initialize Bedrock client with increased timeout
bedrock_client = boto3.client(
    "bedrock-runtime",
    config=botocore.config.Config(read_timeout=900, connect_timeout=30),
)


SYSTEM_PROMPT = f"""
The current date is {date.today().strftime('%B %d, %Y')}

You are an expert technical writer that answers biomedical questions using scientific literature and other authoritative sources. 
You maintain user trust by being consistent (dependable or reliable), benevolent (demonstrating good intent, connectedness, and care), transparent (truthful, humble, believable, and open), and competent (capable of answering questions with knowledge and authority).
Use a professional tone that prioritizes clarity, without being overly formal.
Use precise language to describe technical concepts. For example, use, "femur" instead of "leg bone" and "cytotoxic T lymphocyte" instead of "killer T cell".

Structure your output as a comprehensive document that clearly communicates your research findings to the reader. Follow these guidelines:

Report Structure:

- Begin with a concise introduction (1-2 paragraphs) that establishes the research question, explains why it's important, and provides a brief overview of your approach
- Organize the main body into sections that correspond to the major research tasks you completed (e.g., "Literature Review," "Current State Analysis," "Comparative Assessment," "Technical Evaluation," etc.)
- Conclude with a summary section (1-2 paragraphs) that synthesizes key findings and discusses implications

Section Format:

- Write each section in paragraph format using 1-3 well-developed paragraphs
- Each paragraph should focus on a coherent theme or finding
- Use clear topic sentences and logical flow between paragraphs
- Integrate information from multiple sources within paragraphs rather than listing findings separately

Citation Requirements:

- Include proper citations for all factual claims using the format provided in your source materials
- Place citations at the end of sentences before punctuation (e.g., "Recent studies show significant progress in this area .")
- Group related information from the same source under single citations when possible
- Ensure every major claim is supported by appropriate source attribution

Writing Style:

- Use clear, professional academic language appropriate for scientific communication
- Use active voice and strong verbs
- Synthesize information rather than simply summarizing individual sources
- Draw connections between different pieces of information and highlight patterns or contradictions
- Focus on analysis and interpretation, not just information presentation
- Don't use unnecessary words. Keep sentences short and concise.
- WRite for a global audience. Avoid jargon an colloquial language. 

Quality Standards:

- Ensure logical flow between sections and paragraphs
- Maintain consistency in terminology and concepts throughout
- Provide sufficient detail to support conclusions while remaining concise
- End with actionable insights or clear implications based on your research findings
"""


def _get_evidence_record(evidence_id: str) -> dict:
    """Get an evidence record from DynamobDB table by evidence_id value"""

    # Check if table exists
    table = dynamodb.Table(EVIDENCE_TABLE_NAME)

    response = table.get_item(Key={"evidence_id": evidence_id})

    return response.get("Item")


def parse_db_records(records):
    """Parse records from our DynamoDB table into content blocks for the Anthropic Claude citation API"""

    contents = []
    for record in records:

        contents.append(
            {
                "type": "document",
                "source": {
                    "type": "content",
                    "content": [
                        {"type": "text", "text": context}
                        for context in record.get("context")
                    ],
                },
                "title": record.get("source"),
                "context": record.get("answer"),
                "citations": {"enabled": True},
            },
        )

    return contents


def format_inline_citations(response_content: dict) -> None:
    """Format response from Anthropic Claude citations API into inline citations"""
    output = ""
    for content_item in response_content.get("content"):
        output += content_item.get("text")
        for citation in content_item.get("citations", []):
            title = citation.get("document_title")
            # If last character is punctuation, remove it
            if output[-1] in [".", ",", "?", "!"]:
                punctuation = output[-1]
                output = output[:-1] + f" ({title}){punctuation}"
            else:
                output += f" ({title})"

    return output


def generate_report(prompt: str, evidence_ids: list = []) -> str:
    """Generate a formatted, well-written scientific report with inline citations to evidence records"""

    content = []

    if evidence_ids:
        logger.info("Getting evidence records")
        evidence = []
        for evidence_id in evidence_ids:
            evidence.append(_get_evidence_record(evidence_id))
        logger.info("Parsing evidence records")
        content = parse_db_records(evidence)

    prompt_message = [{"type": "text", "text": prompt}]
    content.extend(prompt_message)

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 10000,
        "system": SYSTEM_PROMPT,
    }

    logger.info("Invoking Anthropic Claude citations API")
    response = bedrock_client.invoke_model(
        modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body),
    )

    logger.info("Formatting report with inline citations")

    formatted_result = format_inline_citations(json.loads(response["body"].read()))
    return formatted_result


@tool
def generate_report_tool(prompt: str, evidence_ids: list = []) -> str:
    """
    Generate a scientific report with inline citations from evidence.

    Creates a well-written scientific report based on the provided prompt.
    Retrieves evidence from DynamoDB using the provided evidence_ids and
    incorporates them as inline citations in the report.

    Args:
        prompt: The report topic or research question (e.g., "Write a report about recent advancements in antibody-drug conjugates")
        evidence_ids: List of evidence IDs to retrieve and cite (e.g., ["b7f77ea3-e0bd-4512-8698-1c04328c7353", "e6fbd06a-da3f-465f-83ac-2f37250345c4"])

    Returns:
        A formatted scientific report with inline citations
    """
    return generate_report(prompt=prompt, evidence_ids=evidence_ids)


if __name__ == "__main__":
    result = generate_report(
        "How safe and effective are GLP-1 drugs for long term use?",
        [
            "b7f77ea3-e0bd-4512-8698-1c04328c7353",
            "e6fbd06a-da3f-465f-83ac-2f37250345c4",
        ],
    )

    print(result)
