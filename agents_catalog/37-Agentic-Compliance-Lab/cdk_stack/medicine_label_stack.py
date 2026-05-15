import hashlib
import json

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_s3_notifications as s3n,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigwv2,
    aws_bedrock as bedrock,
    aws_opensearchserverless as aoss,
)
import aws_cdk.aws_bedrock_agentcore_alpha as agentcore
from constructs import Construct


class MedicineLabelComplianceStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Generate a unique suffix using a hash of the stack's unique ID to avoid collisions
        unique_suffix = hashlib.md5(cdk.Names.unique_id(self).encode()).hexdigest()[:8]

        ## --- S3 BUCKETS --- ##

        # Incoming Bucket: stores uploaded medicine label images
        self.incoming_bucket = s3.Bucket(
            self,
            "IncomingBucket",
            bucket_name=f"agenticlabcompliance-incoming-labels-{unique_suffix}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        # Results Bucket: stores processed compliance results
        self.results_bucket = s3.Bucket(
            self,
            "ResultsBucket",
            bucket_name=f"agenticlabcompliance-processed-results-{unique_suffix}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        # Knowledge Base Bucket: stores regulatory documents with versioning
        self.kb_bucket = s3.Bucket(
            self,
            "KnowledgeBaseBucket",
            bucket_name=f"agentic-compliance-knowledge-base-{unique_suffix}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        # Frontend Bucket: hosts static website
        self.frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=f"agenticlabcompliance-frontend-{unique_suffix}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            website_index_document="index.html",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        # Seed Knowledge Base Bucket with regulatory documents
        # Documents in kb_documents/US_FDA/ → s3://kb-bucket/US_FDA/
        # Documents in kb_documents/UK_MHRA/ → s3://kb-bucket/UK_MHRA/
        s3deploy.BucketDeployment(
            self, "KBDocumentsDeployment",
            sources=[s3deploy.Source.asset("kb_documents")],
            destination_bucket=self.kb_bucket,
            prune=False,  # Don't delete existing documents
        )

        ## --- CLOUDFRONT DISTRIBUTIONS --- ##

        # Results CloudFront Distribution: serves processed results from Results Bucket
        self.results_cf = cloudfront.Distribution(
            self,
            "ResultsDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(   # Uses Origin Access Control (OAC) for secure S3 access
                    self.results_bucket
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
        )

        # Frontend CloudFront Distribution: serves static frontend from Frontend Bucket
        self.frontend_cf = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(   # Uses Origin Access Control (OAC) for secure S3 access
                    self.frontend_bucket
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
        )

        # Build the frontend origin URL for CORS (used by S3 buckets and API Gateway)
        self.frontend_origin = cdk.Fn.join("", ["https://", self.frontend_cf.distribution_domain_name])

        # Add scoped CORS rules to S3 buckets now that we know the CloudFront domain
        cfn_incoming: s3.CfnBucket = self.incoming_bucket.node.default_child
        cfn_incoming.cors_configuration = s3.CfnBucket.CorsConfigurationProperty(
            cors_rules=[s3.CfnBucket.CorsRuleProperty(
                allowed_methods=["PUT", "GET"],
                allowed_origins=[self.frontend_origin],
                allowed_headers=["*"],
            )]
        )

        cfn_results: s3.CfnBucket = self.results_bucket.node.default_child
        cfn_results.cors_configuration = s3.CfnBucket.CorsConfigurationProperty(
            cors_rules=[s3.CfnBucket.CorsRuleProperty(
                allowed_methods=["PUT", "GET"],
                allowed_origins=[self.frontend_origin],
                allowed_headers=["*"],
            )]
        )

        # Deploy frontend static assets (excluding config.js which needs the API URL)
        self.frontend_deployment = s3deploy.BucketDeployment(
            self, "FrontendDeployment",
            sources=[s3deploy.Source.asset("frontend", exclude=["config.js"])],
            destination_bucket=self.frontend_bucket,
            distribution=self.frontend_cf,
            prune=False,
        )

        ## --- DYNAMODB TABLE --- ##

        self.projects_table = cdk.aws_dynamodb.Table(
            self,
            "ProjectsTable",
            table_name=f"agenticlabcompliance-projects-{unique_suffix}",
            partition_key=cdk.aws_dynamodb.Attribute(
                name="projectId",
                type=cdk.aws_dynamodb.AttributeType.STRING,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=cdk.aws_dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery=True,
        )

        ## --- BEDROCK KNOWLEDGE BASE --- ##

        # IAM role for the Knowledge Base service
        self.kb_role = iam.Role(
            self,
            "KnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            inline_policies={
                "KBBucketReadAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:GetObject", "s3:ListBucket"],
                            resources=[
                                self.kb_bucket.bucket_arn,
                                self.kb_bucket.arn_for_objects("*"),
                            ],
                        ),
                    ]
                ),
                "BedrockEmbeddingAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["bedrock:InvokeModel"],
                            resources=[
                                cdk.Fn.sub(
                                    "arn:aws:bedrock:${AWS::Region}::foundation-model/amazon.titan-embed-text-v2:0"
                                ),
                            ],
                        ),
                    ]
                ),
                "AOSSAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["aoss:APIAccessAll"],
                            resources=[
                                cdk.Fn.sub(
                                    "arn:aws:aoss:${AWS::Region}:${AWS::AccountId}:collection/*"
                                ),
                            ],
                        ),
                    ]
                ),
            },
        )

        ## --- OPENSEARCH SERVERLESS VECTOR STORE --- ##

        # Encryption policy (required before collection creation)
        enc_policy = aoss.CfnSecurityPolicy(
            self,
            "AOSSEncryptionPolicy",
            name=f"kb-enc-{unique_suffix}",
            type="encryption",
            policy=json.dumps({
                "Rules": [{"ResourceType": "collection", "Resource": [f"collection/kb-{unique_suffix}"]}],
                "AWSOwnedKey": True,
            }),
        )

        # Network policy (allow public access for Bedrock)
        net_policy = aoss.CfnSecurityPolicy(
            self,
            "AOSSNetworkPolicy",
            name=f"kb-net-{unique_suffix}",
            type="network",
            policy=json.dumps([{
                "Rules": [
                    {"ResourceType": "collection", "Resource": [f"collection/kb-{unique_suffix}"]},
                    {"ResourceType": "dashboard", "Resource": [f"collection/kb-{unique_suffix}"]},
                ],
                "AllowFromPublic": True,
            }]),
        )

        # The OpenSearch Serverless collection
        self.aoss_collection = aoss.CfnCollection(
            self,
            "AOSSCollection",
            name=f"kb-{unique_suffix}",
            type="VECTORSEARCH",
        )
        # must wait for policies
        self.aoss_collection.add_dependency(enc_policy)
        self.aoss_collection.add_dependency(net_policy)
        
        self.aoss_collection.apply_removal_policy(RemovalPolicy.DESTROY)

        # Lambda that creates the vector index via custom resource (below)
        index_creator_fn = lambda_.Function(
            self,
            "AOSSIndexCreator",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            code=lambda_.Code.from_asset("custom_resources/aoss_index_creator"),
            handler="index.handler",
            timeout=cdk.Duration.minutes(15),
        )
        index_creator_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["aoss:APIAccessAll"],
                resources=[self.aoss_collection.attr_arn],
            )
        )

        # Data access policy (must include both KB role and index creator Lambda role)
        data_access_policy = aoss.CfnAccessPolicy(
            self,
            "AOSSDataAccessPolicy",
            name=f"kb-data-{unique_suffix}",
            type="data",
            policy=cdk.Fn.sub(
                json.dumps([{
                    "Rules": [
                        {
                            "ResourceType": "index",
                            "Resource": [f"index/kb-{unique_suffix}/*"],
                            "Permission": [
                                "aoss:CreateIndex", "aoss:UpdateIndex", "aoss:DescribeIndex",
                                "aoss:ReadDocument", "aoss:WriteDocument",
                            ],
                        },
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/kb-{unique_suffix}"],
                            "Permission": [
                                "aoss:CreateCollectionItems", "aoss:UpdateCollectionItems",
                                "aoss:DescribeCollectionItems",
                            ],
                        },
                    ],
                    "Principal": [
                        "${KBRoleArn}",
                        "${IndexCreatorRoleArn}",
                        "arn:aws:iam::${AWS::AccountId}:root",
                    ],
                }]),
                {
                    "KBRoleArn": self.kb_role.role_arn,
                    "IndexCreatorRoleArn": index_creator_fn.role.role_arn,
                },
            ),
        )

        aoss_index = cdk.CustomResource(
            self,
            "AOSSVectorIndex",
            service_token=index_creator_fn.function_arn,
            properties={
                "CollectionEndpoint": self.aoss_collection.attr_collection_endpoint,
                "Region": cdk.Aws.REGION,
                "IndexName": "bedrock-kb-index",
                "Dimension": "1024",
            },
        )
        aoss_index.node.add_dependency(self.aoss_collection)
        aoss_index.node.add_dependency(data_access_policy)

        # The knowledge base (using OpenSearch Serverless)
        self.knowledge_base = bedrock.CfnKnowledgeBase(
            self,
            "MedicineLabelComplianceKB",
            name="MedicineLabelComplianceKB",
            role_arn=self.kb_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=cdk.Fn.sub(
                        "arn:aws:bedrock:${AWS::Region}::foundation-model/amazon.titan-embed-text-v2:0"
                    ),
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
                    collection_arn=self.aoss_collection.attr_arn,
                    field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
                        metadata_field="AMAZON_BEDROCK_METADATA",
                        text_field="AMAZON_BEDROCK_TEXT_CHUNK",
                        vector_field="bedrock-knowledge-base-default-vector",
                    ),
                    vector_index_name="bedrock-kb-index",
                ),
            ),
        )
        self.knowledge_base.add_dependency(aoss_index.node.default_child)

        self.knowledge_base_id = self.knowledge_base.attr_knowledge_base_id

        self.kb_arn = cdk.Fn.sub(
            "arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:knowledge-base/${KbId}",
            {"KbId": self.knowledge_base_id},
        )

        # S3 Data Sources

        # 1. US FDA
        self.kb_data_source_fda = bedrock.CfnDataSource(
            self,
            "KBDataSourceFDA",
            knowledge_base_id=self.knowledge_base_id,
            name="US-FDA-Regulatory-Documents",
            data_deletion_policy="RETAIN",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=self.kb_bucket.bucket_arn,
                    inclusion_prefixes=["US_FDA/"],
                ),
            ),
        )

        # 2. UK MHRA
        self.kb_data_source_mhra = bedrock.CfnDataSource(
            self,
            "KBDataSourceMHRA",
            knowledge_base_id=self.knowledge_base_id,
            name="UK-MHRA-Regulatory-Documents",
            data_deletion_policy="RETAIN",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=self.kb_bucket.bucket_arn,
                    inclusion_prefixes=["UK_MHRA/"],
                ),
            ),
        )

        # Ingest both data sources sequentially (only 1 concurrent job allowed per KB).
        ingest_fn = lambda_.Function(
            self,
            "KBIngestFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            handler="index.handler",
            timeout=cdk.Duration.minutes(15),
            code=lambda_.Code.from_inline("\n".join([
                "import boto3, json, time, urllib.request",
                "def send(event, ctx, status):",
                "    body = json.dumps({'Status': status, 'Reason': 'See CloudWatch', 'PhysicalResourceId': event.get('PhysicalResourceId', ctx.log_stream_name), 'StackId': event['StackId'], 'RequestId': event['RequestId'], 'LogicalResourceId': event['LogicalResourceId']}).encode()",
                "    urllib.request.urlopen(urllib.request.Request(event['ResponseURL'], data=body, headers={'Content-Type': ''}, method='PUT'))",
                "def handler(event, ctx):",
                "    if event['RequestType'] != 'Create':",
                "        return send(event, ctx, 'SUCCESS')",
                "    try:",
                "        client = boto3.client('bedrock-agent')",
                "        kb_id = event['ResourceProperties']['KnowledgeBaseId']",
                "        ds_ids = event['ResourceProperties']['DataSourceIds']",
                "        for ds_id in ds_ids:",
                "            job = client.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)['ingestionJob']",
                "            while job['status'] in ('STARTING', 'IN_PROGRESS'):",
                "                time.sleep(10)",
                "                job = client.get_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id, ingestionJobId=job['ingestionJobId'])['ingestionJob']",
                "            if job['status'] != 'COMPLETE':",
                "                print(f'Ingestion {ds_id} ended with status: {job[\"status\"]}')",
                "    except Exception as e: print(e)",
                "    send(event, ctx, 'SUCCESS')",
            ])),
        )
        ingest_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:StartIngestionJob", "bedrock:GetIngestionJob"],
                resources=[self.kb_arn],
            )
        )
        cdk.CustomResource(
            self,
            "KBIngestAll",
            service_token=ingest_fn.function_arn,
            properties={
                "KnowledgeBaseId": self.knowledge_base_id,
                "DataSourceIds": [
                    self.kb_data_source_fda.attr_data_source_id,
                    self.kb_data_source_mhra.attr_data_source_id,
                ],
            },
        )

        ## --- BEDROCK AGENTCORE RUNTIME --- ##

        # Deploy agent code (AgentCore L2 construct -> from_code_asset)
        agent_runtime_artifact = agentcore.AgentRuntimeArtifact.from_code_asset(
            path="agent_package", # contains agents source + pre-installed dependencies
            runtime=agentcore.AgentCoreRuntime.PYTHON_3_12,
            entrypoint=["orchestrator.py"],
            exclude=["__pycache__", "*.pyc", "*.pyo"],
        )

        self.agent_runtime = agentcore.Runtime(
            self,
            "AgentRuntime",
            runtime_name="MedicineLabelComplianceRuntime",
            agent_runtime_artifact=agent_runtime_artifact,
            description="Multi-agent compliance pipeline for medicine label analysis",
            environment_variables={
                "INCOMING_BUCKET": self.incoming_bucket.bucket_name,
                "RESULTS_BUCKET": self.results_bucket.bucket_name,
                "FRONTEND_BUCKET": self.frontend_bucket.bucket_name,
                "KNOWLEDGE_BASE_ID": self.knowledge_base_id,
                "PROJECTS_TABLE": self.projects_table.table_name,
                "CLOUDFRONT_URL": cdk.Fn.join("", ["https://", self.results_cf.distribution_domain_name]),
                "AWS_DEFAULT_REGION": cdk.Aws.REGION,
            },
        )

        # Grant the runtime permissions to invoke Bedrock models (foundation + inference profiles)
        self.agent_runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*",
                ],
            )
        )

        # Grant read/write on Results Bucket
        self.agent_runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
                resources=[
                    self.results_bucket.bucket_arn,
                    self.results_bucket.arn_for_objects("*"),
                ],
            )
        )

        # Grant read on Incoming Bucket
        self.agent_runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    self.incoming_bucket.bucket_arn,
                    self.incoming_bucket.arn_for_objects("*"),
                ],
            )
        )

        # Grant read on Frontend Bucket (for compliant.png badge)
        self.agent_runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[
                    self.frontend_bucket.arn_for_objects("compliant.png"),
                ],
            )
        )

        # Grant Textract permissions (used by Agent 2 sync for coordinate detection)
        # Textract does not support resource-level permissions — wildcard is required
        self.agent_runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "textract:DetectDocumentText",
                ],
                resources=["*"],
            )
        )

        # Grant bedrock:Retrieve on Knowledge Base
        self.agent_runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:Retrieve"],
                resources=[self.kb_arn],
            )
        )

        # Grant DynamoDB read/write for pipeline progress updates
        self.agent_runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                ],
                resources=[self.projects_table.table_arn],
            )
        )

        # Store the agent runtime ARN for downstream references (Lambdas, policies)
        self.agent_runtime_arn = self.agent_runtime.agent_runtime_arn

        ## --- LAMBDA FUNCTIONS --- ##

        # 1. Compliance API Lambda
        self.compliancelambda = lambda_.Function(
            self,
            "ComplianceApiLambda",
            function_name="CUSTOM-ComplianceApi",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            code=lambda_.Code.from_asset("lambda_functions/frontend_api"),
            handler="index.lambda_handler",
            timeout=cdk.Duration.minutes(15),
            memory_size=256,
            environment={
                "INCOMING_BUCKET": self.incoming_bucket.bucket_name,
                "RESULTS_BUCKET": self.results_bucket.bucket_name,
                "CLOUDFRONT_URL": cdk.Fn.join("", ["https://", self.results_cf.distribution_domain_name]),
                "PROJECTS_TABLE": self.projects_table.table_name,
                "FRONTEND_ORIGIN": self.frontend_origin,
            },
        )

        # IAM: read/write on Incoming Bucket (including PutObjectTagging)
        self.incoming_bucket.grant_read_write(self.compliancelambda)
        self.compliancelambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:PutObjectTagging"],
                resources=[self.incoming_bucket.arn_for_objects("*")],
            )
        )

        # IAM: read on Results Bucket
        self.results_bucket.grant_read(self.compliancelambda)

        # IAM: read/write on Projects DynamoDB table
        self.projects_table.grant_read_write_data(self.compliancelambda)

        # 2. Document Management Lambda
        self.doc_managementlambda = lambda_.Function(
            self,
            "DocumentManagementLambda",
            function_name="CUSTOM-DocumentManagement",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            code=lambda_.Code.from_asset("lambda_functions/document_management"),
            handler="index.lambda_handler",
            timeout=cdk.Duration.seconds(15),
            memory_size=256,
            environment={
                "KB_BUCKET": self.kb_bucket.bucket_name,
                "KNOWLEDGE_BASE_ID": self.knowledge_base_id,
                "FRONTEND_ORIGIN": self.frontend_origin,
            },
        )

        # IAM: read/write on Knowledge Base Bucket
        self.kb_bucket.grant_read_write(self.doc_managementlambda)

        # IAM: bedrock:StartIngestionJob and bedrock:GetIngestionJob
        self.doc_managementlambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:StartIngestionJob", "bedrock:GetIngestionJob", "bedrock:ListDataSources"],
                resources=[self.kb_arn],
            )
        )

        # 3. Trigger Lambda
        self.triggerlambda = lambda_.Function(
            self,
            "TriggerLambda",
            function_name="CUSTOM-TriggerLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            code=lambda_.Code.from_asset("lambda_functions/trigger"),
            handler="index.lambda_handler",
            timeout=cdk.Duration.seconds(10),
            memory_size=512,
            environment={
                "INCOMING_BUCKET": self.incoming_bucket.bucket_name,
                "AGENT_ARN": self.agent_runtime_arn,
                "RESULTS_BUCKET": self.results_bucket.bucket_name,
            },
        )

        # IAM: read on Incoming Bucket (including GetObjectTagging)
        self.incoming_bucket.grant_read(self.triggerlambda)
        self.triggerlambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObjectTagging"],
                resources=[self.incoming_bucket.arn_for_objects("*")],
            )
        )

        # IAM: Grant Trigger Lambda permission to invoke the Agent Runtime
        self.agent_runtime.grant_invoke(self.triggerlambda)

        # Resource-based policy on AgentCore Runtime (required for InvokeAgentRuntime)
        # The identity-based policy from grant_invoke is not sufficient alone;
        # AgentCore also requires a resource-based policy on the runtime itself.
        resource_policy_fn = lambda_.Function(
            self,
            "RuntimeResourcePolicyFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            code=lambda_.Code.from_asset("custom_resources/runtime_resource_policy"),
            handler="index.handler",
            timeout=cdk.Duration.seconds(30),
        )
        resource_policy_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock-agentcore:PutResourcePolicy",
                    "bedrock-agentcore:DeleteResourcePolicy",
                ],
                resources=[self.agent_runtime_arn],
            )
        )

        policy_doc = cdk.Fn.sub(
            '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"${RoleArn}"},"Action":["bedrock-agentcore:InvokeAgentRuntime","bedrock-agentcore:InvokeAgentRuntimeForUser"],"Resource":"${RuntimeArn}"}]}',
            {
                "RoleArn": self.triggerlambda.role.role_arn,
                "RuntimeArn": self.agent_runtime_arn,
            },
        )

        cdk.CustomResource(
            self,
            "AgentRuntimeResourcePolicy",
            service_token=resource_policy_fn.function_arn,
            properties={
                "RuntimeArn": self.agent_runtime_arn,
                "Policy": policy_doc,
            },
        )

        # Trigger Lambda on s3:ObjectCreated:* events with prefix filter "labels/"
        self.incoming_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.triggerlambda),
            s3.NotificationKeyFilter(prefix="labels/"),
        )

        ## --- API GATEWAY --- ##

        # HTTP API with CORS configuration
        self.api = apigwv2.CfnApi(
            self,
            "HttpApi",
            name="MedicineLabelComplianceApi",
            protocol_type="HTTP",
            cors_configuration=apigwv2.CfnApi.CorsProperty(
                allow_origins=[self.frontend_origin],
                allow_methods=["POST", "OPTIONS"],
                allow_headers=["Content-Type"],
            ),
        )

        # Auto-deploy stage
        self.api_stage = apigwv2.CfnStage(
            self,
            "HttpApiDefaultStage",
            api_id=self.api.ref,
            stage_name="$default",
            auto_deploy=True,
        )

        # Integration for Compliance API Lambda (AWS_PROXY)
        compliance_integration = apigwv2.CfnIntegration(
            self,
            "ComplianceApiIntegration",
            api_id=self.api.ref,
            integration_type="AWS_PROXY",
            integration_uri=self.compliancelambda.function_arn,
            payload_format_version="2.0",
        )

        # Integration for Document Management Lambda (AWS_PROXY)
        doc_mgmt_integration = apigwv2.CfnIntegration(
            self,
            "DocManagementIntegration",
            api_id=self.api.ref,
            integration_type="AWS_PROXY",
            integration_uri=self.doc_managementlambda.function_arn,
            payload_format_version="2.0",
        )

        # Routes for Compliance API Lambda
        compliance_routes = ["/upload", "/check", "/projects/list", "/projects/save", "/projects/delete"]
        for route_path in compliance_routes:
            route_id = route_path.strip("/").replace("/", "-").title()
            apigwv2.CfnRoute(
                self,
                f"Route{route_id}",
                api_id=self.api.ref,
                route_key=f"POST {route_path}",
                target=cdk.Fn.join("/", ["integrations", compliance_integration.ref]),
            )

        # Routes for Document Management Lambda
        doc_routes = [
            "/documents/list",
            "/documents/upload",
            "/documents/delete",
            "/documents/download",
            "/documents/sync",
        ]
        for route_path in doc_routes:
            route_id = route_path.strip("/").replace("/", "-").title()
            apigwv2.CfnRoute(
                self,
                f"Route{route_id}",
                api_id=self.api.ref,
                route_key=f"POST {route_path}",
                target=cdk.Fn.join("/", ["integrations", doc_mgmt_integration.ref]),
            )

        # Grant API Gateway permission to invoke the Lambda functions
        self.compliancelambda.add_permission(
            "ApiGwInvokeCompliance",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            source_arn=cdk.Fn.sub(
                "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${ApiId}/*/*",
                {"ApiId": self.api.ref},
            ),
        )

        self.doc_managementlambda.add_permission(
            "ApiGwInvokeDocManagement",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            source_arn=cdk.Fn.sub(
                "arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:${ApiId}/*/*",
                {"ApiId": self.api.ref},
            ),
        )

        # Deploy config.js with the real API Gateway URL (must happen after API is created)
        api_url = cdk.Fn.sub(
            "https://${ApiId}.execute-api.${AWS::Region}.amazonaws.com",
            {"ApiId": self.api.ref},
        )
        self.frontend_config_deployment = s3deploy.BucketDeployment(
            self, "FrontendConfigDeployment",
            sources=[
                s3deploy.Source.data(
                    "config.js",
                    cdk.Fn.sub(
                        "const API_ENDPOINT = '${Url}';",
                        {"Url": api_url},
                    ),
                ),
            ],
            destination_bucket=self.frontend_bucket,
            distribution=self.frontend_cf,
            prune=False,  # Don't delete other files
        )
        self.frontend_config_deployment.node.add_dependency(self.frontend_deployment)

        ## --- STACK OUTPUTS --- ##
        cdk.CfnOutput(self, "IncomingBucketName", value=self.incoming_bucket.bucket_name)
        cdk.CfnOutput(self, "ResultsBucketName", value=self.results_bucket.bucket_name)
        cdk.CfnOutput(self, "KnowledgeBaseBucketName", value=self.kb_bucket.bucket_name)
        cdk.CfnOutput(self, "ApiGatewayEndpoint", value=cdk.Fn.sub("https://${ApiId}.execute-api.${AWS::Region}.amazonaws.com", {"ApiId": self.api.ref}))
        cdk.CfnOutput(self, "ResultsCloudFrontDomain", value=self.results_cf.distribution_domain_name)
        cdk.CfnOutput(self, "FrontendCloudFrontUrl", value=cdk.Fn.join("", ["https://", self.frontend_cf.distribution_domain_name]))
        cdk.CfnOutput(self, "AgentRuntimeArn", value=self.agent_runtime_arn)
        cdk.CfnOutput(self, "KnowledgeBaseId", value=self.knowledge_base_id)
