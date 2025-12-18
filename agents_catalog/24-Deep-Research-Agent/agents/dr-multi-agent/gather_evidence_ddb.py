# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import logging
import os
import re
import uuid
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from paperqa import Settings, ask
from paperqa.settings import (
    AgentSettings,
    AnswerSettings,
    IndexSettings,
    ParsingSettings,
)
from strands import tool
import warnings
warnings.filterwarnings("ignore", module="litellm")

# Global configuration for commercial use filtering
COMMERCIAL_USE_ONLY = os.getenv("COMMERCIAL_USE_ONLY", True)

# Paper-QA Model Configuration
PAPERQA_LLM = os.getenv("PAPERQA_LLM", "global.anthropic.claude-sonnet-4-20250514-v1:0")
PAPERQA_SUMMARY_LLM = os.getenv(
    "PAPERQA_SUMMARY_LLM", "bedrock/openai.gpt-oss-120b-1:0"
)
PAPERQA_AGENT_LLM = os.getenv(
    "PAPERQA_AGENT_LLM", "global.anthropic.claude-sonnet-4-20250514-v1:0"
)
PAPERQA_EMBEDDING = os.getenv(
    "PAPERQA_EMBEDDING", "bedrock/amazon.titan-embed-text-v2:0"
)
PAPERQA_AGENT_TYPE = os.getenv("PAPERQA_AGENT_TYPE", "fake")
PAPERQA_EVIDENCE_K = os.getenv("EVIDENCE_K", 5)
PAPERQA_EVIDENCE_SUMMARY_LENGTH = os.getenv("EVIDENCE_SUMMARY_LENGTH", "25 to 50 words")

# Dynamo DB Configuration
EVIDENCE_TABLE_NAME = os.getenv("EVIDENCE_TABLE_NAME", "deep-research-evidence")

# Configure logging
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("gather_evidence")
logger.level = logging.INFO

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb")


# Configure logging - suppress Rich logging errors from PaperQA
def _configure_paperqa_logging():
    """
    Configure logging to suppress Rich handler errors from PaperQA.

    PaperQA uses Rich logging handlers that fail in Jupyter notebook contexts
    when called from background threads, causing LookupError for parent_header.
    This function replaces Rich handlers with standard StreamHandlers.
    """
    # Get all loggers that might be using Rich handlers
    paperqa_loggers = [
        "paperqa",
        "paperqa.agents",
        "paperqa.agents.tools",
        "paperqa.agents.main",
        "paperqa.agents.env",
        "aviary",
        "aviary.env",
    ]

    for logger_name in paperqa_loggers:
        pqa_logger = logging.getLogger(logger_name)
        # Remove all handlers (including Rich handlers)
        pqa_logger.handlers.clear()
        # Set to WARNING to reduce noise, or ERROR to silence almost everything
        pqa_logger.setLevel(logging.WARNING)
        # Prevent propagation to avoid parent loggers with Rich handlers
        pqa_logger.propagate = False


class PMCError(Exception):
    """Base exception for PMC-related errors"""

    pass


class PMCValidationError(PMCError):
    """Invalid PMCID format"""

    pass


class PMCS3Error(PMCError):
    """S3 access or download error"""

    pass


def _validate_pmc_id(pmc_id: str) -> bool:
    """
    Validate PMCID format: PMC followed by digits

    Args:
        pmc_id: PMC identifier to validate

    Returns:
        bool: True if valid format, False otherwise
    """
    logger.debug(f"Validating PMCID: {pmc_id} (type: {type(pmc_id)})")

    if not isinstance(pmc_id, str):
        logger.debug(f"PMCID validation failed: not a string (type: {type(pmc_id)})")
        return False

    if not pmc_id:
        logger.debug("PMCID validation failed: empty string")
        return False

    if not pmc_id.startswith("PMC"):
        logger.debug(f"PMCID validation failed: does not start with 'PMC' - {pmc_id}")
        return False

    pattern_match = bool(re.match(r"^PMC\d+$", pmc_id))
    if not pattern_match:
        logger.debug(
            f"PMCID validation failed: does not match pattern PMC\\d+ - {pmc_id}"
        )
    else:
        logger.debug(f"PMCID validation successful: {pmc_id}")

    return pattern_match


