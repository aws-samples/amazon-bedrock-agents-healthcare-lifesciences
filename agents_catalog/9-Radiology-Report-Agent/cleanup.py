# delete the agennt
import os
import shutil
import boto3
import argparse
import logging
from botocore.exceptions import ClientError
from botocore.config import Config

# delete s3 bucket
def delete_s3_bucket(bucket_name):
    s3_client = boto3.client('s3')
    try:
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' deleted successfully.")
    except ClientError as e:
        logging.error(f"Error deleting bucket {bucket_name}: {e}")
        
# delete the agent
def delete_agent(agent_name):
    client = boto3.client("bedrock-agent")
    try:
        response = client.delete_agent(agentId=agent_name)
        print(f"Agent '{agent_name}' deleted successfully.")
    except ClientError as e:
        logging.error(f"Error deleting agent {agent_name}: {e}")