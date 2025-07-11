"""
Research Agent CDK Stack

This stack creates:
1. A Lambda layer containing Python dependencies
2. A Lambda function that runs the research agent
3. IAM permissions for the Lambda to invoke Bedrock APIs
"""

from pathlib import Path

from aws_cdk import Duration, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from constructs import Construct


class ResearchAgentStack(Stack):
    """CDK Stack for the Research Agent Lambda function and dependencies."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define paths for packaging
        current_dir = Path(__file__).parent.parent
        packaging_dir = current_dir / "packaging"

        zip_dependencies = packaging_dir / "dependencies.zip"
        zip_app = packaging_dir / "app.zip"

        # Create a lambda layer with dependencies to keep the code readable in the Lambda console
        dependencies_layer = _lambda.LayerVersion(
            self,
            "DependenciesLayer",
            code=_lambda.Code.from_asset(str(zip_dependencies)),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="Dependencies needed for agent-based lambda",
        )

        # Define the Lambda function
        research_agent_function = _lambda.Function(
            self,
            "ResearchAgentLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            function_name="ResearchAgentLambda",
            description="A function that invokes a research agent",
            handler="agent_handler.handler",
            code=_lambda.Code.from_asset(str(zip_app)),
            timeout=Duration.seconds(900),
            memory_size=512,
            layers=[dependencies_layer],
            architecture=_lambda.Architecture.ARM_64,
        )

        # Add permissions for the Lambda function to invoke Bedrock APIs
        research_agent_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )
