import boto3
import json
import yaml
import os
from typing import Dict, Any
import requests

def get_access_token():
    """Get  access token using manual M2M flow."""
    try:
        # Get credentials from SSM
        machine_client_id = get_ssm_parameter("/app/researchapp/agentcore/machine_client_id")
        machine_client_secret = get_ssm_parameter("/app/researchapp/agentcore/cognito_secret")
        cognito_domain = get_ssm_parameter("/app/researchapp/agentcore/cognito_domain")
        user_pool_id = get_ssm_parameter("/app/researchapp/agentcore/userpool_id")
        #print(user_pool_id)

        # Remove https:// if it's already in the domain
        # Clean the domain properly
        cognito_domain = cognito_domain.strip()
        if cognito_domain.startswith("https://"):
            cognito_domain = cognito_domain[8:]  # Remove "https://"
        #print(f"Cleaned domain: {repr(cognito_domain)}")
        token_url = f"https://{cognito_domain}/oauth2/token"
        #print(f"Token URL: {token_url}")  # Debug print
        #print(f"Token URL: {repr(token_url)}")
        
        # Test URL 
        from urllib.parse import urlparse
        parsed = urlparse(token_url)
        #print(f"Parsed - scheme: {parsed.scheme}, netloc: {parsed.netloc}")
        
        # Get resource server ID from machine client configuration
        try:
            cognito_client = boto3.client('cognito-idp')
            
            
            # List resource servers to find the ID
            response = cognito_client.list_resource_servers(UserPoolId=user_pool_id,MaxResults=1)
            print(response)
            if response['ResourceServers']:
                resource_server_id = response['ResourceServers'][0]['Identifier']
                #print(resource_server_id)
                scopes = f"{resource_server_id}/read"
            else:
                scopes = "gateway:read gateway:write"
        except Exception as e:
            raise Exception(f"Error getting scopes: {str(e)}")

        #print("Scope")
        #print(scopes)
        # Perform M2M OAuth flow
        token_url = f"https://{cognito_domain}/oauth2/token"
        token_data = {
            "grant_type": "client_credentials",
            "client_id": machine_client_id,
            "client_secret": machine_client_secret,
            "scope": scopes
        }
        
        response = requests.post(
            token_url, 
            data=token_data, 
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get access token: {response.text}")
        
        access_token=response.json()["access_token"]
           
        return access_token     
        
    except Exception as e:
        raise Exception(f"Error getting  access token: {str(e)}")





def get_ssm_parameter(name: str, with_decryption: bool = True) -> str:
    ssm = boto3.client("ssm")

    response = ssm.get_parameter(Name=name, WithDecryption=with_decryption)

    return response["Parameter"]["Value"]


def put_ssm_parameter(
    name: str, value: str, parameter_type: str = "String", with_encryption: bool = False
) -> None:
    ssm = boto3.client("ssm")

    put_params = {
        "Name": name,
        "Value": value,
        "Type": parameter_type,
        "Overwrite": True,
    }

    if with_encryption:
        put_params["Type"] = "SecureString"

    ssm.put_parameter(**put_params)


def delete_ssm_parameter(name: str) -> None:
    ssm = boto3.client("ssm")
    try:
        ssm.delete_parameter(Name=name)
    except ssm.exceptions.ParameterNotFound:
        pass


def load_api_spec(file_path: str) -> list:
    with open(file_path, "r") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a list in the JSON file")
    return data


def get_aws_region() -> str:
    session = boto3.session.Session()
    return session.region_name


def get_aws_account_id() -> str:
    sts = boto3.client("sts")
    return sts.get_caller_identity()["Account"]


def get_cognito_client_secret() -> str:
    client = boto3.client("cognito-idp")
    response = client.describe_user_pool_client(
        UserPoolId=get_ssm_parameter("/app/researchapp/agentcore/userpool_id"),
        ClientId=get_ssm_parameter("/app/researchapp/agentcore/machine_client_id"),
    )
    return response["UserPoolClient"]["ClientSecret"]


def read_config(file_path: str) -> Dict[str, Any]:
    """
    Read configuration from a file path. Supports JSON, YAML, and YML formats.

    Args:
        file_path (str): Path to the configuration file

    Returns:
        Dict[str, Any]: Configuration data as a dictionary

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is not supported or invalid
        yaml.YAMLError: If YAML parsing fails
        json.JSONDecodeError: If JSON parsing fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    # Get file extension to determine format
    _, ext = os.path.splitext(file_path.lower())

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            if ext == ".json":
                return json.load(file)
            elif ext in [".yaml", ".yml"]:
                return yaml.safe_load(file)
            else:
                # Try to auto-detect format by attempting JSON first, then YAML
                content = file.read()
                file.seek(0)

                # Try JSON first
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Try YAML
                    try:
                        return yaml.safe_load(content)
                    except yaml.YAMLError:
                        raise ValueError(
                            f"Unsupported configuration file format: {ext}. "
                            f"Supported formats: .json, .yaml, .yml"
                        )

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file {file_path}: {e}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in configuration file {file_path}: {e}")
    except Exception as e:
        raise ValueError(f"Error reading configuration file {file_path}: {e}")