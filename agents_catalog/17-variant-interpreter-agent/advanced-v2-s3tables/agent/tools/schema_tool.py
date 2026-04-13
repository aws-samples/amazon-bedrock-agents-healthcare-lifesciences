"""Schema retrieval tool for S3 Tables genomic variants."""

import os
import json
import sys
from strands import tool

# Add project root to path for utils import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

HARDCODED_SCHEMA = {
    "table": "genomic_variants_fixed",
    "namespace": "variant_db_3",
    "columns": [
        {"name": "sample_name", "type": "STRING", "required": True, "notes": "Partition key. e.g. 'HG00096'"},
        {"name": "variant_name", "type": "STRING", "required": True, "notes": "VCF ID field, usually '.'"},
        {"name": "chrom", "type": "STRING", "required": True, "notes": "Partition key. e.g. '22'"},
        {"name": "pos", "type": "LONG", "required": True, "notes": "Genomic position"},
        {"name": "ref", "type": "STRING", "required": True, "notes": "Reference allele"},
        {"name": "alt", "type": "LIST<STRING>", "required": True, "notes": "Alternate allele(s)"},
        {"name": "qual", "type": "DOUBLE", "required": False, "notes": "Quality score"},
        {"name": "filter", "type": "STRING", "required": False, "notes": "'PASS' or filter reason"},
        {"name": "genotype", "type": "STRING", "required": False, "notes": "e.g. '0|0', '0|1', '1|1'"},
        {"name": "info", "type": "MAP<STRING,STRING>", "required": False, "notes": "INFO fields including VEP CSQ annotations. Access with info['CSQ']. CSQ is pipe-delimited: Allele|Consequence|IMPACT|SYMBOL|Gene|..."},
        {"name": "attributes", "type": "MAP<STRING,STRING>", "required": False, "notes": "FORMAT/sample fields (GT, DP, GQ, etc.)"},
        {"name": "is_reference_block", "type": "BOOLEAN", "required": False, "notes": "gVCF reference blocks"},
    ],
    "partition_keys": ["sample_name", "chrom"],
    "source": "hardcoded_fallback"
}


def _schema_from_catalog():
    """Retrieve schema from S3 Tables catalog via pyiceberg."""
    from utils import load_s3_tables_catalog

    bucket_arn = os.environ.get('S3_TABLE_BUCKET_ARN',
        f"arn:aws:s3tables:{os.environ.get('AWS_REGION', 'us-west-2')}:"
        f"{os.environ.get('AWS_ACCOUNT_ID', '')}:bucket/"
        f"genomics-variant-tables-{os.environ.get('AWS_ACCOUNT_ID', '')}")
    namespace = os.environ.get('ATHENA_DATABASE', 'variant_db_3')
    table_name = os.environ.get('ATHENA_TABLE', 'genomic_variants_fixed')

    catalog = load_s3_tables_catalog(bucket_arn)
    table = catalog.load_table(f"{namespace}.{table_name}")
    schema = table.schema()

    columns = []
    for field in schema.fields:
        columns.append({
            "name": field.name,
            "type": str(field.field_type),
            "required": field.required,
            "notes": field.doc or ""
        })

    partition_keys = [f.name for f in table.spec().fields] if table.spec().fields else []

    return {
        "table": table_name,
        "namespace": namespace,
        "columns": columns,
        "partition_keys": partition_keys,
        "source": "s3_tables_catalog"
    }


@tool
def get_table_schema() -> str:
    """Retrieve the schema of the genomic variants table stored in S3 Tables.

    Call this tool FIRST before writing any SQL queries. It returns column names,
    types, partition keys, and notes about special fields like the VEP CSQ annotations
    in the info MAP column.

    Returns:
        JSON string with table schema including columns, types, and notes.
    """
    try:
        result = _schema_from_catalog()
    except Exception as e:
        result = {**HARDCODED_SCHEMA, "catalog_error": str(e)}

    return json.dumps(result, indent=2)
