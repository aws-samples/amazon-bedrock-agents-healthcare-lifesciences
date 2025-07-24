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

def analyze_web_summary_with_bedrock(pdf_content, model_id):
    """
    Analyze web summary pdf content using Bedrock model
    """
    try:
        # Convert pdf content to base64 for document input
        pdf_bytes = pdf_content if isinstance(pdf_content, bytes) else pdf_content.encode('utf-8')
        #pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Create message for Bedrock
        message = {
            "role": "user",
            "content": [
                {
                    "text": """
                    Analyze this web summary file from a single cell gene expression assay. 
                    Extract and organize the following key quality control metrics:
                    
                    1. Sample information (name, chemistry, etc.)
                    2. Sequencing metrics (number of reads, sequencing saturation, etc.)
                    3. Cell metrics (estimated number of cells, median genes per cell, etc.)
                    4. Mapping metrics (reads mapped to genome, reads mapped confidently, etc.)
                    5. Key visualizations described in the summary (t-SNE plots, violin plots, etc.)
                    
                    Present the information in a structured format that clearly shows all important QC metrics.
                    Include any warnings or notable observations about the quality metrics.
                    """
                },
                {
                    "document": {
                        "name": "WebSummary",
                        "format": "pdf",
                        "source": {
                            "bytes": pdf_bytes
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
        
        # Extract and return the analysis
        return response['output']['message']['content'][0]['text']
        
    except Exception as e:
        logger.error(f"Error analyzing web summary with Bedrock: {str(e)}")
        raise

@app.tool(name="analyze_web_summary", description="Analyzes a web summary file from a single cell gene expression assay")
@tracer.capture_method
def analyze_web_summary(web_summary_s3_uri: str) -> str:
    """
    Analyze a web summary file from a single cell gene expression assay
    
    Parameters:
        web_summary_s3_uri: S3 URI of the web summary pdf file to analyze
        
    Returns:
        Analysis of the web summary file with key QC metrics
    """
    try:
        # Get web summary file from S3
        logger.info(f"Retrieving web summary from: {web_summary_s3_uri}")
        pdf_content = get_s3_object(web_summary_s3_uri)
        
        # Analyze web summary using Bedrock
        logger.info(f"Analyzing web summary with Bedrock model: {BEDROCK_MODEL_ID}")
        analysis_result = analyze_web_summary_with_bedrock(pdf_content, BEDROCK_MODEL_ID)
        
        # Return the analysis result
        return analysis_result
        
    except Exception as e:
        error_message = f"Error analyzing web summary: {str(e)}"
        logger.exception(error_message)
        return error_message

# Lambda handler using Powertools
@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext):
    return app.resolve(event, context)
