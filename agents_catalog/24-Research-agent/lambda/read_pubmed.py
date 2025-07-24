# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dataclasses import dataclass
import json
import logging
import re
from strands import tool
from typing import Optional

logger = logging.getLogger("read_pubmed")

CONTENT_CHARACTER_LIMIT = 100000

# Note: Logging configuration is handled by the main application

# Bedrock configuration for content summarization
BEDROCK_MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
MAX_SUMMARY_TOKENS = 1000  # Limit for summary generation
TARGET_SUMMARY_LENGTH = 2000  # Target character count for summaries


class PMCError(Exception):
    """Base exception for PMC-related errors"""

    pass


class PMCValidationError(PMCError):
    """Invalid PMCID format"""

    pass


class PMCSourceValidationError(PMCError):
    """Invalid source URL format"""

    pass


class PMCS3Error(PMCError):
    """S3 access or download error"""

    pass


@dataclass
class PMCArticleResponse:
    """Response model for PMC article retrieval"""

    status: str
    content: Optional[str]
    message: str
    pmcid: str
    license_type: Optional[str]
    s3_path: Optional[str]
    source: Optional[str] = None

    def __post_init__(self):
        """Validate response structure after initialization"""
        self._validate_response()

    def _validate_response(self):
        """Validate response structure and values"""
        # Validate status values
        valid_statuses = {"success", "licensing_restriction", "not_found", "error"}
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of: {valid_statuses}"
            )

        # Validate license_type values
        if self.license_type is not None:
            valid_license_types = {"commercial", "non_commercial"}
            if self.license_type not in valid_license_types:
                raise ValueError(
                    f"Invalid license_type '{self.license_type}'. Must be one of: {valid_license_types}"
                )

        # Validate required fields
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("Message must be a non-empty string")

        # PMCID validation is more lenient for error responses to handle invalid input
        if self.pmcid is None:
            # Allow None for error responses when user provides None
            if self.status not in {"error", "not_found"}:
                raise ValueError("PMCID cannot be None for non-error responses")
        elif not isinstance(self.pmcid, str):
            raise ValueError("PMCID must be a string or None")
        elif (
            isinstance(self.pmcid, str)
            and not self.pmcid.strip()
            and self.status not in {"error", "not_found"}
        ):
            raise ValueError("PMCID cannot be empty for non-error responses")

        # Validate business logic constraints
        if self.status == "success":
            if self.content is None or not isinstance(self.content, str):
                raise ValueError("Success responses must include content")
            if self.license_type != "commercial":
                raise ValueError("Success responses must have commercial license_type")
            if not self.s3_path:
                raise ValueError("Success responses must include s3_path")

        elif self.status == "licensing_restriction":
            if self.content is not None:
                raise ValueError(
                    "Licensing restriction responses must not include content"
                )
            if self.license_type != "non_commercial":
                raise ValueError(
                    "Licensing restriction responses must have non_commercial license_type"
                )
            if not self.s3_path:
                raise ValueError("Licensing restriction responses must include s3_path")

        elif self.status in {"not_found", "error"}:
            if self.content is not None:
                raise ValueError("Error responses must not include content")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        result = {
            "status": self.status,
            "content": self.content,
            "message": self.message,
            "pmcid": self.pmcid,
            "license_type": self.license_type,
            "s3_path": self.s3_path,
        }

        # Add new standardized fields for generate_report compatibility
        # 'text' field contains the summarized content (Requirements 1.3)
        if self.content is not None:
            result["text"] = self.content

        # 'source' field contains the DOI URL (Requirements 1.4, 2.2)
        if self.source is not None:
            result["source"] = self.source

        return result


def _validate_pmcid(pmcid: str) -> bool:
    """
    Validate PMCID format: PMC followed by digits

    Args:
        pmcid: PMC identifier to validate

    Returns:
        bool: True if valid format, False otherwise
    """
    logger.debug(f"Validating PMCID: {pmcid} (type: {type(pmcid)})")

    if not isinstance(pmcid, str):
        logger.debug(f"PMCID validation failed: not a string (type: {type(pmcid)})")
        return False

    if not pmcid:
        logger.debug("PMCID validation failed: empty string")
        return False

    if not pmcid.startswith("PMC"):
        logger.debug(f"PMCID validation failed: does not start with 'PMC' - {pmcid}")
        return False

    pattern_match = bool(re.match(r"^PMC\d+$", pmcid))
    if not pattern_match:
        logger.debug(
            f"PMCID validation failed: does not match pattern PMC\\d+ - {pmcid}"
        )
    else:
        logger.debug(f"PMCID validation successful: {pmcid}")

    return pattern_match


