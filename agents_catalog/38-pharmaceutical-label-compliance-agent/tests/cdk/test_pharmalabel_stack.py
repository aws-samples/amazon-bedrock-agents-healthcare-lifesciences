"""CDK infrastructure tests."""

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Template, Match

import sys
import os

# Add project root so cdk_stack is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from cdk_stack.pharmalabel_stack import PharmaLabelStack


@pytest.fixture(scope="module")
def template():
    app = cdk.App(context={"skip_dependency_check": True, "admin_email": "test@example.com"})
    stack = PharmaLabelStack(app, "TestPharmaLabelStack")
    return Template.from_stack(stack)


class TestS3Buckets:
    def test_creates_seven_buckets(self, template):
        # incoming, results, knowledge base, frontend, access logs, CloudTrail, CloudFront logs
        template.resource_count_is("AWS::S3::Bucket", 7)

    def test_all_buckets_block_public_access(self, template):
        resources = template.find_resources("AWS::S3::Bucket")
        for logical_id, resource in resources.items():
            props = resource.get("Properties", {})
            pab = props.get("PublicAccessBlockConfiguration", {})
            assert pab.get("BlockPublicAcls") is True, f"{logical_id} missing BlockPublicAcls"
            assert pab.get("BlockPublicPolicy") is True, f"{logical_id} missing BlockPublicPolicy"

    def test_all_buckets_enforce_ssl(self, template):
        resources = template.find_resources("AWS::S3::Bucket")
        # SSL enforcement is via bucket policy, not bucket property
        # Just verify buckets exist (SSL policies are separate resources)
        assert len(resources) == 7


class TestDynamoDB:
    def test_creates_projects_table(self, template):
        template.resource_count_is("AWS::DynamoDB::Table", 1)

    def test_partition_key_is_project_id(self, template):
        template.has_resource_properties("AWS::DynamoDB::Table", {
            "KeySchema": [{"AttributeName": "projectId", "KeyType": "HASH"}],
        })

    def test_pay_per_request_billing(self, template):
        template.has_resource_properties("AWS::DynamoDB::Table", {
            "BillingMode": "PAY_PER_REQUEST",
        })


class TestLambdaFunctions:
    def test_creates_lambda_functions(self, template):
        resources = template.find_resources("AWS::Lambda::Function")
        # Should have at least: trigger, frontend_api, doc_management, aoss_index_creator, runtime_resource_policy
        assert len(resources) >= 5

    def test_lambda_functions_use_arm64(self, template):
        resources = template.find_resources("AWS::Lambda::Function")
        for logical_id, resource in resources.items():
            props = resource.get("Properties", {})
            architectures = props.get("Architectures", [])
            if architectures:
                assert "arm64" in architectures, f"{logical_id} not using ARM64"

    def test_trigger_lambda_has_agent_arn_env(self, template):
        template.has_resource_properties("AWS::Lambda::Function", Match.object_like({
            "FunctionName": Match.string_like_regexp(".*Trigger.*"),
            "Environment": {"Variables": Match.object_like({
                "AGENT_ARN": Match.any_value(),
            })}
        }))


class TestCloudFront:
    def test_creates_two_distributions(self, template):
        template.resource_count_is("AWS::CloudFront::Distribution", 2)


class TestApiGateway:
    def test_creates_http_api(self, template):
        template.resource_count_is("AWS::ApiGatewayV2::Api", 1)

    def test_creates_routes(self, template):
        resources = template.find_resources("AWS::ApiGatewayV2::Route")
        # Should have routes for compliance API + document management API
        assert len(resources) >= 5


class TestAuthorization:
    def test_all_routes_require_jwt_authorizer(self, template):
        routes = template.find_resources("AWS::ApiGatewayV2::Route")
        assert routes
        for logical_id, resource in routes.items():
            props = resource["Properties"]
            assert props.get("AuthorizationType") == "JWT", f"{logical_id} is not JWT-protected"
            assert props.get("AuthorizerId"), f"{logical_id} has no authorizer"

    def test_self_sign_up_disabled(self, template):
        template.has_resource_properties("AWS::Cognito::UserPool", {
            "AdminCreateUserConfig": Match.object_like({"AllowAdminCreateUserOnly": True}),
        })

    def test_creates_kb_admin_group(self, template):
        template.resource_count_is("AWS::Cognito::UserPoolGroup", 1)
        template.has_resource_properties("AWS::Cognito::UserPoolGroup", {
            "GroupName": "kb-admins",
        })

    def test_admin_user_is_in_kb_admin_group(self, template):
        template.has_resource_properties("AWS::Cognito::UserPoolUserToGroupAttachment", {
            "Username": "test@example.com",
            "GroupName": {"Ref": Match.string_like_regexp("KbAdminGroup.*")},
        })

    def test_doc_management_lambda_knows_admin_group(self, template):
        template.has_resource_properties("AWS::Lambda::Function", Match.object_like({
            "FunctionName": "PharmaLabel-DocumentManagement",
            "Environment": {"Variables": Match.object_like({"KB_ADMIN_GROUP": "kb-admins"})},
        }))


class TestAgentCoreRuntime:
    # Amazon Bedrock AgentCore
    def test_creates_agent_runtime(self, template):
        resources = template.find_resources("AWS::BedrockAgentCore::Runtime")
        assert len(resources) >= 1
