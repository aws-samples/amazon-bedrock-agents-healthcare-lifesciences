import json
import os
import boto3
import urllib.request

def handler(event, context):
    status = 'SUCCESS'
    reason = ''
    try:
        request_type = event['RequestType']
        props = event['ResourceProperties']
        runtime_arn = props['RuntimeArn']

        # Amazon Bedrock AgentCore control-plane client for runtime resource policy management
        client = boto3.client('bedrock-agentcore-control', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

        if request_type in ('Create', 'Update'):
            policy = props['Policy']
            print(f"Putting resource policy on {runtime_arn}")
            client.put_resource_policy(resourceArn=runtime_arn, policy=policy)
        elif request_type == 'Delete':
            try:
                client.delete_resource_policy(resourceArn=runtime_arn)
            except Exception as delete_error:
                # Best-effort cleanup: the policy or runtime may already be
                # gone during stack teardown. Log and continue so the Delete
                # does not block stack deletion.
                print(f"Ignoring delete_resource_policy error: {delete_error}")
    
    except Exception as e:
        print(f"Error: {e}")
        status = 'FAILED'
        reason = str(e)

    # Send response to AWS CloudFormation
    body = json.dumps({
        'Status': status,
        'Reason': reason or 'OK',
        'PhysicalResourceId': event.get('PhysicalResourceId', 'AgentRuntimeResourcePolicy'),
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
    }).encode()

    response_url = event['ResponseURL']
    if not response_url.startswith('https://'):
        raise ValueError(f"ResponseURL must use HTTPS scheme, got: {response_url[:20]}")
    req = urllib.request.Request(response_url, data=body, method='PUT')
    req.add_header('Content-Type', '')
    req.add_header('Content-Length', str(len(body)))
    urllib.request.urlopen(req)
