import boto3


def get_ssm_parameter(parameter_name: str, region: str = "us-east-1") -> str:
    """Get parameter from AWS Systems Manager Parameter Store."""
    ssm = boto3.client("ssm", region_name=region)
    try:
        response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except Exception as e:
        raise Exception(f"Failed to get SSM parameter {parameter_name}: {str(e)}")
