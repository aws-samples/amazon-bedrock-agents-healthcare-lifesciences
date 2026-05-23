#!/usr/bin/env python3
"""
Deploy HealthLake Agent with automatic resource verification and creation.

This script verifies that required AWS resources exist (HealthLake datastore, S3 bucket)
and creates them if they don't exist, then deploys the agent to AgentCore.
"""

import os
import sys
import json
import time
import subprocess
import argparse
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output"""
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    RESET = '\033[0m'


def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.CYAN}{'=' * 50}")
    print(text)
    print(f"{'=' * 50}{Colors.RESET}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.WHITE}{text}{Colors.RESET}")


def run_aws_command(command):
    """Run AWS CLI command and return JSON output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {command}")
        print_error(f"Error: {e.stderr}")
        return None
    except json.JSONDecodeError:
        return result.stdout.strip() if result.stdout else None


def get_account_id():
    """Get AWS Account ID"""
    print_info("Getting AWS Account ID...")
    result = run_aws_command("aws sts get-caller-identity --query Account --output text")
    if result:
        print_success(f"Account ID: {result}")
        return result
    print_error("Failed to get AWS Account ID. Please check your AWS credentials.")
    sys.exit(1)


def check_healthlake_datastore(region):
    """Check for existing ACTIVE HealthLake datastore"""
    print_info("Checking for existing HealthLake datastore...")
    
    datastores = run_aws_command(f"aws healthlake list-fhir-datastores --region {region} --output json")
    
    if datastores and datastores.get('DatastorePropertiesList'):
        for ds in datastores['DatastorePropertiesList']:
            if ds['DatastoreStatus'] == 'ACTIVE':
                print_success("Found existing ACTIVE HealthLake datastore:")
                print_info(f"  Datastore ID: {ds['DatastoreId']}")
                print_info(f"  Datastore Name: {ds['DatastoreName']}")
                print_info(f"  Endpoint: {ds['DatastoreEndpoint']}")
                return ds['DatastoreId'], ds['DatastoreEndpoint']
    
    return None, None


def create_healthlake_datastore(datastore_name, region):
    """Create a new HealthLake datastore with SYNTHEA data"""
    print_warning("No ACTIVE HealthLake datastore found. Creating new datastore...")
    print_warning("Note: This will take 5-10 minutes and will preload with SYNTHEA sample data.")
    
    command = f"""aws healthlake create-fhir-datastore \
        --datastore-name {datastore_name} \
        --datastore-type-version R4 \
        --preload-data-config PreloadDataType=SYNTHEA \
        --region {region} \
        --output json"""
    
    response = run_aws_command(command)
    
    if not response:
        print_error("Failed to create HealthLake datastore")
        return None, None
    
    datastore_id = response['DatastoreId']
    print_success(f"HealthLake datastore creation initiated: {datastore_id}")
    
    # Wait for datastore to become ACTIVE
    print_info("Waiting for datastore to become ACTIVE (this may take 5-10 minutes)...")
    
    max_wait_time = 600  # 10 minutes
    wait_interval = 30
    elapsed_time = 0
    
    while elapsed_time < max_wait_time:
        time.sleep(wait_interval)
        elapsed_time += wait_interval
        
        status_response = run_aws_command(
            f"aws healthlake describe-fhir-datastore --datastore-id {datastore_id} --region {region} --output json"
        )
        
        if status_response:
            status = status_response['DatastoreProperties']['DatastoreStatus']
            print_info(f"  Status: {status} ({elapsed_time}s elapsed)")
            
            if status == 'ACTIVE':
                endpoint = status_response['DatastoreProperties']['DatastoreEndpoint']
                print_success("Datastore is now ACTIVE!")
                print_info(f"  Endpoint: {endpoint}")
                return datastore_id, endpoint
            
            if status == 'CREATE_FAILED':
                error_msg = status_response['DatastoreProperties'].get('ErrorCause', {}).get('ErrorMessage', 'Unknown error')
                print_error(f"Datastore creation failed: {error_msg}")
                return None, None
    
    print_warning(f"Datastore is still creating after {max_wait_time} seconds.")
    print_info(f"Check status later with: aws healthlake describe-fhir-datastore --datastore-id {datastore_id}")
    return datastore_id, None


