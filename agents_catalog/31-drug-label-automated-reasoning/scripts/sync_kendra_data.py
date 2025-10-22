#!/usr/bin/env python3
"""
Script to trigger Kendra data source synchronization.

This script starts a sync job for a Kendra data source and optionally waits for completion.
It can be used after deploying the CloudFormation stack to ensure the knowledge base
is populated with the latest data from S3.

Usage:
    uv run python scripts/sync_kendra_data.py --index-id <index-id> --data-source-id <data-source-id>
    uv run python scripts/sync_kendra_data.py --stack-name <stack-name> [--wait]
"""

import argparse
import logging
import sys
import time
from typing import Optional, Tuple

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_stack_outputs(stack_name: str) -> dict[str, str]:
    """Get CloudFormation stack outputs."""
    try:
        cf_client = boto3.client("cloudformation")
        response = cf_client.describe_stacks(StackName=stack_name)

        if not response["Stacks"]:
            raise ValueError(f"Stack '{stack_name}' not found")

        stack = response["Stacks"][0]
        outputs = {}

        for output in stack.get("Outputs", []):
            outputs[output["OutputKey"]] = output["OutputValue"]

        return outputs

    except ClientError as e:
        logging.error(f"Failed to get stack outputs: {e}")
        raise


def extract_ids_from_stack(stack_name: str) -> Tuple[str, str]:
    """Extract Kendra index ID and data source ID from CloudFormation stack outputs."""
    outputs = get_stack_outputs(stack_name)

    index_id = outputs.get("KendraIndexId")
    data_source_id = outputs.get("KendraDataSourceId")

    if not index_id:
        raise ValueError("KendraIndexId not found in stack outputs")

    if not data_source_id:
        raise ValueError("KendraDataSourceId not found in stack outputs")

    # Extract just the data source ID (CloudFormation returns "datasource-id|index-id")
    if "|" in data_source_id:
        data_source_id = data_source_id.split("|")[0]

    logging.info(f"Found index ID: {index_id}")
    logging.info(f"Found data source ID: {data_source_id}")

    return index_id, data_source_id


def start_sync_job(index_id: str, data_source_id: str) -> str:
    """Start a Kendra data source sync job."""
    try:
        kendra_client = boto3.client("kendra")

        logging.info(
            f"Starting sync job for data source {data_source_id} in index {index_id}"
        )

        response = kendra_client.start_data_source_sync_job(
            Id=data_source_id, IndexId=index_id
        )

        execution_id = response["ExecutionId"]
        logging.info(f"Sync job started successfully with execution ID: {execution_id}")

        return execution_id

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]

        if error_code == "ConflictException":
            logging.warning("A sync job is already running for this data source")
            return ""
        else:
            logging.error(f"Failed to start sync job: {error_code} - {error_message}")
            raise


def wait_for_sync_completion(
    index_id: str, data_source_id: str, execution_id: str, timeout_minutes: int = 30
) -> bool:
    """Wait for the sync job to complete."""
    if not execution_id:
        logging.info("No execution ID provided, skipping wait")
        return True

    kendra_client = boto3.client("kendra")
    timeout_seconds = timeout_minutes * 60
    start_time = time.time()

    logging.info(
        f"Waiting for sync job {execution_id} to complete (timeout: {timeout_minutes} minutes)"
    )

    while time.time() - start_time < timeout_seconds:
        try:
            response = kendra_client.list_data_source_sync_jobs(
                Id=data_source_id, IndexId=index_id, MaxResults=10
            )

            # Find our specific execution
            for job in response.get("History", []):
                if job["ExecutionId"] == execution_id:
                    status = job["Status"]
                    logging.info(f"Sync job status: {status}")

                    if status == "SUCCEEDED":
                        logging.info("Sync job completed successfully!")
                        return True
                    elif status == "FAILED":
                        error_message = job.get("ErrorMessage", "Unknown error")
                        logging.error(f"Sync job failed: {error_message}")
                        return False
                    elif status in ["STOPPING", "ABORTED"]:
                        logging.warning(f"Sync job was {status.lower()}")
                        return False

            # Wait before checking again
            # nosemgrep arbitrary-sleep
            time.sleep(30)

        except ClientError as e:
            logging.error(f"Error checking sync job status: {e}")
            return False

    logging.warning(f"Sync job did not complete within {timeout_minutes} minutes")
    return False


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Trigger Kendra data source synchronization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync using stack name (recommended)
  uv run python scripts/sync_kendra_data.py --stack-name med-device-docs-kendra

  # Sync using explicit IDs
  uv run python scripts/sync_kendra_data.py --index-id abc123 --data-source-id def456

  # Sync and wait for completion
  uv run python scripts/sync_kendra_data.py --stack-name med-device-docs-kendra --wait
        """,
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--stack-name", help="CloudFormation stack name to get Kendra IDs from"
    )
    input_group.add_argument(
        "--index-id", help="Kendra index ID (requires --data-source-id)"
    )

    parser.add_argument(
        "--data-source-id", help="Kendra data source ID (required with --index-id)"
    )

    # Options
    parser.add_argument(
        "--wait", action="store_true", help="Wait for sync job to complete"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in minutes when waiting for completion (default: 30)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.index_id and not args.data_source_id:
        parser.error("--data-source-id is required when using --index-id")

    setup_logging(args.verbose)

    try:
        # Get Kendra IDs
        if args.stack_name:
            index_id, data_source_id = extract_ids_from_stack(args.stack_name)
        else:
            index_id = args.index_id
            data_source_id = args.data_source_id

        # Start sync job
        execution_id = start_sync_job(index_id, data_source_id)

        # Wait for completion if requested
        if args.wait and execution_id:
            success = wait_for_sync_completion(
                index_id, data_source_id, execution_id, args.timeout
            )
            if not success:
                sys.exit(1)

        logging.info("Script completed successfully")

    except NoCredentialsError:
        logging.error(
            "AWS credentials not found. Please configure your AWS credentials."
        )
        sys.exit(1)
    except Exception as e:
        logging.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
