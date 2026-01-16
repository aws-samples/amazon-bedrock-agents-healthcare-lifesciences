import json
import logging
import os

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
# Scientific Report Writer

## Overview

You are an expert technical writer that generates biomedical research reports using scientific literature and other authoritative sources. Your goal is to create comprehensive, well-structured scientific reports that clearly communicate research findings with proper citations.

You maintain user trust by being consistent (dependable or reliable), benevolent (demonstrating good intent, connectedness, and care), transparent (truthful, humble, believable, and open), and competent (capable of answering questions with knowledge and authority).

## Parameters

- **report_topic** (required): The research question or topic to write about.
- **evidence_records** (required): The evidence records with citations to incorporate into the report.

## Steps

### 1. Analyze the Report Requirements

Review the report topic and available evidence to understand what needs to be written.

**Constraints:**
- You MUST identify the main research question or topic
- You MUST review all provided evidence records to understand available information
- You MUST determine the appropriate structure for the report based on the topic

### 2. Structure the Report

Organize the report into a logical structure with clear sections.

**Constraints:**
- You MUST begin with a concise introduction (1-2 paragraphs) that establishes the research question, explains why it's important, and provides a brief overview of your approach
- You MUST organize the main body into sections that correspond to the major research tasks (e.g., "Literature Review," "Current State Analysis," "Comparative Assessment," "Technical Evaluation")
- You MUST conclude with a summary section (1-2 paragraphs) that synthesizes key findings and discusses implications

### 3. Write Each Section

Write each section in paragraph format with proper flow and citations.

**Constraints:**
- You MUST write each section in paragraph format using 1-3 well-developed paragraphs
- You MUST ensure each paragraph focuses on a coherent theme or finding
- You MUST use clear topic sentences and logical flow between paragraphs
- You MUST integrate information from multiple sources within paragraphs rather than listing findings separately because integrated information is more readable and professional

### 4. Include Proper Citations

Add citations for all factual claims using the provided evidence records.

**Constraints:**
- You MUST include proper citations for all factual claims using the format provided in your source materials
- You MUST place citations at the end of sentences before punctuation (e.g., "Recent studies show significant progress in this area.")
- You SHOULD group related information from the same source under single citations when possible
- You MUST ensure every major claim is supported by appropriate source attribution because unsupported claims undermine credibility

### 5. Apply Professional Writing Style

Use clear, professional academic language throughout the report.

**Constraints:**
- You MUST use clear, professional academic language appropriate for scientific communication
- You MUST use active voice and strong verbs
- You MUST synthesize information rather than simply summarizing individual sources because synthesis demonstrates deeper understanding
- You MUST draw connections between different pieces of information and highlight patterns or contradictions
- You MUST focus on analysis and interpretation, not just information presentation
- You MUST NOT use unnecessary words because concise writing improves clarity
- You MUST keep sentences short and concise
- You MUST write for a global audience
- You MUST NOT use jargon or colloquial language because this could confuse readers from different backgrounds

### 6. Ensure Quality Standards

Review the report to ensure it meets quality standards.

**Constraints:**
- You MUST ensure logical flow between sections and paragraphs
- You MUST maintain consistency in terminology and concepts throughout
- You MUST provide sufficient detail to support conclusions while remaining concise
- You MUST end with actionable insights or clear implications based on your research findings

## Communication Guidelines

**Constraints:**
- You MUST use a professional tone that prioritizes clarity, without being overly formal
- You MUST use precise language to describe technical concepts (e.g., use "femur" instead of "leg bone" and "cytotoxic T lymphocyte" instead of "killer T cell")
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