def _validate_source_url(source: str) -> bool:
    """
    Validate source parameter format (URL structure)

    Args:
        source: Source URL to validate

    Returns:
        bool: True if valid URL format, False otherwise
    """
    logger.debug(f"Validating source URL: {source} (type: {type(source)})")

    if not isinstance(source, str):
        logger.debug(f"Source validation failed: not a string (type: {type(source)})")
        return False

    if not source or not source.strip():
        logger.debug("Source validation failed: empty or whitespace-only string")
        return False

    source = source.strip()

    # Basic URL format validation
    # Must start with http:// or https://
    if not (source.startswith("http://") or source.startswith("https://")):
        logger.debug(
            f"Source validation failed: does not start with http:// or https:// - {source}"
        )
        return False

    # Use regex to validate basic URL structure
    # This pattern checks for:
    # - Protocol (http/https)
    # - Domain name with at least one dot
    # - Optional path, query parameters, and fragments
    url_pattern = r"^https?://[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*(/[^\s]*)?$"

    pattern_match = bool(re.match(url_pattern, source))
    if not pattern_match:
        logger.debug(f"Source validation failed: does not match URL pattern - {source}")
    else:
        logger.debug(f"Source validation successful: {source}")

    return pattern_match


def _download_from_s3(bucket: str, key: str) -> str:
    """
    Download text content from S3 bucket using anonymous access

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        str: Downloaded text content

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
            # Use us-east-1 region for PMC Open Access bucket
            region_name="us-east-1",
            # Configure for anonymous access
            config=Config(signature_version=UNSIGNED),
        )

        logger.info(f"Attempting to download {s3_path}")

        # Download the object
        response = s3_client.get_object(Bucket=bucket, Key=key)

        # Read and decode the content
        content = response["Body"].read().decode("utf-8")

        logger.info(f"Successfully downloaded {len(content)} characters from {s3_path}")
        return content

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        request_id = e.response.get("ResponseMetadata", {}).get("RequestId", "N/A")

        logger.debug(
            f"S3 ClientError details - Code: {error_code}, Message: {error_message}, RequestId: {request_id}"
        )

        if error_code == "NoSuchKey":
            logger.debug(f"Object not found: {s3_path}")
            raise PMCS3Error(f"Article not found at {s3_path}")
        elif error_code == "NoSuchBucket":
            logger.error(f"Bucket not found: {bucket} (RequestId: {request_id})")
            raise PMCS3Error(f"S3 bucket '{bucket}' not found")
        elif error_code == "AccessDenied":
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
        # This shouldn't happen with anonymous access, but handle it
        logger.error(
            f"Credentials error during anonymous S3 access to {s3_path}: {str(e)}"
        )
        raise PMCS3Error("S3 credentials configuration error - anonymous access failed")

    except UnicodeDecodeError as e:
        logger.error(f"Failed to decode content from {s3_path} as UTF-8: {str(e)}")
        raise PMCS3Error(
            f"Content encoding error - unable to decode article text as UTF-8"
        )

    except MemoryError as e:
        logger.error(
            f"Memory error while downloading large file from {s3_path}: {str(e)}"
        )
        raise PMCS3Error(f"Article too large to process - insufficient memory")

    except Exception as e:
        logger.error(
            f"Unexpected error downloading from {s3_path}: {str(e)}", exc_info=True
        )
        raise PMCS3Error(f"Failed to download from S3: {str(e)}")


def _create_error_response(
    status: str,
    message: str,
    pmcid: str,
    license_type: Optional[str] = None,
    s3_path: Optional[str] = None,
    source: Optional[str] = None,
) -> PMCArticleResponse:
    """
    Create standardized error response

    Args:
        status: Error status type
        message: Human-readable error message
        pmcid: Original PMCID
        license_type: License type if applicable
        s3_path: S3 path if applicable
        source: Optional DOI URL to include in response

    Returns:
        PMCArticleResponse: Standardized error response
    """
    return PMCArticleResponse(
        status=status,
        content=None,
        message=message,
        pmcid=pmcid,
        license_type=license_type,
        s3_path=s3_path,
        source=source,
    )


def _create_success_response(
    content: str, pmcid: str, license_type: str, s3_path: str, source: str = None
) -> PMCArticleResponse:
    """
    Create standardized success response with summarized content

    Args:
        content: Article full text content
        pmcid: Original PMCID
        license_type: License type (commercial/non_commercial)
        s3_path: S3 path where article was found
        source: Optional DOI URL to include in response

    Returns:
        PMCArticleResponse: Standardized success response with summarized content
    """
    # Summarize content for optimal report generation
    try:
        summarized_content = _summarize_content(content, pmcid)
        logger.info(f"Content summarization successful for {pmcid}")
    except Exception as e:
        logger.error(f"Content summarization failed for {pmcid}: {str(e)}")
        # Use fallback summarization
        summarized_content = _fallback_summarization(content, pmcid)

    return PMCArticleResponse(
        status="success",
        content=summarized_content,
        message=_format_success_message(pmcid),
        pmcid=pmcid,
        license_type=license_type,
        s3_path=s3_path,
        source=source,
    )


def _create_licensing_response(
    pmcid: str, s3_path: str, source: str = None
) -> PMCArticleResponse:
    """
    Create standardized licensing restriction response

    Args:
        pmcid: Original PMCID
        s3_path: S3 path where non-commercial article was found
        source: Optional DOI URL to include in response

    Returns:
        PMCArticleResponse: Standardized licensing restriction response
    """
    return PMCArticleResponse(
        status="licensing_restriction",
        content=None,
        message=_format_licensing_restriction_message(pmcid),
        pmcid=pmcid,
        license_type="non_commercial",
        s3_path=s3_path,
        source=source,
    )


def _format_validation_error_message(pmcid: str) -> str:
    """
    Format consistent validation error message

    Args:
        pmcid: Invalid PMCID that was provided

    Returns:
        str: Formatted validation error message
    """
    return f"Invalid PMCID format: {pmcid}. Expected format: PMC followed by numbers (e.g., PMC6033041)"


def _format_source_validation_error_message(source) -> str:
    """
    Format consistent source validation error message

    Args:
        source: Invalid source URL that was provided (any type)

    Returns:
        str: Formatted source validation error message
    """
    # Handle non-string inputs
    if not isinstance(source, str):
        return f"Invalid source parameter: must be a string URL, got {type(source).__name__}. Expected format: https://doi.org/10.1234/example"

    if not source or not source.strip():
        return "Invalid source parameter: empty or missing URL. Expected format: https://doi.org/10.1234/example"

    source = source.strip()
    if not (source.startswith("http://") or source.startswith("https://")):
        return f"Invalid source URL format: {source}. URL must start with http:// or https://"

    return f"Invalid source URL format: {source}. Expected a valid URL (e.g., https://doi.org/10.1234/example)"


def _format_not_found_message(pmcid: str) -> str:
    """
    Format consistent not found error message

    Args:
        pmcid: PMCID that was not found

    Returns:
        str: Formatted not found error message
    """
    return f"Article {pmcid} is not available in the PMC Open Access Subset on AWS"


def _format_s3_error_message(pmcid: str, error_details: str) -> str:
    """
    Format consistent S3 error message

    Args:
        pmcid: PMCID being processed
        error_details: Specific error details

    Returns:
        str: Formatted S3 error message
    """
    return f"Error accessing PMC Open Access Subset for {pmcid}: {error_details}"


def _format_success_message(pmcid: str) -> str:
    """
    Format consistent success message

    Args:
        pmcid: Successfully retrieved PMCID

    Returns:
        str: Formatted success message
    """
    return f"Successfully retrieved article {pmcid}"


def _format_licensing_restriction_message(pmcid: str) -> str:
    """
    Format consistent licensing restriction message

    Args:
        pmcid: PMCID with licensing restrictions

    Returns:
        str: Formatted licensing restriction message
    """
    return f"Article {pmcid} is available in PMC Open Access Subset but not licensed for commercial use"


def _summarize_content(content: str, pmcid: str) -> str:
    """
    Summarize article content using Amazon Bedrock for optimal report generation.

    Args:
        content: Full text content of the article
        pmcid: PMC identifier for logging purposes

    Returns:
        str: Summarized content limited to approximately 2000 characters

    Raises:
        Exception: If summarization fails, returns truncated original content
    """
    from botocore.config import Config

    logger.info(f"Starting content summarization for {pmcid}")

    # Handle edge cases for very short content
    if len(content) <= TARGET_SUMMARY_LENGTH:
        logger.info(
            f"Content for {pmcid} is already short ({len(content)} chars), returning as-is"
        )
        return content

    # Handle edge cases for very long content - pre-truncate to manageable size
    if len(content) > CONTENT_CHARACTER_LIMIT:  # 100KB limit for processing
        logger.warning(
            f"Content for {pmcid} is very long ({len(content)} chars), pre-truncating"
        )
        content = (
            content[:CONTENT_CHARACTER_LIMIT] + "... [content truncated for processing]"
        )

    try:
        # Initialize Amazon Bedrock client
        try:
            # Configure extended timeout for long-running AI synthesis requests
            bedrock_config = Config(
                read_timeout=3600,  # 3600 seconds (1 hour) for long AI processing
                connect_timeout=60,  # 60 seconds for connection establishment
                retries={"max_attempts": 3, "mode": "standard"},
            )

            boto_session = boto3.Session()
            bedrock_client = boto_session.client(
                "bedrock-runtime", config=bedrock_config
            )
            logger.debug(f"Initialized Bedrock client for {pmcid}")
        except NoCredentialsError as e:
            logger.error(f"AWS credentials not found for summarization of {pmcid}")
            raise RuntimeError(
                "AWS credentials not configured for content summarization"
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client for {pmcid}: {str(e)}")
            raise RuntimeError(
                f"Failed to initialize AI service for summarization: {str(e)}"
            ) from e

        # Prepare summarization prompt
        prompt = (
            f"Please provide a concise scientific summary of the following research article. "
            f"Focus on key findings, methodology, and conclusions. "
            f"Preserve scientific accuracy and important details. "
            f"Limit the summary to approximately {TARGET_SUMMARY_LENGTH} characters. "
            f"Maintain the technical language appropriate for researchers.\n\n"
            f"Article content:\n{content}"
        )

        # Prepare request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": MAX_SUMMARY_TOKENS,
        }

        request_json = json.dumps(request_body)
        logger.debug(f"Prepared summarization request for {pmcid}")

        # Make the API call
        response = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=request_json,
        )

        # Parse response
        response_body = json.loads(response["body"].read())

        # Extract summary from response
        if "content" in response_body and len(response_body["content"]) > 0:
            summary = response_body["content"][0].get("text", "")
            if summary:
                logger.info(
                    f"Successfully generated summary for {pmcid} ({len(summary)} chars)"
                )
                return summary
            else:
                logger.warning(f"Empty summary received for {pmcid}")
                raise ValueError("Empty summary received from AI service")
        else:
            logger.warning(f"Invalid response structure for {pmcid}")
            raise ValueError("Invalid response structure from AI service")

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"Bedrock API error for {pmcid} ({error_code}): {error_message}")
        # Fall back to truncated content
        return _fallback_summarization(content, pmcid)

    except Exception as e:
        logger.error(f"Unexpected error during summarization for {pmcid}: {str(e)}")
        # Fall back to truncated content
        return _fallback_summarization(content, pmcid)


def _fallback_summarization(content: str, pmcid: str) -> str:
    """
    Fallback summarization strategy when AI summarization fails.

    Args:
        content: Full text content
        pmcid: PMC identifier for logging

    Returns:
        str: Intelligently truncated content
    """
    logger.info(f"Using fallback summarization for {pmcid}")

    # Try to extract key sections if content is structured
    sections_to_extract = [
        "abstract",
        "introduction",
        "conclusion",
        "results",
        "discussion",
    ]

    # Simple heuristic: look for section headers and extract key parts
    content_lower = content.lower()
    extracted_parts = []

    for section in sections_to_extract:
        # Look for section headers (case insensitive)
        section_patterns = [
            f"\n{section}\n",
            f"\n{section}:",
            f"\n{section.upper()}\n",
            f"\n{section.upper()}:",
            f"\n{section.capitalize()}\n",
            f"\n{section.capitalize()}:",
        ]

        for pattern in section_patterns:
            if pattern.lower() in content_lower:
                # Find the section start
                start_idx = content_lower.find(pattern.lower())
                if start_idx != -1:
                    # Extract a reasonable chunk (up to 500 chars)
                    section_start = start_idx + len(pattern)
                    section_end = min(section_start + 500, len(content))

                    # Try to end at a sentence boundary
                    section_text = content[section_start:section_end]
                    last_period = section_text.rfind(".")
                    if last_period > 100:  # Only if we have a reasonable amount of text
                        section_text = section_text[: last_period + 1]

                    extracted_parts.append(
                        f"{section.capitalize()}: {section_text.strip()}"
                    )
                    break

    # If we extracted sections, combine them
    if extracted_parts:
        fallback_summary = "\n\n".join(extracted_parts)
        if len(fallback_summary) <= TARGET_SUMMARY_LENGTH:
            logger.info(
                f"Fallback extraction successful for {pmcid} ({len(fallback_summary)} chars)"
            )
            return fallback_summary

    # Final fallback: intelligent truncation from the beginning
    if len(content) > TARGET_SUMMARY_LENGTH:
        truncated = content[:TARGET_SUMMARY_LENGTH]
        # Try to end at a sentence boundary
        last_period = truncated.rfind(".")
        if last_period > TARGET_SUMMARY_LENGTH * 0.8:  # Only if we don't lose too much
            truncated = truncated[: last_period + 1]

        truncated += "... [content truncated]"
        logger.info(f"Fallback truncation applied for {pmcid} ({len(truncated)} chars)")
        return truncated

    logger.info(
        f"Fallback: returning original content for {pmcid} ({len(content)} chars)"
    )
    return content


@tool
def read_pubmed(pmcid: str, source: str = None) -> dict:
    """
    Retrieve full text of PMC article from S3.

    Args:
        pmcid: PMC identifier (e.g., "PMC6033041")
        source: Optional DOI URL to include in the response for citation purposes

    Returns:
        dict: Object with "source" (DOI/URL) and "text" (content/summary) keys
    """
    logger.info(f"Starting read_pubmed for PMCID: {pmcid}")

    try:
        # Step 1: Validate PMCID format
        if not _validate_pmcid(pmcid):
            logger.warning(f"Invalid PMCID format: {pmcid}")
            raise PMCValidationError(_format_validation_error_message(pmcid))

        # Step 2: Validate source parameter if provided
        if source is not None and not _validate_source_url(source):
            logger.warning(f"Invalid source URL format: {source}")
            raise PMCSourceValidationError(
                _format_source_validation_error_message(source)
            )

        # S3 configuration
        bucket = "pmc-oa-opendata"
        commercial_key = f"oa_comm/txt/all/{pmcid}.txt"
        noncommercial_key = f"oa_noncomm/txt/all/{pmcid}.txt"
        commercial_s3_path = f"s3://{bucket}/{commercial_key}"
        noncommercial_s3_path = f"s3://{bucket}/{noncommercial_key}"

        # Step 3: Check commercial bucket first (priority)
        try:
            logger.debug(f"Checking commercial bucket for {pmcid}")
            content = _download_from_s3(bucket, commercial_key)

            logger.info(f"Successfully retrieved commercial article {pmcid}")
            response = _create_success_response(
                content, pmcid, "commercial", commercial_s3_path, source
            )
            # Return simplified object with just source and text
            logger.info(
                f"Content summary:\n#############################\n{response.content[:1000]}...\n#############################"
            )
            return {
                "source": source
                or f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
                "text": response.content,
            }

        except PMCS3Error as e:
            # If it's not a "not found" error, this is a serious S3 issue
            if "not found" not in str(e).lower():
                logger.error(f"S3 error accessing commercial bucket: {str(e)}")
                raise e

            # Article not found in commercial bucket, continue to non-commercial check
            logger.debug(f"Article {pmcid} not found in commercial bucket")

        # Step 4: Check non-commercial bucket
        try:
            logger.info(f"Checking non-commercial bucket for {pmcid}")
            # We don't actually download the content for non-commercial articles
            # Just check if it exists by attempting to get object metadata
            from botocore import UNSIGNED
            from botocore.config import Config

            s3_client = boto3.client(
                "s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED)
            )

            # Use head_object to check existence without downloading content
            s3_client.head_object(Bucket=bucket, Key=noncommercial_key)

            logger.info(f"Found non-commercial article {pmcid}")
            response = _create_licensing_response(pmcid, noncommercial_s3_path, source)
            # Return simplified object with licensing restriction message
            return {
                "source": source
                or f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
                "text": response.message,
            }

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code in ["NoSuchKey", "404"]:
                # Article not found in either bucket
                logger.info(
                    f"Article {pmcid} not found in either commercial or non-commercial buckets"
                )
                response = _create_error_response(
                    "not_found", _format_not_found_message(pmcid), pmcid, source=source
                )
                # Return simplified object with error message
                return {
                    "source": source
                    or f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
                    "text": response.message,
                }
            else:
                # Other S3 error during non-commercial check
                error_message = e.response.get("Error", {}).get("Message", str(e))
                logger.error(
                    f"S3 ClientError checking non-commercial bucket ({error_code}): {error_message}"
                )
                raise PMCS3Error(
                    f"S3 access error during non-commercial check: {error_message}"
                )

        except Exception as e:
            # Unexpected error during non-commercial check
            logger.error(f"Unexpected error checking non-commercial bucket: {str(e)}")
            raise PMCS3Error(f"Unexpected error during non-commercial check: {str(e)}")

    except PMCValidationError as e:
        # Handle PMCID validation errors gracefully
        logger.warning(f"PMCID validation error: {str(e)}")
        response = _create_error_response("error", str(e), pmcid, source=source)
        return {
            "source": source or f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
            "text": response.message,
        }

    except PMCSourceValidationError as e:
        # Handle source validation errors gracefully
        logger.warning(f"Source validation error: {str(e)}")
        response = _create_error_response("error", str(e), pmcid, source=source)
        return {
            "source": source or f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
            "text": response.message,
        }

    except PMCS3Error as e:
        # Handle S3-specific errors gracefully
        logger.error(f"S3 error: {str(e)}")
        response = _create_error_response(
            "error", _format_s3_error_message(pmcid, str(e)), pmcid, source=source
        )
        return {
            "source": source or f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
            "text": response.message,
        }

    except PMCError as e:
        # Handle other PMC-specific errors gracefully
        logger.error(f"PMC error: {str(e)}")
        response = _create_error_response("error", str(e), pmcid, source=source)
        return {
            "source": source or f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
            "text": response.message,
        }

    except Exception as e:
        # Handle any unexpected errors gracefully
        logger.error(f"Unexpected error in read_pubmed: {str(e)}", exc_info=True)
        response = _create_error_response(
            "error",
            f"An unexpected error occurred while processing {pmcid}: {str(e)}",
            pmcid,
            source=source,
        )
        return {
            "source": source or f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
            "text": response.message,
        }


# def _get_api_key_params(base_params: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Add NCBI API key to request parameters if available.

#     Args:
#         base_params: Base request parameters dictionary

#     Returns:
#         Parameters dictionary with API key added if available
#     """
#     api_key = os.getenv("NCBI_API_KEY")

#     # If API key exists and is not empty, add it to parameters
#     if api_key and api_key.strip():
#         # Create a new dictionary to avoid modifying the original
#         params_with_key = base_params.copy()
#         params_with_key["api_key"] = api_key
#         return params_with_key

#     # Return original parameters if no API key or empty string
#     return base_params


if __name__ == "__main__":
    # Example usage for testing
    result = read_pubmed("PMC6033041")
    print(result)
