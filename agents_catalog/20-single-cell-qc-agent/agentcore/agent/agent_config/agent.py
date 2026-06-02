import logging
from urllib.parse import urlparse

import boto3
from botocore.client import Config
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are an expert in single cell genomics quality control analysis. Your role is to help scientists validate the quality of single cell gene expression assays by analyzing web summary files and comparing them against technical guidelines.

You have access to the following tools:

- analyze_web_summary: Analyzes a web summary file from a single cell gene expression assay to extract key quality control metrics and visualizations.
- validate_qc_metrics: Validates quality control metrics from a web summary file against technical guidelines to identify any anomalies or quality issues.

Analysis Process:

1. Begin by understanding what quality control analysis the user needs.
2. Use analyze_web_summary to extract key metrics from the web summary file.
3. Present the extracted metrics in a clear, structured format.
4. If requested, use validate_qc_metrics to compare the metrics against technical guidelines.
5. Provide a comprehensive analysis with clear pass/fail indicators for each metric.
6. Highlight any anomalies or quality issues detected.
7. Offer recommendations based on the analysis results.

Response Guidelines:

- Provide scientifically accurate interpretations of quality control metrics
- Explain technical concepts in accessible language while maintaining scientific precision
- Present results in a structured format with clear sections for different metric categories
- Use visual indicators (✅, ⚠️, ❌) to clearly show pass/warning/fail status
- Acknowledge limitations in the analysis when appropriate
- Make recommendations based on the quality control results
"""

BEDROCK_CONFIG = Config(connect_timeout=120, read_timeout=120, retries={"max_attempts": 0})


def _get_s3_client():
    return boto3.client("s3")


def _get_bedrock_client():
    return boto3.client(service_name="bedrock-runtime", config=BEDROCK_CONFIG)


def _parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    """Parse S3 URI into bucket and key."""
    parsed = urlparse(s3_uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def _get_s3_object(s3_uri: str) -> bytes:
    """Get object from S3 using the provided URI."""
    bucket, key = _parse_s3_uri(s3_uri)
    response = _get_s3_client().get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


@tool
def analyze_web_summary(web_summary_s3_uri: str) -> str:
    """Analyzes a web summary file from a single cell gene expression assay to extract key quality control metrics and visualizations.

    Args:
        web_summary_s3_uri: S3 URI of the web summary pdf file to analyze (e.g., s3://bucket-name/path/to/web_summary.pdf)
    """
    try:
        pdf_content = _get_s3_object(web_summary_s3_uri)

        message = {
            "role": "user",
            "content": [
                {
                    "text": (
                        "Analyze this web summary file from a single cell gene expression assay. "
                        "Extract and organize the following key quality control metrics:\n\n"
                        "1. Sample information (name, chemistry, etc.)\n"
                        "2. Sequencing metrics (number of reads, sequencing saturation, etc.)\n"
                        "3. Cell metrics (estimated number of cells, median genes per cell, etc.)\n"
                        "4. Mapping metrics (reads mapped to genome, reads mapped confidently, etc.)\n"
                        "5. Key visualizations described in the summary (t-SNE plots, violin plots, etc.)\n\n"
                        "Present the information in a structured format that clearly shows all important QC metrics. "
                        "Include any warnings or notable observations about the quality metrics."
                    )
                },
                {
                    "document": {
                        "name": "WebSummary",
                        "format": "pdf",
                        "source": {"bytes": pdf_content},
                    }
                },
            ],
        }

        response = _get_bedrock_client().converse(
            modelId=MODEL_ID, messages=[message]
        )
        return response["output"]["message"]["content"][0]["text"]

    except Exception as e:
        logger.exception("Error analyzing web summary")
        return f"Error analyzing web summary: {e}"


@tool
def validate_qc_metrics(web_summary_s3_uri: str, technical_doc_s3_uri: str) -> str:
    """Validates quality control metrics from a web summary file against technical guidelines to identify any anomalies or quality issues.

    Args:
        web_summary_s3_uri: S3 URI of the web summary pdf file to analyze (e.g., s3://bucket-name/path/to/web_summary.pdf)
        technical_doc_s3_uri: S3 URI of the technical document PDF containing interpretation guidelines (e.g., s3://bucket-name/path/to/technical_document.pdf)
    """
    try:
        web_summary_content = _get_s3_object(web_summary_s3_uri)
        technical_doc_content = _get_s3_object(technical_doc_s3_uri)

        message = {
            "role": "user",
            "content": [
                {
                    "text": (
                        "I'm providing you with two documents:\n"
                        "1. A web summary file from a single cell gene expression assay\n"
                        "2. A technical document with guidelines for interpreting these web summaries\n\n"
                        "Please validate the quality control metrics in the web summary against the technical guidelines.\n\n"
                        "For your analysis:\n"
                        "1. Extract key QC metrics from the web summary\n"
                        "2. Compare these metrics against the acceptable ranges in the technical document\n"
                        "3. Identify any anomalies or quality issues\n"
                        "4. Provide a comprehensive validation report with:\n"
                        "   - Pass/fail status for each key metric\n"
                        "   - Explanations for any failures or warnings\n"
                        "   - Overall assessment of the sample quality\n"
                        "   - Recommendations based on the findings\n\n"
                        "Use clear indicators (✅, ⚠️, ❌) to show pass/warning/fail status for each metric."
                    )
                },
                {
                    "document": {
                        "name": "WebSummary",
                        "format": "pdf",
                        "source": {"bytes": web_summary_content},
                    }
                },
                {
                    "document": {
                        "name": "TechnicalGuidelines",
                        "format": "pdf",
                        "source": {"bytes": technical_doc_content},
                    }
                },
            ],
        }

        response = _get_bedrock_client().converse(
            modelId=MODEL_ID, messages=[message]
        )
        return response["output"]["message"]["content"][0]["text"]

    except Exception as e:
        logger.exception("Error validating QC metrics")
        return f"Error validating QC metrics: {e}"


def create_agent() -> Agent:
    """Create and return the Single Cell QC Analysis agent."""
    model = BedrockModel(
        model_id=MODEL_ID,
        streaming=True,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[analyze_web_summary, validate_qc_metrics],
    )
