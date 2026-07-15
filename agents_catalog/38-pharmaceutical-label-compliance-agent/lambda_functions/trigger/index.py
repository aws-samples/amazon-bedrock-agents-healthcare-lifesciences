import json
import logging
import os
import boto3
import urllib.parse
from botocore.config import Config

AGENT_ARN = os.environ['AGENT_ARN']

LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    logger.info("Triggered for s3://%s/%s", bucket, key)

    # Amazon S3 client for reading object tags
    amazon_s3_client = boto3.client('s3')
    region = None
    project_id = None

    # Get region and projectId from Amazon S3 object tags
    try:
        tags_response = amazon_s3_client.get_object_tagging(Bucket=bucket, Key=key)
        for tag in tags_response.get('TagSet', []):
            if tag['Key'] == 'regulatory_region':
                region = tag['Value']
                logger.info("Region from S3 tag: %s", region)
            elif tag['Key'] == 'project_id':
                project_id = tag['Value']
                logger.info("Project ID from S3 tag: %s", project_id)
    except Exception as e:
        logger.warning("Could not read S3 tags: %s", e)

    session_id = f"s3-trigger-{context.aws_request_id}"

    payload = json.dumps({
        "image_bucket": bucket,
        "image_key": key,
        "max_retries": 3,
        "region": region,
        "project_id": project_id or ""
    }).encode()

    # Start agent and exit immediately
    config = Config(
        read_timeout=3,
        connect_timeout=3,
        retries={'max_attempts': 0}
    )

    client = boto3.client('bedrock-agentcore', region_name=os.environ.get('AWS_REGION', 'us-east-1'), config=config)

    try:
        # Start invocation
        client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            runtimeSessionId=session_id,
            payload=payload
        )
        logger.info("Agent triggered. Session: %s", session_id)
    except Exception as e:
        if 'ReadTimeoutError' not in str(e) and 'timeout' not in str(e).lower():
            raise
        else:
            logger.info("Agent invoked (async timeout expected)")

    return {
        'statusCode': 202,
        'body': json.dumps({
            'status': 'triggered',
            'session_id': session_id,
            'region': region
        })
    }
