import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import List

class SageMakerRolePolicyChecker:
    def __init__(self):
        """Initialize the checker with AWS clients."""
        try:
            self.iam_client = boto3.client('iam')
            self.sagemaker_client = boto3.client('sagemaker')
        except NoCredentialsError:
            raise Exception("AWS credentials not found. Please configure your credentials.")
    
    def get_required_policies(self) -> List[str]:
        """Return the list of required managed policies."""
        return [
            'AmazonBedrockFullAccess',
            'AmazonRedshiftFullAccess', 
            'AmazonS3FullAccess',
            'AmazonSageMakerFullAccess',
            'AWSLambda_FullAccess',
            'AWSStepFunctionsFullAccess',
            'IAMFullAccess'
        ]
    
    def get_notebook_instance_role(self, notebook_instance_name: str) -> str:
        """Get the IAM role ARN for a SageMaker notebook instance."""
        try:
            response = self.sagemaker_client.describe_notebook_instance(
                NotebookInstanceName=notebook_instance_name
            )
            return response['RoleArn']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException':
                raise Exception(f"Notebook instance '{notebook_instance_name}' not found")
            else:
                raise Exception(f"Error retrieving notebook instance: {e}")
    
    def extract_role_name_from_arn(self, role_arn: str) -> str:
        """Extract role name from ARN."""
        return role_arn.split('/')[-1]
    
    def get_attached_managed_policies(self, role_name: str) -> List[str]:
        """Get all managed policies attached to a role."""
        try:
            paginator = self.iam_client.get_paginator('list_attached_role_policies')
            attached_policies = []
            
            for page in paginator.paginate(RoleName=role_name):
                for policy in page['AttachedPolicies']:
                    attached_policies.append(policy['PolicyName'])
            
            return attached_policies
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                raise Exception(f"Role '{role_name}' not found")
            else:
                raise Exception(f"Error retrieving attached policies: {e}")
    
    def check_single_role_policies(self, role_name: str):
        """Check if a single role has all required managed policies. Throws exception if missing."""
        required_policies = self.get_required_policies()
        attached_policies = self.get_attached_managed_policies(role_name)
        
        missing_policies = [policy for policy in required_policies if policy not in attached_policies]
        
        if missing_policies:
            raise Exception(f"Role '{role_name}' is missing required policies: {', '.join(missing_policies)}")
    
    def check_policies(self, role_arn=None, notebook_instance_name: str = None):
        """
        Check if role(s) have all required managed policies. Throws exception if any are missing.
        
        Args:
            role_arn: Direct IAM role ARN (str) or list of role ARNs (List[str]) (optional)
            notebook_instance_name: SageMaker notebook instance name (optional)
            
        Raises:
            Exception: If any required policies are missing from any role
        """
        if not role_arn and not notebook_instance_name:
            raise ValueError("Either role_arn or notebook_instance_name must be provided")
        
        # Handle notebook instance name
        if notebook_instance_name:
            role_arn_from_notebook = self.get_notebook_instance_role(notebook_instance_name)
            role_name = self.extract_role_name_from_arn(role_arn_from_notebook)
            self.check_single_role_policies(role_name)
            return
        
        # Handle single role ARN
        if isinstance(role_arn, str):
            role_name = self.extract_role_name_from_arn(role_arn)
            self.check_single_role_policies(role_name)
            return
        
        # Handle list of role ARNs
        if isinstance(role_arn, list):
            missing_roles = []
            for arn in role_arn:
                try:
                    role_name = self.extract_role_name_from_arn(arn)
                    self.check_single_role_policies(role_name)
                except Exception as e:
                    missing_roles.append(f"{arn}: {str(e)}")
            
            if missing_roles:
                raise Exception(f"Policy check failed for roles:\n" + "\n".join(missing_roles))
            return
        
        raise ValueError("role_arn must be a string or list of strings")
