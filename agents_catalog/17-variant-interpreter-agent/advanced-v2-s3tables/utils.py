import boto3
from pyiceberg.catalog import Catalog, load_catalog
from pyiceberg.schema import Schema
from pyiceberg.table import Table
from pyiceberg.table.sorting import SortOrder
from pyiceberg.partitioning import PartitionSpec
from uuid import uuid4
from pyarrow import Array, array, binary


def create_table(catalog: Catalog,
                 namespace: str,
                 table_name: str,
                 schema: Schema,
                 partition_spec: PartitionSpec = None,
                 sort_order: SortOrder = None) -> Table:
    """Create an Iceberg Table given the relevant information"""

    # check if the table already exists
    if catalog.table_exists(f"{namespace}.{table_name}"):
        print(f"Table {namespace}.{table_name} already exists.")
        return catalog.load_table(f"{namespace}.{table_name}")

    else:
        # Handle cases where partition_spec and/or sort_order are None
        create_table_args = {
            "identifier": f"{namespace}.{table_name}",
            "schema": schema,
            "properties": {"format-version": "2"}
        }

        if partition_spec is not None:
            create_table_args["partition_spec"] = partition_spec

        if sort_order is not None:
            create_table_args["sort_order"] = sort_order

        table = catalog.create_table(**create_table_args)
        print(f"Created table: {namespace}.{table_name}")
        print(f"Table location: {table.location()}")
        return table


def create_namespace(catalog: Catalog, namespace: str) -> None:
    """Create a namespace in the Catalog."""
    try:
        catalog.create_namespace(namespace)
        print(f"Created namespace: {namespace}")
    except Exception as e:
        if "already exists" in str(e):
            print(f"Namespace {namespace} already exists.")
        else:
            raise e


def get_aws_account_id() -> str:
    """Get AWS account ID using boto3."""
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']


def get_aws_region() -> str:
    """Get AWS region using boto3."""
    session = boto3.session.Session()
    return session.region_name or 'us-east-1'


def load_s3_tables_catalog(bucket_arn: str) -> Catalog:
    # Configure the catalog
    region = get_aws_region()
    catalog_config = {
        "type": "rest",
        "warehouse": bucket_arn,
        "uri": f"https://s3tables.{region}.amazonaws.com/iceberg",
        "rest.sigv4-enabled": "true",
        "rest.signing-name": "s3tables",
        "rest.signing-region": region
    }

    # Connect to the S3Tables catalog
    catalog = load_catalog("s3tables", **catalog_config)
    return catalog


def convert_uuids_to_arrow_array(uuids: list[uuid4]) -> Array:
    """
    Convert a list of Python UUID objects into a PyArrow string array suitable for Iceberg.
    
    This function has been updated to use StringType instead of UUIDType to match schema_1.py changes.

    Args:
        uuids: List of UUID objects to convert

    Returns:
        PyArrow Array with string type containing the UUID strings

    Example usage:
        uuids = [uuid4() for _ in range(3)]
        arrow_array = convert_uuids_to_arrow_array(uuids)
    """
    # Convert UUIDs to their string representation
    uuid_strings = [str(uuid) for uuid in uuids]

    # Create PyArrow array with string type as required by updated Iceberg schema
    return array(uuid_strings)


def retry_operation(operation, *args, max_retries=5, retry_condition=None, **kwargs):
    """
    Retry an operation with exponential backoff.

    Args:
        operation: The function to retry
        *args: Arguments to pass to the operation
        max_retries: Maximum number of retry attempts
        retry_condition: Function that takes an exception and returns True if retry should be attempted
        **kwargs: Keyword arguments to pass to the operation

    Returns:
        The result of the operation if successful

    Raises:
        The last exception encountered if all retries fail
    """
    import time

    retry_count = 0
    last_exception = None

    while retry_count < max_retries:
        try:
            result = operation(*args, **kwargs)
            return result  # Success, return the result
        except Exception as e:
            retry_count += 1
            last_exception = e

            # Check if we should retry based on the exception
            should_retry = retry_condition(e) if retry_condition else True

            if should_retry and retry_count < max_retries:
                print(f"Operation failed. Retry attempt {retry_count}/{max_retries}...")
                # Exponential backoff
                time.sleep(retry_count * 2)
            else:
                # If we shouldn't retry or we've exhausted retries, re-raise
                raise e

    # If we've exhausted all retries
    if last_exception:
        print(f"Failed after {max_retries} attempts.")
        raise last_exception