def _download_from_s3(bucket: str, key: str, local_folder: str = "my_papers") -> str:
    """
    Download file from S3 bucket to local folder using anonymous access

    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_folder: Local folder to save the file (default: "my_papers")

    Returns:
        str: Path to the downloaded file

    Raises:
        PMCS3Error: If download fails
    """
    s3_path = f"s3://{bucket}/{key}"

    try:
        # Configure S3 client for anonymous access
        from botocore import UNSIGNED
        from botocore.config import Config

        logger.debug(f"Configuring S3 client for anonymous access to {s3_path}")

        s3_client = boto3.client(
            "s3",
            region_name="us-east-1",
            config=Config(signature_version=UNSIGNED),
        )

        # Create local folder if it doesn't exist
        os.makedirs(local_folder, exist_ok=True)
        logger.debug(f"Ensured local folder exists: {local_folder}")

        # Extract filename from key
        filename = os.path.basename(key)
        local_path = os.path.join(local_folder, filename)

        logger.info(f"Attempting to download {s3_path} to {local_path}")

        # Download the file
        s3_client.download_file(bucket, key, local_path)

        logger.info(f"Successfully downloaded file to {local_path}")
        return local_path

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        request_id = e.response.get("ResponseMetadata", {}).get("RequestId", "N/A")

        logger.debug(
            f"S3 ClientError details - Code: {error_code}, Message: {error_message}, RequestId: {request_id}"
        )

        if error_code == "404" or error_code == "NoSuchKey":
            logger.debug(f"Object not found: {s3_path}")
            raise PMCS3Error(f"Article not found at {s3_path}")
        elif error_code == "NoSuchBucket":
            logger.error(f"Bucket not found: {bucket} (RequestId: {request_id})")
            raise PMCS3Error(f"S3 bucket '{bucket}' not found")
        elif error_code == "403" or error_code == "AccessDenied":
            logger.error(f"Access denied to {s3_path} (RequestId: {request_id})")
            raise PMCS3Error(f"Access denied to {s3_path}")
        elif error_code in ["ServiceUnavailable", "SlowDown", "RequestTimeout"]:
            logger.warning(
                f"S3 service issue ({error_code}) for {s3_path}: {error_message}"
            )
            raise PMCS3Error(f"S3 service temporarily unavailable: {error_message}")
        elif error_code in ["InternalError", "InternalServerError"]:
            logger.error(
                f"S3 internal error for {s3_path}: {error_message} (RequestId: {request_id})"
            )
            raise PMCS3Error(f"S3 internal server error: {error_message}")
        else:
            logger.error(
                f"S3 ClientError ({error_code}) for {s3_path}: {error_message} (RequestId: {request_id})"
            )
            raise PMCS3Error(f"S3 access error ({error_code}): {error_message}")

    except NoCredentialsError as e:
        logger.error(
            f"Credentials error during anonymous S3 access to {s3_path}: {str(e)}"
        )
        raise PMCS3Error("S3 credentials configuration error - anonymous access failed")

    except OSError as e:
        logger.error(f"File system error while saving to {local_path}: {str(e)}")
        raise PMCS3Error(f"Failed to save file to disk: {str(e)}")

    except Exception as e:
        logger.error(
            f"Unexpected error downloading from {s3_path}: {str(e)}", exc_info=True
        )
        raise PMCS3Error(f"Failed to download from S3: {str(e)}")


