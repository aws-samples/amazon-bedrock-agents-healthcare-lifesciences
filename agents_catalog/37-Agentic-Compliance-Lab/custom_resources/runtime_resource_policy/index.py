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

        client = boto3.client('bedrock-agentcore-control', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

        if request_type in ('Create', 'Update'):
            policy = props['Policy']
            print(f"Putting resource policy on {runtime_arn}")
            client.put_resource_policy(resourceArn=runtime_arn, policy=policy)
        elif request_type == 'Delete':
            try:
                client.delete_resource_policy(resourceArn=runtime_arn)
            except Exception:
                pass
    except Exception as e:
        print(f"Error: {e}")
        status = 'FAILED'
        reason = str(e)

    # Send response to CloudFormation
    body = json.dumps({
        'Status': status,
        'Reason': reason or 'OK',
        'PhysicalResourceId': event.get('PhysicalResourceId', 'AgentRuntimeResourcePolicy'),
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
    }).encode()

    req = urllib.request.Request(event['ResponseURL'], data=body, method='PUT')
    req.add_header('Content-Type', '')
    req.add_header('Content-Length', str(len(body)))
    urllib.request.urlopen(req)
