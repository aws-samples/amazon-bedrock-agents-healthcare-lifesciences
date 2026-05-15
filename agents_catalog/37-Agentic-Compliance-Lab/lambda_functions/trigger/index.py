import json
import os
import boto3
import urllib.parse
from botocore.config import Config

AGENT_ARN = os.environ['AGENT_ARN']

def lambda_handler(event, context):
    print(event)
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
    
    s3_client = boto3.client('s3')
    region = None
    project_id = None
    
    # Get region and projectId from S3 object tags
    try:
        tags_response = s3_client.get_object_tagging(Bucket=bucket, Key=key)
        for tag in tags_response.get('TagSet', []):
            if tag['Key'] == 'regulatory_region':
                region = tag['Value']
                print(f"✓ Region detected from S3 tag: {region}")
            elif tag['Key'] == 'project_id':
                project_id = tag['Value']
                print(f"✓ Project ID from S3 tag: {project_id}")
    except Exception as e:
        print(f"⚠ Could not read S3 tags: {str(e)}")
    
    print(f"🚀 Triggering pipeline for: s3://{bucket}/{key}")
    print(f"📍 Regulatory Region: {region}")
    
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
        print(f"✓ Agent triggered successfully. Session: {session_id}")
    except Exception as e:
        # Ignore timeout errors since agent is running async
        if 'ReadTimeoutError' not in str(e) and 'timeout' not in str(e).lower():
            print(f"✗ Error: {str(e)}")
            raise
        else:
            print(f"✓ Agent invoked (timeout expected for async execution)")
    
    return {
        'statusCode': 202,
        'body': json.dumps({
            'status': 'triggered',
            'session_id': session_id,
            'region': region
        })
    }