def _save_to_db(
    evidence_id: str,
    question: str,
    answer: str,
    source: str,
    context: list,
) -> dict:
    """Save gathered evidence record to DynamoDb table

    Args:
        evidence_id: Unique identifier for the evidence record
        question: Question asked
        answer: Answer text
        source: Reference to source document
        context: List of context summaries

    Returns:
        dict: DynamoDB response

    Raises:
        ValueError: If table doesn't exist
        ClientError: If DynamoDB operation fails
    """
    logger.info(f"Saving record to {EVIDENCE_TABLE_NAME}")

    record = {
        "evidence_id": evidence_id,
        "question": question,
        "answer": answer,
        "source": source,
        "context": context,
    }
    logger.info(record)

    try:
        # Verify table exists
        table = dynamodb.Table(EVIDENCE_TABLE_NAME)
        table.load()  # This will raise an exception if table doesn't exist

        # Put record
        response = table.put_item(Item=record)
        logger.debug(response)
        logger.info(f"Successfully saved record with evidence_id: {evidence_id}")

        return response

    except dynamodb.meta.client.exceptions.ResourceNotFoundException:
        error_msg = f"DynamoDB table '{EVIDENCE_TABLE_NAME}' does not exist"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"DynamoDB error ({error_code}): {error_message}")
        raise


