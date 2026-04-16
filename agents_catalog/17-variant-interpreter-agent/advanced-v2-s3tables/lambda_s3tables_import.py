"""
Container-based Lambda handler for importing VEP-annotated VCFs into S3 Tables.
Replaces the Batch job approach — runs directly in Lambda with pyiceberg/pyarrow.
"""
import json
import os
import boto3
from datetime import datetime

# Import the existing VCF loading logic
from load_vcf_schema3 import process_vcf_file, get_table
from schema_3 import create_schema_tables
from utils import load_s3_tables_catalog, create_namespace
import load_vcf_schema3

DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'genomics-vep-s3tables-dynamotable')
TABLE_BUCKET_ARN = os.environ.get('TABLE_BUCKET_ARN', '')
NAMESPACE = 'variant_db_3'


def update_dynamodb(sample_id, stage, extra_attrs=None):
    """Update DynamoDB processing status."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(DYNAMODB_TABLE)
    update_expr = 'SET #status = :status, ProcessingStage = :stage, UpdatedAt = :updated'
    attr_names = {'#status': 'Status'}
    attr_values = {
        ':status': stage,
        ':stage': stage,
        ':updated': datetime.now().isoformat()
    }
    if extra_attrs:
        for k, v in extra_attrs.items():
            update_expr += f', {k} = :{k}'
            attr_values[f':{k}'] = v

    try:
        table.update_item(
            Key={'SampleID': sample_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=attr_values
        )
    except Exception as e:
        print(f"DynamoDB update warning: {e}")


def find_vep_output(output_uri):
    """Find the annotated VCF file in the workflow output."""
    s3 = boto3.client('s3')

    # Parse S3 URI
    if not output_uri.startswith('s3://'):
        return None
    parts = output_uri.replace('s3://', '').split('/', 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ''

    # Search for .ann.vcf.gz files
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('.ann.vcf.gz') or key.endswith('.ann.vcf'):
                return f's3://{bucket}/{key}'

    return None


def handler(event, context):
    """Lambda handler — triggered by EventBridge on workflow completion."""
    print(f"Event: {json.dumps(event)}")

    detail = event.get('detail', {})
    run_id = detail.get('runId') or detail.get('id')
    status = detail.get('status')
    output_uri = detail.get('runOutputUri', '')

    print(f"Run ID: {run_id}, Status: {status}, Output: {output_uri}")

    if status != 'COMPLETED':
        print(f"Skipping — status is {status}")
        return {'statusCode': 200, 'body': f'Status: {status}'}

    # Find sample ID from DynamoDB or derive from run
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(DYNAMODB_TABLE)

    sample_id = None
    try:
        # Use RunIDIndex GSI instead of scan for O(1) lookup
        response = table.query(
            IndexName='RunIDIndex',
            KeyConditionExpression='RunID = :rid',
            ExpressionAttributeValues={':rid': run_id}
        )
        if response.get('Items'):
            sample_id = response['Items'][0]['SampleID']
            output_uri = output_uri or response['Items'][0].get('OutputPrefix', '')
    except Exception as e:
        print(f"DynamoDB lookup warning: {e}")

    if not sample_id:
        # Derive from run name or use run_id
        run_name = detail.get('runName', '')
        sample_id = run_name.replace('vep-', '').rsplit('-', 1)[0] if run_name else run_id
        print(f"Derived sample_id: {sample_id}")

    # Find the annotated VCF
    vep_file = find_vep_output(output_uri)
    if not vep_file:
        msg = f"No annotated VCF found in {output_uri}"
        print(msg)
        update_dynamodb(sample_id, 'S3_TABLES_IMPORT_FAILED')
        return {'statusCode': 404, 'body': msg}

    print(f"Found VEP output: {vep_file}")
    update_dynamodb(sample_id, 'S3_TABLES_IMPORTING')

    try:
        # Setup S3 Tables
        load_vcf_schema3.bucket_arn = TABLE_BUCKET_ARN
        catalog = load_s3_tables_catalog(TABLE_BUCKET_ARN)
        create_namespace(catalog, NAMESPACE)
        create_schema_tables(catalog, NAMESPACE)

        # Get table and schema
        iceberg_table = get_table()
        pyarrow_schema = iceberg_table.schema().as_arrow()

        # Process VCF and load into S3 Tables
        process_vcf_file(vep_file, sample_id, iceberg_table, pyarrow_schema)

        update_dynamodb(sample_id, 'S3_TABLES_IMPORTED',
                        {'VepOutputFile': vep_file, 'ImportedAt': datetime.now().isoformat()})

        msg = f"Successfully imported {sample_id} from {vep_file}"
        print(msg)
        return {'statusCode': 200, 'body': msg}

    except Exception as e:
        msg = f"Import failed for {sample_id}: {str(e)}"
        print(msg)
        import traceback
        traceback.print_exc()
        update_dynamodb(sample_id, 'S3_TABLES_IMPORT_FAILED')
        return {'statusCode': 500, 'body': msg}