def check_s3_bucket(bucket_name, region):
    """Check if S3 bucket exists"""
    print_info(f"Checking for S3 bucket: {bucket_name}...")
    
    result = subprocess.run(
        f"aws s3api head-bucket --bucket {bucket_name} 2>&1",
        shell=True,
        capture_output=True
    )
    
    if result.returncode == 0:
        print_success(f"Found existing S3 bucket: {bucket_name}")
        return True
    
    return False


def create_s3_bucket(bucket_name, region):
    """Create S3 bucket with versioning and encryption"""
    print_info(f"Creating S3 bucket: {bucket_name}...")
    
    # Create bucket
    if region == 'us-east-1':
        command = f"aws s3api create-bucket --bucket {bucket_name} --region {region}"
    else:
        command = f"aws s3api create-bucket --bucket {bucket_name} --region {region} --create-bucket-configuration LocationConstraint={region}"
    
    result = subprocess.run(command, shell=True, capture_output=True)
    
    if result.returncode != 0:
        print_error(f"Failed to create S3 bucket: {result.stderr.decode()}")
        return False
    
    print_success(f"Created S3 bucket: {bucket_name}")
    
    # Enable versioning
    subprocess.run(
        f"aws s3api put-bucket-versioning --bucket {bucket_name} --versioning-configuration Status=Enabled",
        shell=True,
        capture_output=True
    )
    print_success("Enabled versioning on S3 bucket")
    
    # Add encryption
    encryption_config = {
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }
    
    subprocess.run(
        f"aws s3api put-bucket-encryption --bucket {bucket_name} --server-side-encryption-configuration '{json.dumps(encryption_config)}'",
        shell=True,
        capture_output=True
    )
    print_success("Enabled encryption on S3 bucket")
    
    # Create sample folder structure
    print_info("Creating sample folder structure...")
    folders = ["patient-records", "lab-results", "imaging-reports", "clinical-notes"]
    for folder in folders:
        subprocess.run(
            f"aws s3api put-object --bucket {bucket_name} --key {folder}/",
            shell=True,
            capture_output=True
        )
    print_success("Created sample folder structure")
    
    return True


