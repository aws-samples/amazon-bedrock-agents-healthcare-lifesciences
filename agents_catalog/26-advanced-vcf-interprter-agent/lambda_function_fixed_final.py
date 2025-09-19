import json
import os
import boto3
import time
from datetime import datetime
import logging
from urllib.parse import unquote_plus

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
omics = boto3.client('omics')
dynamodb = boto3.client('dynamodb')
lakeformation = boto3.client('lakeformation')
glue = boto3.client('glue')
s3 = boto3.client('s3')

# Get environment variables
VARIANT_STORE_NAME = os.environ['VARIANT_STORE_NAME']
VARIANT_STORE_ID = os.environ['VARIANT_STORE_ID']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
VEP_WORKFLOW_ID = os.environ['VEP_WORKFLOW_ID']  # Added for VEP workflow
VEP_ROLE_ARN = os.environ['VEP_ROLE_ARN']  # Added for VEP workflow
VEP_OUTPUT_PREFIX = os.environ['VEP_OUTPUT_PREFIX']  # Added for VEP workflow

def lambda_handler(event, context):
    """Handle S3 events and process VCF files"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Process each record in the event
        for record in event['Records']:
            if record['eventName'].startswith('ObjectCreated:'):
                bucket = record['s3']['bucket']['name']
                key = unquote_plus(record['s3']['object']['key'])
                
                if not key.endswith('.vcf.gz'):
                    logger.info(f"Skipping non-VCF file: {key}")
                    continue
                
                # Extract sample ID from the file name
                sample_id = key.split('/')[-1].split('.')[0]
                s3_uri = f"s3://{bucket}/{key}"
                
                # First, run the VEP workflow
                vep_run_id = start_vep_workflow(sample_id, s3_uri)
                if not vep_run_id:
                    logger.error(f"Failed to start VEP workflow for {sample_id}")
                    continue
                
                # Wait for VEP workflow to complete
                vep_output_uri = wait_for_vep_workflow(vep_run_id)
                if not vep_output_uri:
                    logger.error(f"VEP workflow failed for {sample_id}")
                    continue
                
                # Now start the variant import job with the VEP output
                import_job_id = start_variant_import(sample_id, vep_output_uri)
                if not import_job_id:
                    logger.error(f"Failed to start variant import for {sample_id}")
                    continue
                
                # Create initial DynamoDB entry
                create_initial_record(sample_id, vep_output_uri, import_job_id)
                
                logger.info(f"Successfully processed {sample_id}")
                
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        raise

def start_vep_workflow(sample_id, input_vcf_uri):
    """Start the VEP workflow for a VCF file"""
    try:
        output_uri = f"s3://{VEP_OUTPUT_PREFIX}/{sample_id}/"
        
        response = omics.start_run(
            workflowId=VEP_WORKFLOW_ID,
            name=f"vep-{sample_id}",
            roleArn=VEP_ROLE_ARN,
            outputUri=output_uri,
            parameters={
                "id": sample_id,
                "vcf": input_vcf_uri,
                "ecr_registry": "public.ecr.aws/aws-genomics",  # Update with your ECR registry
                "vep_cache": "s3://aws-genomics-static-files/vep/cache/",  # Update with your VEP cache location
                "vep_genome": "GRCh38",
                "vep_species": "homo_sapiens",
                "vep_cache_version": "110"
            }
        )
        
        logger.info(f"Started VEP workflow for {sample_id}: {response['id']}")
        return response['id']
        
    except Exception as e:
        logger.error(f"Error starting VEP workflow: {str(e)}")
        return None

def wait_for_vep_workflow(run_id):
    """Wait for VEP workflow to complete and return output VCF location"""
    try:
        while True:
            response = omics.get_run(runId=run_id)
            status = response['status']
            
            if status == 'COMPLETED':
                # Get the output VCF file location from the workflow output
                output_uri = f"{response['outputUri']}/output.vcf.gz"  # Adjust based on your workflow output path
                logger.info(f"VEP workflow completed successfully: {output_uri}")
                return output_uri
            elif status in ['FAILED', 'CANCELLED', 'TERMINATED']:
                logger.error(f"VEP workflow failed with status {status}")
                return None
            
            time.sleep(30)  # Wait 30 seconds before checking again
            
    except Exception as e:
        logger.error(f"Error checking VEP workflow status: {str(e)}")
        return None

def start_variant_import(sample_id, vcf_uri):
    """Start a variant import job"""
    try:
        response = omics.start_variant_import_job(
            variantStoreId=VARIANT_STORE_ID,
            roleArn=VEP_ROLE_ARN,
            items=[{
                'source': vcf_uri,
                'name': sample_id
            }]
        )
        
        logger.info(f"Started variant import job for {sample_id}: {response['id']}")
        return response['id']
        
    except Exception as e:
        logger.error(f"Error starting variant import: {str(e)}")
        return None

def create_initial_record(sample_id, vcf_uri, import_job_id):
    """Create initial DynamoDB record for tracking"""
    try:
        timestamp = datetime.utcnow().isoformat()
        
        dynamodb.put_item(
            TableName=DYNAMODB_TABLE,
            Item={
                'SampleID': {'S': sample_id},
                'ImportJobId': {'S': import_job_id},
                'S3Uri': {'S': vcf_uri},
                'Status': {'S': 'SUBMITTED'},
                'CreatedTime': {'S': timestamp},
                'StartTime': {'S': timestamp},
                'VariantStoreId': {'S': VARIANT_STORE_ID},
                'TargetDatabase': {'S': 'vcf_analysis_db'},
                'TargetTable': {'S': VARIANT_STORE_NAME},
                'ExpectedAthenaPath': {'S': f'vcf_analysis_db.{VARIANT_STORE_NAME}'}
            }
        )
        
        logger.info(f"Created DynamoDB record for {sample_id}")
        
    except Exception as e:
        logger.error(f"Error creating DynamoDB record: {str(e)}")
        raise

def update_record_status(sample_id, status, completion_time=None):
    """Update DynamoDB record status"""
    try:
        update_expr = "SET #status = :status, LastChecked = :now"
        expr_attrs = {
            '#status': 'Status',
            ':status': {'S': status},
            ':now': {'S': datetime.utcnow().isoformat()}
        }
        
        if completion_time:
            update_expr += ", CompletionTime = :completion"
            expr_attrs[':completion'] = {'S': completion_time}
        
        dynamodb.update_item(
            TableName=DYNAMODB_TABLE,
            Key={'SampleID': {'S': sample_id}},
            UpdateExpression=update_expr,
            ExpressionAttributeNames={'#status': 'Status'},
            ExpressionAttributeValues=expr_attrs
        )
        
        logger.info(f"Updated status for {sample_id} to {status}")
        
    except Exception as e:
        logger.error(f"Error updating DynamoDB record: {str(e)}")
        raise
