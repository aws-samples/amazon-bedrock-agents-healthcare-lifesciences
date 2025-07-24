import os
import json
import boto3
import logging
import base64
from urllib.parse import urlparse
from botocore.client import Config

# Import Powertools for AWS Lambda
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import BedrockAgentFunctionResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

# Configure logging and tracing
logger = Logger()
tracer = Tracer()
app = BedrockAgentFunctionResolver()

# Environment variables
REGION = os.environ.get('AWS_REGION', 'us-east-1')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')

# Bedrock configuration
BEDROCK_CONFIG = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})

# Initialize clients
s3_client = boto3.client('s3')
bedrock_client = boto3.client(service_name='bedrock-runtime', region_name=REGION, config=BEDROCK_CONFIG)

def parse_s3_uri(s3_uri):
    """Parse S3 URI into bucket and key"""
    parsed_url = urlparse(s3_uri)
    if parsed_url.scheme != 's3':
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    
    bucket = parsed_url.netloc
    key = parsed_url.path.lstrip('/')
    return bucket, key

def get_s3_object(s3_uri):
    """Get object from S3 using the provided URI"""
    try:
        bucket, key = parse_s3_uri(s3_uri)
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read()
        return content
    except Exception as e:
        logger.error(f"Error retrieving S3 object: {str(e)}")
        raise

def validate_qc_metrics_with_bedrock(web_summary_content, technical_doc_content, model_id):
    """
    Validate QC metrics against technical guidelines using Bedrock model
    """
    try:
        # Convert content to base64 for document input
        web_summary_bytes = web_summary_content if isinstance(web_summary_content, bytes) else web_summary_content.encode('utf-8')
        #web_summary_base64 = base64.b64encode(web_summary_bytes).decode('utf-8')
        
        technical_doc_bytes = technical_doc_content if isinstance(technical_doc_content, bytes) else technical_doc_content.encode('utf-8')
        #technical_doc_base64 = base64.b64encode(technical_doc_bytes).decode('utf-8')
        
        # Create message for Bedrock
        message = {
            "role": "user",
            "content": [
                {
                    "text": """
                    I'm providing you with two documents:
                    1. A web summary file from a single cell gene expression assay
                    2. A technical document with guidelines for interpreting these web summaries
                    
                    Please validate the quality control metrics in the web summary against the technical guidelines.
                    
                    For your analysis:
                    1. Extract key QC metrics from the web summary
                    2. Compare these metrics against the acceptable ranges in the technical document
                    3. Identify any anomalies or quality issues
                    4. Provide a comprehensive validation report with:
                       - Pass/fail status for each key metric
                       - Explanations for any failures or warnings
                       - Overall assessment of the sample quality
                       - Recommendations based on the findings
                    
                    Use clear indicators (✅, ⚠️, ❌) to show pass/warning/fail status for each metric.
                    """
                },
                {
                    "document": {
                        "name": "WebSummary",
                        "format": "pdf",
                        "source": {
                            "bytes": web_summary_bytes
                        }
                    }
                },
                {
                    "document": {
                        "name": "TechnicalGuidelines",
                        "format": "pdf",
                        "source": {
                            "bytes": technical_doc_bytes
                        }
                    }
                }
            ]
        }
        
        # Invoke Bedrock model
        response = bedrock_client.converse(
            modelId=model_id,
            messages=[message]
        )
        
        # Extract and return the validation results
        return response['output']['message']['content'][0]['text']
        
    except Exception as e:
        logger.error(f"Error validating QC metrics with Bedrock: {str(e)}")
        raise

@app.tool(name="validate_qc_metrics", description="Validates quality control metrics against technical guidelines")
@tracer.capture_method
def validate_qc_metrics(web_summary_s3_uri: str, technical_doc_s3_uri: str) -> str:
    """
    Validate quality control metrics from a web summary file against technical guidelines
    
    Parameters:
        web_summary_s3_uri: S3 URI of the web summary pdf file to analyze
        technical_doc_s3_uri: S3 URI of the technical document PDF containing interpretation guidelines
        
    Returns:
        Validation results comparing the web summary metrics against technical guidelines
    """
    try:
        # Get web summary file from S3
        logger.info(f"Retrieving web summary from: {web_summary_s3_uri}")
        web_summary_content = get_s3_object(web_summary_s3_uri)
        
        # Get technical document from S3
        logger.info(f"Retrieving technical document from: {technical_doc_s3_uri}")
        technical_doc_content = get_s3_object(technical_doc_s3_uri)
        
        # Validate QC metrics using Bedrock
        logger.info(f"Validating QC metrics with Bedrock model: {BEDROCK_MODEL_ID}")
        validation_result = validate_qc_metrics_with_bedrock(
            web_summary_content, 
            technical_doc_content, 
            BEDROCK_MODEL_ID
        )
        
        # Return the validation result
        return validation_result
        
    except Exception as e:
        error_message = f"Error validating QC metrics: {str(e)}"
        logger.exception(error_message)
        return error_message

# Lambda handler using Powertools
@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext):
    return app.resolve(event, context)
