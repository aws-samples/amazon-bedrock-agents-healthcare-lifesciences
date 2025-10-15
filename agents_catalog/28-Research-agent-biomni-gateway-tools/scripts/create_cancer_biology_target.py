#!/usr/bin/python
"""
Cancer Biology Gateway Target Management Script

This script creates and manages a gateway target for cancer biology analysis tools.
It follows the established database gateway pattern and integrates with the existing
AgentCore Gateway infrastructure.
"""
import os
import sys
import boto3
import click

from utils import (
    get_aws_region,
    get_ssm_parameter,
    put_ssm_parameter,
    delete_ssm_parameter,
    load_api_spec,
)


REGION = get_aws_region()

gateway_client = boto3.client(
    "bedrock-agentcore-control",
    region_name=REGION,
)


def create_cancer_biology_target(gateway_id: str, api_spec: list) -> dict:
    """Create a cancer biology gateway target with the specified configuration."""
    try:
        # Get Cancer Biology Lambda ARN from SSM
        lambda_arn = get_ssm_parameter(
            "/app/researchapp/agentcore/cancer_biology_lambda_arn"
        )

        # Configure Lambda target with MCP protocol and tool schema
        lambda_target_config = {
            "mcp": {
                "lambda": {
                    "lambdaArn": lambda_arn,
                    "toolSchema": {"inlinePayload": api_spec},
                }
            }
        }

        # Configure credential provider to use Gateway IAM role
        credential_config = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]

        click.echo(f"Creating cancer biology target for gateway: {gateway_id}")
        click.echo(f"Lambda ARN: {lambda_arn}")
        click.echo(f"Number of tools: {len(api_spec)}")

        # Create the gateway target
        create_target_response = gateway_client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name="CancerBiologyTarget",
            description="Cancer Biology Analysis Tools - DDR network, cell senescence/apoptosis, somatic mutations, structural variations, NMF analysis, and CNV analysis",
            targetConfiguration=lambda_target_config,
            credentialProviderConfigurations=credential_config,
        )

        target_id = create_target_response["targetId"]
        click.echo(f"✅ Cancer biology target created: {target_id}")

        # Store target ID in SSM parameter
        put_ssm_parameter(
            "/app/researchapp/agentcore/cancer_biology_target_id", target_id
        )
        click.echo("✅ Target ID saved to SSM parameter")

        return {
            "target_id": target_id,
            "gateway_id": gateway_id,
            "lambda_arn": lambda_arn,
        }

    except Exception as e:
        click.echo(f"❌ Error creating cancer biology target: {str(e)}", err=True)
        sys.exit(1)


def delete_cancer_biology_target(gateway_id: str, target_id: str) -> bool:
    """Delete the cancer biology gateway target."""
    try:
        click.echo(f"🗑️  Deleting cancer biology target: {target_id}")
        click.echo(f"   Gateway: {gateway_id}")

        gateway_client.delete_gateway_target(
            gatewayIdentifier=gateway_id, targetId=target_id
        )

        click.echo(f"✅ Cancer biology target {target_id} deleted successfully")

        # Clean up SSM parameter
        delete_ssm_parameter("/app/researchapp/agentcore/cancer_biology_target_id")
        click.echo("🧹 Removed cancer biology target SSM parameter")

        return True

    except Exception as e:
        click.echo(f"❌ Error deleting cancer biology target: {str(e)}", err=True)
        return False


def get_gateway_id_from_ssm() -> str:
    """Get gateway ID from SSM parameter."""
    try:
        return get_ssm_parameter("/app/researchapp/agentcore/gateway_id")
    except Exception as e:
        click.echo(f"❌ Error reading gateway ID from SSM: {str(e)}", err=True)
        return None


def get_target_id_from_ssm() -> str:
    """Get cancer biology target ID from SSM parameter."""
    try:
        return get_ssm_parameter(
            "/app/researchapp/agentcore/cancer_biology_target_id"
        )
    except Exception as e:
        click.echo(
            f"❌ Error reading cancer biology target ID from SSM: {str(e)}", err=True
        )
        return None


@click.group()
@click.pass_context
def cli(ctx):
    """Cancer Biology Gateway Target Management CLI.

    Create and delete cancer biology gateway targets for the research application.
    """
    ctx.ensure_object(dict)


@cli.command()
@click.option(
    "--gateway-id",
    help="Gateway ID to attach the target to (if not provided, will read from SSM)",
)
@click.option(
    "--api-spec-file",
    default="prerequisite/lambda/cancer_biology_api_spec.json",
    help="Path to the cancer biology API specification file (default: prerequisite/lambda/cancer_biology_api_spec.json)",
)
def create(gateway_id, api_spec_file):
    """Create a new cancer biology gateway target."""
    click.echo("🚀 Creating cancer biology gateway target")
    click.echo(f"📍 Region: {REGION}")

    # Get gateway ID from SSM if not provided
    if not gateway_id:
        gateway_id = get_gateway_id_from_ssm()
        if not gateway_id:
            click.echo(
                "❌ No gateway ID provided and couldn't read from SSM parameters",
                err=True,
            )
            sys.exit(1)
        click.echo(f"📖 Using gateway ID from SSM: {gateway_id}")

    # Validate API spec file exists
    if not os.path.exists(api_spec_file):
        click.echo(f"❌ API specification file not found: {api_spec_file}", err=True)
        sys.exit(1)

    try:
        # Load the cancer biology API specification
        api_spec = load_api_spec(api_spec_file)
        click.echo(f"📄 Loaded API spec with {len(api_spec)} tools")

        # List the tools being registered
        click.echo("🔧 Cancer biology tools:")
        for tool in api_spec:
            click.echo(f"   - {tool['name']}")

        # Create the target
        target = create_cancer_biology_target(gateway_id=gateway_id, api_spec=api_spec)
        click.echo(
            f"🎉 Cancer biology target created successfully with ID: {target['target_id']}"
        )

    except Exception as e:
        click.echo(f"❌ Failed to create cancer biology target: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--gateway-id",
    help="Gateway ID (if not provided, will read from SSM)",
)
@click.option(
    "--target-id",
    help="Target ID to delete (if not provided, will read from SSM)",
)
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def delete(gateway_id, target_id, confirm):
    """Delete the cancer biology gateway target."""

    # Get gateway ID from SSM if not provided
    if not gateway_id:
        gateway_id = get_gateway_id_from_ssm()
        if not gateway_id:
            click.echo(
                "❌ No gateway ID provided and couldn't read from SSM parameters",
                err=True,
            )
            sys.exit(1)
        click.echo(f"📖 Using gateway ID from SSM: {gateway_id}")

    # Get target ID from SSM if not provided
    if not target_id:
        target_id = get_target_id_from_ssm()
        if not target_id:
            click.echo(
                "❌ No target ID provided and couldn't read from SSM parameters",
                err=True,
            )
            sys.exit(1)
        click.echo(f"📖 Using target ID from SSM: {target_id}")

    # Confirmation prompt
    if not confirm:
        if not click.confirm(
            f"⚠️  Are you sure you want to delete cancer biology target {target_id}? This action cannot be undone."
        ):
            click.echo("❌ Operation cancelled")
            sys.exit(0)

    click.echo(f"🗑️  Deleting cancer biology target: {target_id}")

    if delete_cancer_biology_target(gateway_id, target_id):
        click.echo("🎉 Cancer biology target deleted successfully")
    else:
        click.echo("❌ Failed to delete cancer biology target", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
