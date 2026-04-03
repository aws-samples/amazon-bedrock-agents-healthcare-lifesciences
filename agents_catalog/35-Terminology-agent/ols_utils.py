"""Utility functions for OLS MCP server deployment using Terminology Agent stack credentials."""

import boto3
import requests
from typing import Optional


def get_ssm_parameter(name: str, with_decryption: bool = True) -> str:
    """Get parameter from AWS Systems Manager Parameter Store."""
    ssm = boto3.client("ssm")
    response = ssm.get_parameter(Name=name, WithDecryption=with_decryption)
    return response["Parameter"]["Value"]


def get_secret(name: str) -> str:
    """Get secret from AWS Secrets Manager."""
    secrets_client = boto3.client("secretsmanager")
    response = secrets_client.get_secret_value(SecretId=name)
    return response["SecretString"]


def put_ssm_parameter(
    name: str, value: str, parameter_type: str = "String", description: str = ""
) -> None:
    """Store parameter in AWS Systems Manager Parameter Store."""
    ssm = boto3.client("ssm")
    ssm.put_parameter(
        Name=name,
        Value=value,
        Type=parameter_type,
        Description=description,
        Overwrite=True,
    )


def get_terminology_agent_cognito_config(stack_name: str = "terminology-agent") -> dict:
    """
    Get Cognito configuration from Terminology Agent stack.

    Returns:
        dict with keys: pool_id, client_id, client_secret, discovery_url, cognito_domain
    """
    print(f"🔍 Retrieving Cognito configuration from stack: {stack_name}")

    # Get parameters from SSM (created by CDK stack)
    pool_id = get_ssm_parameter(f"/{stack_name}/cognito-user-pool-id")
    client_id = get_ssm_parameter(f"/{stack_name}/machine_client_id")
    cognito_domain = get_ssm_parameter(f"/{stack_name}/cognito_provider")

    # Get client secret from Secrets Manager
    client_secret = get_secret(f"/{stack_name}/machine_client_secret")

    # Construct discovery URL
    region = boto3.Session().region_name
    discovery_url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"

    config = {
        "pool_id": pool_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "discovery_url": discovery_url,
        "cognito_domain": cognito_domain,
    }

    print(f"✓ User Pool ID: {pool_id}")
    print(f"✓ Client ID: {client_id}")
    print(f"✓ Discovery URL: {discovery_url}")

    return config


def get_access_token(stack_name: str = "terminology-agent") -> str:
    """
    Get access token using M2M OAuth2 client credentials flow.

    Args:
        stack_name: The CDK stack name (default: terminology-agent)

    Returns:
        Access token string
    """
    try:
        config = get_terminology_agent_cognito_config(stack_name)

        # Clean the domain
        cognito_domain = config["cognito_domain"].strip()
        if cognito_domain.startswith("https://"):
            cognito_domain = cognito_domain[8:]

        # Get resource server scopes
        cognito_client = boto3.client("cognito-idp")
        response = cognito_client.list_resource_servers(
            UserPoolId=config["pool_id"], MaxResults=1
        )

        if response["ResourceServers"]:
            resource_server_id = response["ResourceServers"][0]["Identifier"]
            scopes = f"{resource_server_id}/read {resource_server_id}/write"
        else:
            raise Exception("No resource servers found in user pool")

        # Perform OAuth2 client credentials flow
        token_url = f"https://{cognito_domain}/oauth2/token"
        token_data = {
            "grant_type": "client_credentials",
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "scope": scopes,
        }

        response = requests.post(
            token_url,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,  # 30 seconds timeout for OAuth token request
        )

        if response.status_code != 200:
            raise Exception(f"Failed to get access token: {response.text}")

        access_token = response.json()["access_token"]
        print("✓ Access token retrieved successfully")

        return access_token

    except Exception as e:
        raise Exception(f"Error getting access token: {str(e)}")


def get_aws_region() -> str:
    """Get current AWS region."""
    session = boto3.session.Session()
    return session.region_name


def get_aws_account_id() -> str:
    """Get current AWS account ID."""
    sts = boto3.client("sts")
    return sts.get_caller_identity()["Account"]
