"""Radiology Report Validator Agent — Strands + AgentCore.

Validates radiology reports against American College of Radiology (ACR)
guidance documents. ACR guideline PDFs are stored in an S3 bucket; a report is
validated by grounding an Amazon Bedrock ``converse`` call on the relevant
guideline PDF.

Migrated from the notebook-driven Bedrock Agent + Lambda action group in the
parent directory. The original Lambda carried unused SageMaker/AWS Batch
clients and ``BATCH_JOB_*`` environment variables; that dead wiring is dropped
here.
"""

import logging
import os
import tempfile

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

MODEL_ID = os.environ.get("MODEL_ID", "global.anthropic.claude-sonnet-5")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "radiologyreport-validator")

# Directory where guideline PDFs are staged between download and validation.
# Configurable so the agent works outside a Lambda's ephemeral /tmp.
GUIDANCE_DIR = os.environ.get("GUIDANCE_DIR", os.path.join(tempfile.gettempdir(), "acr_guidance"))

SYSTEM_PROMPT = """You are a Radiology Report Validator. You help junior radiologists write \
reports that adhere to American College of Radiology (ACR) guidance criteria.

Workflow:
1. First confirm the user has provided an actual radiology report. If the text is not a \
radiology report, ask the user to provide one.
2. Use download_guidance_document with the relevant modality or anatomical structure \
(for example "Chest") to stage the matching ACR guidance document.
3. Use run_validator to evaluate the report against the staged ACR guidance document.

When validating, assess whether the report adheres to the ACR guidelines in the document, \
whether it is detailed enough to support a diagnosis, whether it is missing any key \
anatomical structures, and whether it meets ACR quality standards. Provide terse, \
actionable feedback. Do not summarize the report itself.

You perform document-grounded validation, not clinical diagnosis. Refer clinical \
questions to qualified healthcare professionals."""

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


@tool
def download_guidance_document(anatomical_structure: str) -> str:
    """Stage the ACR guidance PDF(s) for a modality or anatomical structure from S3.

    Lists the guidance S3 bucket and downloads every PDF whose key contains the
    given anatomical structure (e.g. "Chest") into the local guidance directory,
    ready for run_validator to use.

    Args:
        anatomical_structure: Modality or anatomical structure, e.g. "Chest".

    Returns:
        A status string listing the staged documents, or an error if none match.
    """
    if not anatomical_structure or not anatomical_structure.strip():
        return "Error: anatomical_structure parameter is required."

    s3 = _get_s3_client()
    os.makedirs(GUIDANCE_DIR, exist_ok=True)

    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    except Exception as e:
        logger.error(f"Error listing guidance bucket {BUCKET_NAME}: {e}")
        return f"Error listing guidance bucket: {e}"

    keys = [obj["Key"] for obj in response.get("Contents", [])]
    needle = anatomical_structure.strip().title()

    staged = []
    for key in keys:
        if needle in key and key.endswith(".pdf"):
            basename = os.path.basename(key)
            dest = os.path.join(GUIDANCE_DIR, basename)
            try:
                s3.download_file(BUCKET_NAME, key, dest)
            except Exception as e:
                logger.error(f"Error downloading {key}: {e}")
                return f"Error downloading guidance document {key}: {e}"
            staged.append(basename)

    if not staged:
        return (
            f"No ACR guidance document found for '{anatomical_structure}'. "
            "Please ask the user to provide the guidance document or try another structure."
        )
    return "Staged ACR guidance document(s): " + ", ".join(staged)


@tool
def run_validator(report: str) -> str:
    """Validate a radiology report against the staged ACR guidance document.

    Grounds an Amazon Bedrock ``converse`` call on the first staged ACR guideline
    PDF (see download_guidance_document) and returns terse, actionable feedback on
    the report's adherence to ACR guidelines.

    Args:
        report: The radiology report text for a given patient.

    Returns:
        Actionable validation feedback, or an error if no guidance document is staged.
    """
    if not report or not report.strip():
        return "Error: report parameter is required."

    if not os.path.isdir(GUIDANCE_DIR):
        return (
            "No ACR guidance document staged. "
            "Call download_guidance_document first with the relevant anatomical structure."
        )
    documents = [f for f in os.listdir(GUIDANCE_DIR) if f.endswith(".pdf")]
    if not documents:
        return (
            "No ACR guidance document staged. "
            "Call download_guidance_document first with the relevant anatomical structure."
        )

    prompt = (
        "Does the above radiology report adhere to the ACR guidelines mentioned in the "
        "document? Is it detailed enough to provide a diagnosis? Is the report missing any "
        "key anatomical structures? Does the report meet the quality standards of the ACR "
        "guidelines? Please provide terse actionable feedback and do not try to summarize "
        "the report itself.\n\nRadiology report:\n" + report
    )

    guidance_path = os.path.join(GUIDANCE_DIR, documents[0])
    with open(guidance_path, "rb") as f:
        pdf_bytes = f.read()

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "document": {
                        "format": "pdf",
                        "name": "ACRGuidance",
                        "source": {"bytes": pdf_bytes},
                    }
                },
                {"text": prompt},
            ],
        }
    ]
    # Sonnet 5 is a reasoning model; give it enough budget to emit a text answer
    # after any internal reasoning tokens.
    inference_config = {"maxTokens": 2000}

    client = boto3.client("bedrock-runtime")
    try:
        model_response = client.converse(
            modelId=MODEL_ID,
            messages=messages,
            inferenceConfig=inference_config,
        )
    except Exception as e:
        logger.error(f"Error during report validation: {e}")
        return f"Error validating report: {e}"

    # Sonnet 5 may return non-text content blocks (e.g. reasoning) before the text;
    # scan for the first text block, falling back to reasoning text if present.
    content_blocks = model_response["output"]["message"]["content"]
    for block in content_blocks:
        if "text" in block:
            return block["text"]
    for block in content_blocks:
        reasoning = block.get("reasoningContent", {}).get("reasoningText", {}).get("text")
        if reasoning:
            return reasoning
    return "No text feedback was returned by the model."


def create_agent() -> Agent:
    """Create and return the Radiology Report Validator Agent."""
    model = BedrockModel(model_id=MODEL_ID, streaming=True)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[download_guidance_document, run_validator],
    )