def update_env_file(datastore_id, bucket_name, region, agent_name):
    """Update .env file with configuration"""
    print_info("Updating .env configuration...")
    
    env_content = f"""# AWS Configuration
AWS_REGION={region}
AWS_PROFILE=

# HealthLake Configuration
HEALTHLAKE_DATASTORE_ID={datastore_id}

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_TEMPERATURE=0.7
BEDROCK_MAX_TOKENS=4096

# S3 Configuration
S3_BUCKET_NAME={bucket_name}

# AgentCore Configuration
AGENTCORE_RUNTIME_NAME={agent_name}
AGENTCORE_TIMEOUT_SECONDS=300
AGENTCORE_MEMORY_MB=2048

# Debug
DEBUG=false
LOG_LEVEL=INFO
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print_success("Updated .env file with configuration")


def update_agentcore_config(datastore_id, bucket_name, region, agent_name):
    """Update AgentCore configuration with environment variables"""
    print_info("Updating AgentCore configuration...")
    
    config_path = '.bedrock_agentcore.yaml'
    if not os.path.exists(config_path):
        print_warning(f"{config_path} not found. Run 'agentcore configure' first.")
        return
    
    try:
        import yaml
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'agents' in config and agent_name in config['agents']:
            if 'environment_variables' not in config['agents'][agent_name]:
                config['agents'][agent_name]['environment_variables'] = {}
            
            config['agents'][agent_name]['environment_variables'].update({
                'HEALTHLAKE_DATASTORE_ID': datastore_id,
                'AWS_REGION': region,
                'S3_BUCKET_NAME': bucket_name,
                'BEDROCK_MODEL_ID': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'BEDROCK_TEMPERATURE': '0.7',
                'BEDROCK_MAX_TOKENS': '4096'
            })
            
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            print_success("Updated AgentCore configuration with environment variables")
        else:
            print_warning(f"Agent '{agent_name}' not found in configuration")
    
    except ImportError:
        print_warning("PyYAML not installed. Skipping AgentCore config update.")
        print_info("Install with: pip install pyyaml")
    except Exception as e:
        print_warning(f"Failed to update AgentCore config: {e}")


def deploy_agent(agent_name):
    """Deploy agent to AgentCore"""
    print_info("Deploying agent to AgentCore...")
    
    result = subprocess.run(
        f"agentcore deploy --agent {agent_name}",
        shell=True
    )
    
    if result.returncode == 0:
        print_header("Deployment Complete!")
        print_info("Test your agent with:")
        print(f"{Colors.CYAN}  agentcore invoke '{{\"prompt\": \"Search for patients\"}}' --agent {agent_name}{Colors.RESET}")
        return True
    else:
        print_error("Deployment failed. Check the error messages above.")
        return False


def main():
    parser = argparse.ArgumentParser(description='Deploy HealthLake Agent with resource verification')
    parser.add_argument('--agent-name', default='healthlake_agent', help='Agent name')
    parser.add_argument('--datastore-name', default='healthlake-agent-datastore', help='HealthLake datastore name')
    parser.add_argument('--s3-bucket-prefix', default='healthlake-clinical-docs', help='S3 bucket prefix')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--skip-datastore', action='store_true', help='Skip datastore creation')
    parser.add_argument('--skip-s3', action='store_true', help='Skip S3 bucket creation')
    parser.add_argument('--skip-deploy', action='store_true', help='Skip agent deployment')
    
    args = parser.parse_args()
    
    print_header("HealthLake Agent Deployment Verification")
    
    # Step 1: Get AWS Account ID
    account_id = get_account_id()
    
    # Step 2: Check/Create HealthLake Datastore
    print_header("Step 1: Verifying HealthLake Datastore")
    datastore_id, datastore_endpoint = check_healthlake_datastore(args.region)
    
    if not datastore_id and not args.skip_datastore:
        datastore_id, datastore_endpoint = create_healthlake_datastore(args.datastore_name, args.region)
        if not datastore_id:
            print_error("Failed to create HealthLake datastore")
            sys.exit(1)
    elif not datastore_id:
        print_error("No HealthLake datastore found and creation was skipped.")
        sys.exit(1)
    
    # Step 3: Check/Create S3 Bucket
    print_header("Step 2: Verifying S3 Bucket for Clinical Documents")
    bucket_name = f"{args.s3_bucket_prefix}-{account_id}"
    bucket_exists = check_s3_bucket(bucket_name, args.region)
    
    if not bucket_exists and not args.skip_s3:
        bucket_exists = create_s3_bucket(bucket_name, args.region)
        if not bucket_exists:
            print_warning("Continuing without S3 bucket...")
            bucket_name = ""
    elif not bucket_exists:
        print_warning("No S3 bucket found and creation was skipped.")
        bucket_name = ""
    
    # Step 4: Update Configuration
    print_header("Step 3: Updating Configuration")
    update_env_file(datastore_id, bucket_name, args.region, args.agent_name)
    update_agentcore_config(datastore_id, bucket_name, args.region, args.agent_name)
    
    # Step 5: Display Summary
    print_header("Configuration Summary")
    print_info(f"AWS Account: {account_id}")
    print_info(f"Region: {args.region}")
    print_info(f"HealthLake Datastore ID: {datastore_id}")
    if datastore_endpoint:
        print_info(f"HealthLake Endpoint: {datastore_endpoint}")
    if bucket_name:
        print_info(f"S3 Bucket: {bucket_name}")
    
    # Step 6: Deploy Agent
    if not args.skip_deploy:
        print_header("Step 4: Deploying Agent")
        response = input("Do you want to deploy the agent now? (y/n): ")
        if response.lower() == 'y':
            deploy_agent(args.agent_name)
        else:
            print_info("\nDeployment skipped. To deploy later, run:")
            print(f"{Colors.CYAN}  agentcore deploy --agent {args.agent_name}{Colors.RESET}\n")
    
    print_success("Done!")


if __name__ == '__main__':
    main()
