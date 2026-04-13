"""Query tools for S3 Tables genomic variants via Athena."""

import os
import json
import time
import re
import boto3
import pandas as pd
from strands import tool

AWS_REGION = os.environ.get('AWS_REGION', 'us-west-2')
ATHENA_WORKGROUP = os.environ.get('ATHENA_WORKGROUP', 'genomics-variant-analysis')
ATHENA_CATALOG = os.environ.get('ATHENA_CATALOG', 's3tablescatalog')
ATHENA_DATABASE = os.environ.get('ATHENA_DATABASE', 'variant_db_3')
ATHENA_TABLE = os.environ.get('ATHENA_TABLE', 'genomic_variants_fixed')
VEP_OUTPUT_BUCKET = os.environ.get('VEP_OUTPUT_BUCKET', '')

BLOCKED_KEYWORDS = {'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE', 'GRANT', 'REVOKE'}


def _run_athena_query(query: str, max_results: int = 100) -> pd.DataFrame:
    """Execute Athena query and return DataFrame."""
    client = boto3.client('athena', region_name=AWS_REGION)

    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': ATHENA_DATABASE, 'Catalog': ATHENA_CATALOG},
        ResultConfiguration={'OutputLocation': f's3://{VEP_OUTPUT_BUCKET}/athena-results/'},
        WorkGroup=ATHENA_WORKGROUP
    )
    qid = response['QueryExecutionId']

    for _ in range(60):
        status = client.get_query_execution(QueryExecutionId=qid)
        state = status['QueryExecution']['Status']['State']
        if state in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
            break
        time.sleep(1)

    if state != 'SUCCEEDED':
        reason = status['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
        return pd.DataFrame({'error': [f'Query {state}: {reason}']})

    results = client.get_query_results(QueryExecutionId=qid, MaxResults=max_results + 1)
    rows = results['ResultSet']['Rows']
    if not rows:
        return pd.DataFrame()

    columns = [col.get('VarCharValue', '') for col in rows[0]['Data']]
    data = [[col.get('VarCharValue', '') for col in row['Data']] for row in rows[1:]]
    return pd.DataFrame(data, columns=columns)


def _validate_query(sql: str) -> str | None:
    """Return error message if query is unsafe, None if OK."""
    tokens = set(re.findall(r'[A-Z]+', sql.upper()))
    blocked = tokens & BLOCKED_KEYWORDS
    if blocked:
        return f"Blocked keywords: {', '.join(blocked)}. Only SELECT queries allowed."
    if not sql.strip().upper().startswith('SELECT'):
        return "Query must start with SELECT."
    return None


def _ensure_limit(sql: str, default_limit: int = 100) -> str:
    """Add LIMIT if not present."""
    if not re.search(r'\bLIMIT\b', sql, re.IGNORECASE):
        sql = sql.rstrip().rstrip(';') + f' LIMIT {default_limit}'
    return sql


@tool
def execute_query(sql_query: str) -> str:
    """Execute a SELECT query against the genomic variants Athena table.

    Use get_table_schema first to understand available columns and types.
    Only SELECT queries are allowed. A LIMIT clause is enforced automatically.

    The table is: variant_db_3.genomic_variants_fixed

    Args:
        sql_query: SQL SELECT query to execute against the genomic variants table.

    Returns:
        JSON string with query results including row count and data.
    """
    error = _validate_query(sql_query)
    if error:
        return json.dumps({"status": "error", "message": error})

    sql_query = _ensure_limit(sql_query)

    df = _run_athena_query(sql_query)

    if 'error' in df.columns:
        return json.dumps({"status": "error", "message": df['error'].iloc[0]})

    return json.dumps({
        "status": "success",
        "count": len(df),
        "columns": list(df.columns),
        "results": df.to_dict('records')
    }, indent=2)


@tool
def get_cohort_summary() -> str:
    """Get summary statistics for all samples in the genomic variants cohort.

    Returns sample count, variant counts per sample, and average quality scores.
    No parameters needed — runs a fixed aggregation query.

    Returns:
        JSON string with cohort summary statistics.
    """
    query = f"""
    SELECT
        sample_name,
        COUNT(*) as total_variants,
        COUNT(DISTINCT chrom) as chromosomes,
        ROUND(AVG(qual), 2) as avg_quality
    FROM {ATHENA_DATABASE}.{ATHENA_TABLE}
    GROUP BY sample_name
    ORDER BY sample_name
    LIMIT 100
    """

    df = _run_athena_query(query)

    if 'error' in df.columns:
        return json.dumps({"status": "error", "message": df['error'].iloc[0]})

    return json.dumps({
        "status": "success",
        "total_samples": len(df),
        "samples": df.to_dict('records')
    }, indent=2)