def gather_evidence(pmc_id: str, question: str) -> dict:
    """
    Answer questions about a PMC article using paper-qa for intelligent retrieval.

    This function downloads a scientific paper from PubMed Central and uses the paper-qa
    library to answer specific questions about the paper with sources.

    Args:
        pmc_id: PMC identifier (e.g., "PMC6033041")
        question: The question to answer about the paper

    Returns:
        dict: ToolResult with status and content containing the answer and sources
    """
    logger.info(f"Starting gather_evidence for PMCID: {pmc_id}, question: {question}")

    # Configure PaperQA logging to avoid Rich handler errors in Jupyter
    _configure_paperqa_logging()

    # source = source or f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/",

    try:
        # Step 1: Validate PMCID format
        if not _validate_pmc_id(pmc_id):
            error_msg = f"Invalid PMCID format: {pmc_id}. Expected format: PMC followed by numbers (e.g., PMC6033041)"
            logger.warning(error_msg)
            return {
                "status": "error",
                "content": [
                    {"text": error_msg},
                    {"json": {"question": question, "source": pmc_id}},
                ],
            }

        # S3 configuration
        bucket = "pmc-oa-opendata"
        commercial_key = f"oa_comm/txt/all/{pmc_id}.txt"
        noncommercial_key = f"oa_noncomm/txt/all/{pmc_id}.txt"
        local_text_folder = f"my_papers/{pmc_id}/txt"
        local_index_folder = f"my_papers/{pmc_id}/index"

        # Step 2: Try to download from commercial bucket first
        local_file_path = None
        try:
            logger.debug(f"Checking commercial bucket for {pmc_id}")
            local_file_path = _download_from_s3(
                bucket, commercial_key, local_folder=local_text_folder
            )
            logger.info(f"Successfully retrieved commercial article {pmc_id}")

        except PMCS3Error as e:
            if "not found" not in str(e).lower():
                logger.warning(f"S3 error accessing commercial bucket: {str(e)}")
                raise e

            # Try non-commercial bucket
            logger.debug(f"Article {pmc_id} not found in commercial bucket")
            if COMMERCIAL_USE_ONLY:
                logger.warning(
                    f"Article {pmc_id} not found in commercial bucket and COMMERCIAL_USE_ONLY is set to True"
                )
                raise PMCS3Error(
                    f"Article {pmc_id} not found in commercial bucket and COMMERCIAL_USE_ONLY is set to True"
                )
            logger.info(f"Checking non-commercial bucket for {pmc_id}")

            try:
                local_file_path = _download_from_s3(
                    bucket, noncommercial_key, local_folder=local_text_folder
                )
                logger.warning(
                    f"Article {pmc_id} found in non-commercial bucket - licensing restrictions may apply"
                )

            except PMCS3Error as nc_error:
                if "not found" in str(nc_error).lower():
                    error_msg = f"Article {pmc_id} is not available in the PMC Open Access Subset on AWS"
                    logger.info(error_msg)
                    return {
                        "status": "error",
                        "content": [
                            {"text": error_msg},
                            {"json": {"question": question, "source": pmc_id}},
                        ],
                    }
                else:
                    raise nc_error

        # Step 3: Use paper-qa to answer the question
        logger.info(f"Processing paper with paper-qa for question: {question}")

        # Get the directory containing the downloaded file
        logger.debug(f"Using paper directory: {local_text_folder}")

        # Configure paper-qa settings
        settings = Settings(
            llm=PAPERQA_LLM,
            summary_llm=PAPERQA_SUMMARY_LLM,
            agent=AgentSettings(
                agent_llm=PAPERQA_AGENT_LLM,
                index=IndexSettings(
                    index_directory=local_index_folder,
                    paper_directory=local_text_folder,
                ),
                agent_type=PAPERQA_AGENT_TYPE,
            ),
            embedding=PAPERQA_EMBEDDING,
            parsing=ParsingSettings(use_doc_details=False),
            answer=AnswerSettings(
                answer_max_sources=1,
                evidence_k=PAPERQA_EVIDENCE_K,
                evidence_summary_length=PAPERQA_EVIDENCE_SUMMARY_LENGTH,
            ),
        )

        # Ask the question
        logger.info("Invoking paper-qa")
        answer = ask(question, settings=settings)

        # Format the response using Strands ToolResult format
        answer_text = answer.session.answer
        contexts = [
            {"chunk": context.text.name, "summary": context.context}
            for context in answer.session.contexts
        ]

        # Generate unique evidence ID
        evidence_id = str(uuid.uuid4())

        logger.info(f"Successfully answered question for {pmc_id}")
        logger.debug(f"Answer: {answer_text[:200]}...")
        # Save evidence record to DynamoDB
        if not evidence_id:
            logger.warning("No toolUseId found in tool_context, skipping DynamoDB save")
        else:
            try:
                db_response = _save_to_db(
                    evidence_id,
                    answer.session.question,
                    answer_text,
                    pmc_id,
                    [context.get("summary") for context in contexts],
                )
            except Exception as db_error:
                logger.error(f"Failed to save to DynamoDB: {str(db_error)}")
                # Continue execution - don't fail the tool if DB save fails
        return {
            "status": "success",
            "content": [
                {"text": answer_text},
                {
                    "json": {
                        "evidence_id": evidence_id,
                        "question": answer.session.question,
                        "source": pmc_id,
                        "context": contexts,
                    }
                },
            ],
        }

    except PMCValidationError as e:
        logger.warning(f"PMCID validation error: {str(e)}")
        return {
            "status": "error",
            "content": [
                {"text": str(e)},
                {"json": {"question": question, "source": pmc_id}},
            ],
        }

    except PMCS3Error as e:
        logger.error(f"S3 error: {str(e)}")
        error_msg = f"Error accessing PMC Open Access Subset for {pmc_id}: {str(e)}"
        return {
            "status": "error",
            "content": [
                {"text": error_msg},
                {"json": {"question": question, "source": pmc_id}},
            ],
        }

    except Exception as e:
        logger.error(
            f"Unexpected error in gather_evidence_tool: {str(e)}", exc_info=True
        )
        error_msg = f"An unexpected error occurred while processing {pmc_id}: {str(e)}"
        return {
            "status": "error",
            "content": [
                {"text": error_msg},
                {"json": {"question": question, "source": pmc_id}},
            ],
        }


@tool
def gather_evidence_tool(pmc_id: str, question: str) -> dict:
    """
    Answer questions about a PMC article using paper-qa for intelligent retrieval.

    This tool downloads a scientific paper from PubMed Central and uses the paper-qa
    library to answer specific questions about the paper with source.

    Args:
        pmc_id: PMC identifier (e.g., "PMC6033041")
        question: The question to answer about the paper

    Returns:
        dict: ToolResult with status and content containing the answer and source
    """
    return gather_evidence(pmc_id=pmc_id, question=question)


if __name__ == "__main__":
    # Example usage for testing
    result = gather_evidence(
        "PMC9438179", "How safe and effective are GLP-1 drugs for long term use?"
    )
    print(result)
