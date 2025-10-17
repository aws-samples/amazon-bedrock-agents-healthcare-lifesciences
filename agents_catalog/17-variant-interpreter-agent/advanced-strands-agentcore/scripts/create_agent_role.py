#!/usr/bin/env python3
"""
Script to create an IAM role for the agent core with specified permissions.
Creates role: agentcore-agentcore_strands-role-{datestamp}
"""

import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError

def create_agent_role():
    """Create IAM role with specified permissions for agent core."""
    
    # Initialize IAM client
    iam = boto3.client('iam')
    
    # Generate datestamp for role name
    datestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    role_name = f'agentcore-agentcore_strands-role-{datestamp}'
    
    print(f"Creating IAM role: {role_name}")
    
    # Trust policy for the role (allows Lambda and Bedrock to assume this role)
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": [
                        "lambda.amazonaws.com",
                        "bedrock.amazonaws.com",
                        "omics.amazonaws.com"
                    ]
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        # Create the IAM role
        response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f'Agent core role created on {datestamp} with exploratory permissions',
            MaxSessionDuration=3600
        )
        
        role_arn = response['Role']['Arn']
        print(f"✅ Successfully created role: {role_name}")
        print(f"   Role ARN: {role_arn}")
        
        # Attach managed policies
        managed_policies = [
            'arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess',
            'arn:aws:iam::aws:policy/AmazonOmicsFullAccess'
        ]
        
        for policy_arn in managed_policies:
            try:
                iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
                print(f"✅ Attached managed policy: {policy_arn}")
            except ClientError as e:
                print(f"❌ Failed to attach managed policy {policy_arn}: {e}")
        
        # Create custom inline policy for additional permissions
        custom_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:*"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream",
                        "bedrock:ListKnowledgeBases"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                }
            ]
        }
        
        # Attach the custom inline policy
        try:
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName=f'{role_name}-custom-policy',
                PolicyDocument=json.dumps(custom_policy)
            )
            print(f"✅ Attached custom inline policy with additional permissions")
        except ClientError as e:
            print(f"❌ Failed to attach custom policy: {e}")
        
        print(f"\n🎉 Role creation completed!")
        print(f"Role Name: {role_name}")
        print(f"Role ARN: {role_arn}")
        
        return {
            'role_name': role_name,
            'role_arn': role_arn,
            'datestamp': datestamp
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'EntityAlreadyExists':
            print(f"❌ Role {role_name} already exists")
        else:
            print(f"❌ Failed to create role: {e}")
        return None

def list_role_policies(role_name):
    """List all policies attached to the role for verification."""
    iam = boto3.client('iam')
    
    print(f"\n📋 Policies attached to role '{role_name}':")
    
    try:
        # List attached managed policies
        managed_policies = iam.list_attached_role_policies(RoleName=role_name)
        print("  Managed Policies:")
        for policy in managed_policies['AttachedPolicies']:
            print(f"    - {policy['PolicyName']} ({policy['PolicyArn']})")
        
        # List inline policies
        inline_policies = iam.list_role_policies(RoleName=role_name)
        print("  Inline Policies:")
        for policy_name in inline_policies['PolicyNames']:
            print(f"    - {policy_name}")
            
    except ClientError as e:
        print(f"❌ Failed to list policies: {e}")

if __name__ == "__main__":
    print("🚀 Starting IAM role creation for agent core...")
    print("=" * 60)
    
    # Create the role
    result = create_agent_role()
    
    if result:
        # Verify by listing attached policies
        list_role_policies(result['role_name'])
        
        print("\n" + "=" * 60)
        print("✨ Script completed successfully!")
        print(f"You can now use this role ARN in your agent configuration:")
        print(f"   {result['role_arn']}")
    else:
        print("\n❌ Script failed to create the role")
