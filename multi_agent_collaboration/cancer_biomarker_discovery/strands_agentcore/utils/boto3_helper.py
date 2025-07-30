import boto3
import sys
from typing import Optional

def find_s3_bucket_name_by_suffix(name_suffix: str) -> Optional[str]:
    """Find S3 bucket name by name suffix"""
    client = boto3.client('s3')
    
    response = client.list_buckets()
    for bucket in response['Buckets']:
        if bucket['Name'].endswith(name_suffix):
            return bucket['Name']
    return None

def find_state_machine_arn_by_prefix(name_prefix: str) -> Optional[str]:
    """Find state machine ARN by name prefix"""
    client = boto3.client('stepfunctions')
    
    paginator = client.get_paginator('list_state_machines')
    for page in paginator.paginate():
        for sm in page['stateMachines']:
            if sm['name'].startswith(name_prefix):
                return sm['stateMachineArn']
    return None
