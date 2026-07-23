import hashlib
import json
import os

# AWS Cloud Development Kit (AWS CDK) imports for Amazon S3, Amazon CloudFront,
# AWS Lambda, Amazon API Gateway, Amazon Bedrock, and Amazon OpenSearch Serverless
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
    aws_cognito as cognito,
    aws_opensearchserverless as aoss,
    aws_cloudtrail as cloudtrail,
    aws_wafv2 as wafv2,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_sqs as sqs,
    aws_lambda_destinations as lambda_destinations,
    aws_kms as kms,
)
import aws_cdk.aws_bedrockagentcore as agentcore
from constructs import Construct


class PharmaLabelStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Fail fast if the bundled runtime/Lambda dependencies are not installed.
        if not self.node.try_get_context("skip_dependency_check"):
            self._verify_bundled_dependencies()

        # Access to the app is gated by Amazon Cognito. The deployer MUST supply the email address of the initial (admin) user via context.
        self.admin_email = self._require_admin_email()

        # Generate a unique suffix using a hash of the stack's unique ID to avoid collisions
        unique_suffix = hashlib.md5(cdk.Names.unique_id(self).encode(), usedforsecurity=False).hexdigest()[:8]

        ## --- AMAZON S3 BUCKETS --- ##

        # Access Logs Bucket: receives S3 server access logs from the other buckets.
        self.access_logs_bucket = s3.Bucket(
            self,
            "AccessLogsBucket",
            bucket_name=f"pharmalabel-access-logs-{unique_suffix}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            lifecycle_rules=[s3.LifecycleRule(
                id="expire-logs",
                expiration=cdk.Duration.days(90),
                abort_incomplete_multipart_upload_after=cdk.Duration.days(7),
            )],
        )

        # Incoming Bucket: stores uploaded medicine label images
        self.incoming_bucket = s3.Bucket(
            self,
            "IncomingBucket",
            bucket_name=f"pharmalabel-incoming-labels-{unique_suffix}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            server_access_logs_bucket=self.access_logs_bucket,
            server_access_logs_prefix="incoming/",
            # Uploaded label images are transient (read once during processing);
            # expire them to avoid unbounded growth.
            lifecycle_rules=[s3.LifecycleRule(
                id="expire-incoming-uploads",
                expiration=cdk.Duration.days(730),  # 2 years
                abort_incomplete_multipart_upload_after=cdk.Duration.days(7),
            )],
        )

        # Results Bucket: stores processed compliance results
        self.results_bucket = s3.Bucket(
            self,
            "ResultsBucket",
            bucket_name=f"pharmalabel-processed-results-{unique_suffix}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            server_access_logs_bucket=self.access_logs_bucket,
            server_access_logs_prefix="results/",
        )

        # Knowledge Base Bucket: stores regulatory documents with versioning
        self.kb_bucket = s3.Bucket(
            self,
            "KnowledgeBaseBucket",
            bucket_name=f"pharmalabel-knowledge-base-{unique_suffix}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            server_access_logs_bucket=self.access_logs_bucket,
            server_access_logs_prefix="knowledge-base/",
            # Versioned: keep current documents indefinitely, but clean up
            # superseded (noncurrent) versions to bound storage growth.
            lifecycle_rules=[s3.LifecycleRule(
                id="expire-noncurrent-versions",
                noncurrent_version_expiration=cdk.Duration.days(730),  # 2 years
                abort_incomplete_multipart_upload_after=cdk.Duration.days(7),
            )],
        )

        # Frontend Bucket: static assets served via CloudFront (Origin Access Control (OAC), REST origin)
        self.frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=f"pharmalabel-frontend-{unique_suffix}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            server_access_logs_bucket=self.access_logs_bucket,
            server_access_logs_prefix="frontend/",
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

        ## --- AMAZON CLOUDFRONT DISTRIBUTIONS --- ##

        # AWS WAF (Web Application Firewall) Web access control list (ACL) (CLOUDFRONT scope) with AWS managed common rules,
        # attached to both distributions below.
        self.web_acl = wafv2.CfnWebACL(
            self,
            "CloudFrontWebAcl",
            scope="CLOUDFRONT",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="PharmaLabelWebAcl",
                sampled_requests_enabled=True,
            ),
            rules=[
                wafv2.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesCommonRuleSet",
                    priority=1,
                    override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesCommonRuleSet",
                        ),
                    ),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="AWSManagedRulesCommonRuleSet",
                        sampled_requests_enabled=True,
                    ),
                ),
            ],
        )

        # Dedicated CloudFront access-log bucket. CloudFront standard logging
        # requires ACLs enabled, so this bucket uses BUCKET_OWNER_PREFERRED
        # (separate from the other ACL-disabled buckets).
        self.cf_logs_bucket = s3.Bucket(
            self,
            "CloudFrontLogsBucket",
            bucket_name=f"pharmalabel-cf-logs-{unique_suffix}",
            # RETAIN + a dedicated emptier custom resource (below).
            # The bucket is retained because CloudFront logs are asynchronous.
            # The bucket is emptied by a custom resource (below) on stack deletion.
            removal_policy=RemovalPolicy.RETAIN,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
            server_access_logs_bucket=self.access_logs_bucket,
            server_access_logs_prefix="cf-logs-access/",
            lifecycle_rules=[s3.LifecycleRule(
                id="expire-logs",
                expiration=cdk.Duration.days(90),
                abort_incomplete_multipart_upload_after=cdk.Duration.days(7),
            )],
        )

        # Emptier custom resource for the (retained) CloudFront logs bucket.
        # Explicit log group so the emptier's logs are removed with the stack.
        cf_logs_emptier_log_group = logs.LogGroup(
            self,
            "CloudFrontLogsBucketEmptierLogs",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )
        cf_logs_emptier_fn = lambda_.Function(
            self,
            "CloudFrontLogsBucketEmptier",
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.ARM_64,
            tracing=lambda_.Tracing.ACTIVE,
            code=lambda_.Code.from_asset("custom_resources/bucket_emptier"),
            handler="index.handler",
            timeout=cdk.Duration.minutes(15),
            log_group=cf_logs_emptier_log_group,
        )
        cf_logs_emptier_fn.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "s3:ListBucket",
                "s3:ListBucketVersions",
                "s3:GetBucketLocation",
                "s3:DeleteObject",
                "s3:DeleteObjectVersion",
                "s3:DeleteBucket",
            ],
            resources=[
                self.cf_logs_bucket.bucket_arn,
                self.cf_logs_bucket.arn_for_objects("*"),
            ],
        ))
        self.cf_logs_emptier = cdk.CustomResource(
            self,
            "CloudFrontLogsBucketEmptierCR",
            service_token=cf_logs_emptier_fn.function_arn,
            properties={"BucketName": self.cf_logs_bucket.bucket_name},
        )
        self.cf_logs_emptier.node.add_dependency(self.cf_logs_bucket)

        # Results Amazon CloudFront Distribution: serves processed results from Results Bucket
        self.results_cf = cloudfront.Distribution(
            self,
            "ResultsDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(   # Uses OAC for secure Amazon S3 access
                    self.results_bucket
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            web_acl_id=self.web_acl.attr_arn,
            enable_logging=True,
            log_bucket=self.cf_logs_bucket,
            log_file_prefix="results/",
        )

        # Frontend Amazon CloudFront Distribution: serves static frontend from Frontend Bucket
        self.frontend_cf = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(   # Uses OAC for secure Amazon S3 access
                    self.frontend_bucket
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            web_acl_id=self.web_acl.attr_arn,
            enable_logging=True,
            log_bucket=self.cf_logs_bucket,
            log_file_prefix="frontend/",
        )

        # Force both distributions to be deleted before the emptier runs, so
        # CloudFront has stopped generating new logs by the time we drain the
        # bucket. (Delete order is the reverse of dependency order.)
        self.results_cf.node.add_dependency(self.cf_logs_emptier)
        self.frontend_cf.node.add_dependency(self.cf_logs_emptier)

        # Build the frontend origin URL for cross-origin resource sharing (CORS) (used by Amazon S3 buckets and API Gateway)
        self.frontend_origin = cdk.Fn.join("", ["https://", self.frontend_cf.distribution_domain_name])

        # Add scoped CORS rules to Amazon S3 buckets now that we know the Amazon CloudFront domain
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

        ## --- AMAZON DYNAMODB TABLE --- ##

        self.projects_table = cdk.aws_dynamodb.Table(
            self,
            "ProjectsTable",
            table_name=f"pharmalabel-projects-{unique_suffix}",
            partition_key=cdk.aws_dynamodb.Attribute(
                name="projectId",
                type=cdk.aws_dynamodb.AttributeType.STRING,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=cdk.aws_dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=cdk.aws_dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery_specification=cdk.aws_dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
            ),
        )

        # CloudTrail trail capturing account management (control-plane) events
        # for audit logging. This records API activity such as DynamoDB table
        # changes, IAM updates, and resource configuration changes.
        self.trail_bucket = s3.Bucket(
            self,
            "TrailBucket",
            bucket_name=f"pharmalabel-cloudtrail-{unique_suffix}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            server_access_logs_bucket=self.access_logs_bucket,
            server_access_logs_prefix="cloudtrail/",
            lifecycle_rules=[s3.LifecycleRule(
                id="expire-logs",
                expiration=cdk.Duration.days(90),
                abort_incomplete_multipart_upload_after=cdk.Duration.days(7),
            )],
        )
        # CloudTrail bucket policy (required for trail creation)
        trail_name = f"pharmalabel-trail-{unique_suffix}"
        trail_arn = f"arn:aws:cloudtrail:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:trail/{trail_name}"
        self.trail_bucket.add_to_resource_policy(iam.PolicyStatement(
            actions=["s3:GetBucketAcl"],
            principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
            resources=[self.trail_bucket.bucket_arn],
            conditions={"StringEquals": {
                "aws:SourceArn": trail_arn,
                "aws:SourceAccount": cdk.Aws.ACCOUNT_ID,
            }},
        ))
        self.trail_bucket.add_to_resource_policy(iam.PolicyStatement(
            actions=["s3:PutObject"],
            principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
            resources=[self.trail_bucket.arn_for_objects(f"AWSLogs/{cdk.Aws.ACCOUNT_ID}/*")],
            conditions={"StringEquals": {
                "s3:x-amz-acl": "bucket-owner-full-control",
                "aws:SourceArn": trail_arn,
                "aws:SourceAccount": cdk.Aws.ACCOUNT_ID,
            }},
        ))

        self.audit_trail = cloudtrail.CfnTrail(
            self,
            "AuditTrail",
            trail_name=trail_name,
            is_logging=True,
            s3_bucket_name=self.trail_bucket.bucket_name,
            enable_log_file_validation=True,
            include_global_service_events=True,
            is_multi_region_trail=False,
            advanced_event_selectors=[
                cloudtrail.CfnTrail.AdvancedEventSelectorProperty(
                    name="Management events",
                    field_selectors=[
                        cloudtrail.CfnTrail.AdvancedFieldSelectorProperty(field="eventCategory", equal_to=["Management"]),
                    ],
                ),
            ],
        )
        # Trail creation requires the bucket policy to exist first.
        self.audit_trail.node.add_dependency(self.trail_bucket.policy)

        ## --- AMAZON BEDROCK KNOWLEDGE BASE --- ##

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
            },
        )

        ## --- AMAZON OPENSEARCH SERVERLESS VECTOR STORE --- ##

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

        # Network policy (allow public access for Amazon Bedrock)
        net_policy = aoss.CfnSecurityPolicy(
            self,
            "AOSSNetworkPolicy",
            name=f"kb-net-{unique_suffix}",
            type="network",
            policy=json.dumps([{
                "Rules": [
                    {"ResourceType": "collection", "Resource": [f"collection/kb-{unique_suffix}"]},
                ],
                "AllowFromPublic": True,
            }]),
        )

        # The Amazon OpenSearch Serverless collection
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

        # Grant the KB role data-plane access scoped to this collection
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                actions=["aoss:APIAccessAll"],
                resources=[self.aoss_collection.attr_arn],
            )
        )

        # AWS Lambda that creates the vector index via custom resource (below)
        index_creator_fn = lambda_.Function(
            self,
            "AOSSIndexCreator",
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.ARM_64,
            tracing=lambda_.Tracing.ACTIVE,
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

        # Data access policy (must include both KB role and index creator AWS Lambda role)
        data_access_policy = aoss.CfnAccessPolicy(
            self,
            "AOSSDataAccessPolicy",
            name=f"kb-data-{unique_suffix}",
            type="data",
            policy=cdk.Fn.sub(
                json.dumps([
                    {
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
                        "Principal": ["${KBRoleArn}"],
                    },
                    {
                        "Rules": [
                            {
                                "ResourceType": "index",
                                "Resource": [f"index/kb-{unique_suffix}/*"],
                                "Permission": ["aoss:CreateIndex", "aoss:DescribeIndex"],
                            },
                            {
                                "ResourceType": "collection",
                                "Resource": [f"collection/kb-{unique_suffix}"],
                                "Permission": ["aoss:DescribeCollectionItems"],
                            },
                        ],
                        "Principal": ["${IndexCreatorRoleArn}"],
                    },
                ]),
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
            "PharmaLabelKB",
            name="PharmaLabelKB",
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

        # Amazon S3 Data Sources

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
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.ARM_64,
            tracing=lambda_.Tracing.ACTIVE,
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

        ## --- AMAZON BEDROCK AGENTCORE RUNTIME --- ##

        # Bedrock Guardrail applied to agent model calls.
        self.guardrail = bedrock.CfnGuardrail(
            self,
            "AgentGuardrail",
            name=f"pharmalabel-guardrail-{unique_suffix}",
            blocked_input_messaging="This request was blocked by content safety guardrails.",
            blocked_outputs_messaging="This response was blocked by content safety guardrails.",
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="HATE", input_strength="LOW", output_strength="NONE"),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="INSULTS", input_strength="LOW", output_strength="NONE"),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="SEXUAL", input_strength="LOW", output_strength="NONE"),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="VIOLENCE", input_strength="LOW", output_strength="NONE"),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(type="MISCONDUCT", input_strength="LOW", output_strength="NONE"),
                ],
            ),
            word_policy_config=bedrock.CfnGuardrail.WordPolicyConfigProperty(
                managed_word_lists_config=[
                    bedrock.CfnGuardrail.ManagedWordsConfigProperty(type="PROFANITY"),
                ],
            ),
        )
        self.guardrail_version = bedrock.CfnGuardrailVersion(
            self,
            "AgentGuardrailVersion",
            guardrail_identifier=self.guardrail.attr_guardrail_id,
        )

        # CloudWatch dashboard reporting Guardrail interventions, so any time the
        # guardrail blocks a request or response it is visible for review.
        _gr_dims = {
            "GuardrailArn": self.guardrail.attr_guardrail_arn,
            "GuardrailVersion": self.guardrail_version.attr_version,
        }
        self.guardrail_dashboard = cloudwatch.Dashboard(
            self,
            "GuardrailDashboard",
            dashboard_name=f"PharmaLabel-Guardrail-{unique_suffix}",
            widgets=[[
                cloudwatch.GraphWidget(
                    title="Guardrail Interventions",
                    left=[cloudwatch.Metric(
                        namespace="AWS/Bedrock/Guardrails",
                        metric_name="InvocationsIntervened",
                        dimensions_map=_gr_dims,
                        statistic="Sum",
                        period=cdk.Duration.minutes(5),
                    )],
                    width=12,
                ),
                cloudwatch.GraphWidget(
                    title="Guardrail Invocations",
                    left=[cloudwatch.Metric(
                        namespace="AWS/Bedrock/Guardrails",
                        metric_name="Invocations",
                        dimensions_map=_gr_dims,
                        statistic="Sum",
                        period=cdk.Duration.minutes(5),
                    )],
                    width=12,
                ),
            ]],
        )

        # Deploy agent code (Amazon Bedrock AgentCore L2 construct -> from_code_asset)
        agent_runtime_artifact = agentcore.AgentRuntimeArtifact.from_code_asset(
            path="agent_package",
            runtime=agentcore.AgentCoreRuntime.PYTHON_3_12,
            entrypoint=["orchestrator.py"],
            exclude=["__pycache__", "*.pyc", "*.pyo"],
        )

        self.agent_runtime = agentcore.Runtime(
            self,
            "AgentRuntime",
            runtime_name="PharmaLabelRuntime",
            agent_runtime_artifact=agent_runtime_artifact,
            description="PharmaLabel: multi-agent compliance pipeline for pharmaceutical label analysis",
            environment_variables={
                "INCOMING_BUCKET": self.incoming_bucket.bucket_name,
                "RESULTS_BUCKET": self.results_bucket.bucket_name,
                "FRONTEND_BUCKET": self.frontend_bucket.bucket_name,
                "KNOWLEDGE_BASE_ID": self.knowledge_base_id,
                "PROJECTS_TABLE": self.projects_table.table_name,
                "CLOUDFRONT_URL": cdk.Fn.join("", ["https://", self.results_cf.distribution_domain_name]),
                "AWS_DEFAULT_REGION": cdk.Aws.REGION,
                "LOG_LEVEL": "WARNING",
                "GUARDRAIL_ID": self.guardrail.attr_guardrail_id,
                "GUARDRAIL_VERSION": self.guardrail_version.attr_version,
            },
        )

        # Allow the runtime to apply the Bedrock Guardrail on model calls.
        self.agent_runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:ApplyGuardrail"],
                resources=[self.guardrail.attr_guardrail_arn],
            )
        )

        # Grant the runtime permissions to invoke Amazon Bedrock models (foundation + inference profiles)
        self.agent_runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-6",
                    "arn:aws:bedrock:*::foundation-model/anthropic.claude-opus-4-7",
                    "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0",
                    cdk.Fn.sub("arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:inference-profile/us.anthropic.claude-sonnet-4-6"),
                    cdk.Fn.sub("arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:inference-profile/us.anthropic.claude-opus-4-7"),
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

        # Grant Amazon Textract permissions (used by Agent 2 for coordinate detection).
        # Resource "*" is required: Amazon Textract DetectDocumentText does not support
        # resource-level permissions per AWS service authorization. Scope is limited by the
        # aws:RequestedRegion condition below. See:
        # https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazontextract.html
        self.agent_runtime.add_to_role_policy(
            iam.PolicyStatement(
                actions=["textract:DetectDocumentText"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "aws:RequestedRegion": cdk.Aws.REGION,
                    }
                },
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

        # Store the agent runtime Amazon Resource Name (ARN) for downstream references (Lambdas, policies)
        self.agent_runtime_arn = self.agent_runtime.agent_runtime_arn

        ## --- AWS LAMBDA FUNCTIONS --- ##

        # 1. Compliance API AWS Lambda
        self.compliancelambda = lambda_.Function(
            self,
            "ComplianceApiLambda",
            function_name="PharmaLabel-ComplianceApi",
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.ARM_64,
            tracing=lambda_.Tracing.ACTIVE,
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
                "LOG_LEVEL": "WARNING",
            },
        )

        # IAM: read + put on Incoming Bucket (presigned PUT URLs require s3:PutObject)
        self.incoming_bucket.grant_read(self.compliancelambda)
        self.compliancelambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject", "s3:PutObjectTagging"],
                resources=[self.incoming_bucket.arn_for_objects("*")],
            )
        )

        # IAM: read on Results Bucket
        self.results_bucket.grant_read(self.compliancelambda)

        # IAM: read/write on Projects DynamoDB table
        self.projects_table.grant_read_write_data(self.compliancelambda)

        # 2. Document Management AWS Lambda
        self.doc_managementlambda = lambda_.Function(
            self,
            "DocumentManagementLambda",
            function_name="PharmaLabel-DocumentManagement",
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.ARM_64,
            tracing=lambda_.Tracing.ACTIVE,
            code=lambda_.Code.from_asset("lambda_functions/document_management"),
            handler="index.lambda_handler",
            timeout=cdk.Duration.seconds(15),
            memory_size=256,
            environment={
                "KB_BUCKET": self.kb_bucket.bucket_name,
                "KNOWLEDGE_BASE_ID": self.knowledge_base_id,
                "FRONTEND_ORIGIN": self.frontend_origin,
                "LOG_LEVEL": "WARNING",
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

        # 3. Trigger AWS Lambda
        self.triggerlambda = lambda_.Function(
            self,
            "TriggerLambda",
            function_name="PharmaLabel-TriggerLambda",
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.ARM_64,
            tracing=lambda_.Tracing.ACTIVE,
            code=lambda_.Code.from_asset("lambda_functions/trigger"),
            handler="index.lambda_handler",
            timeout=cdk.Duration.seconds(10),
            memory_size=512,
            environment={
                "INCOMING_BUCKET": self.incoming_bucket.bucket_name,
                "AGENT_ARN": self.agent_runtime_arn,
                "RESULTS_BUCKET": self.results_bucket.bucket_name,
                "LOG_LEVEL": "WARNING",
            },
        )

        # IAM: read on Incoming Bucket
        self.incoming_bucket.grant_read(self.triggerlambda)
        self.triggerlambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObjectTagging"],
                resources=[self.incoming_bucket.arn_for_objects("*")],
            )
        )

        # IAM: Grant Trigger AWS Lambda permission to invoke the Agent Runtime
        self.agent_runtime.grant_invoke(self.triggerlambda)

        # Resource-based policy on Amazon Bedrock AgentCore Runtime (required for InvokeAgentRuntime)
        # The identity-based policy from grant_invoke is not sufficient alone;
        # Amazon Bedrock AgentCore also requires a resource-based policy on the runtime itself.
        resource_policy_fn = lambda_.Function(
            self,
            "RuntimeResourcePolicyFn",
            runtime=lambda_.Runtime.PYTHON_3_14,
            architecture=lambda_.Architecture.ARM_64,
            tracing=lambda_.Tracing.ACTIVE,
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

        # Trigger AWS Lambda on s3:ObjectCreated:* events with prefix filter "labels/"
        self.incoming_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.triggerlambda),
            s3.NotificationKeyFilter(prefix="labels/"),
        )

        ## --- MONITORING & ALERTING --- ##
        # SNS topic for operational alarms.
        self.alarm_topic = sns.Topic(
            self,
            "AlarmTopic",
            topic_name=f"pharmalabel-alarms-{unique_suffix}",
            master_key=kms.Alias.from_alias_name(self, "SnsManagedKey", "alias/aws/sns"),
            enforce_ssl=True,
        )
        self.alarm_topic.add_subscription(sns_subs.EmailSubscription(self.admin_email))

        # Dead-letter queue for failed asynchronous trigger-Lambda invocations.
        self.trigger_dlq = sqs.Queue(
            self,
            "TriggerDlq",
            queue_name=f"pharmalabel-trigger-dlq-{unique_suffix}",
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            enforce_ssl=True,
            retention_period=cdk.Duration.days(14),
        )
        # Route failed asynchronous invocations of the S3-triggered Lambda to the dead-letter queue (DLQ).
        self.triggerlambda.configure_async_invoke(
            on_failure=lambda_destinations.SqsDestination(self.trigger_dlq),
            retry_attempts=2,
        )

        # Alarm when failed async invocations land in the DLQ.
        cloudwatch.Alarm(
            self,
            "TriggerDlqAlarm",
            metric=self.trigger_dlq.metric_approximate_number_of_messages_visible(
                period=cdk.Duration.minutes(5), statistic="Maximum"
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Asynchronous trigger-Lambda invocations are failing (messages in DLQ).",
        ).add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # Error alarms on the application Lambdas.
        for _alarm_name, _fn in (
            ("ComplianceApi", self.compliancelambda),
            ("DocumentManagement", self.doc_managementlambda),
            ("Trigger", self.triggerlambda),
        ):
            cloudwatch.Alarm(
                self,
                f"{_alarm_name}ErrorsAlarm",
                metric=_fn.metric_errors(period=cdk.Duration.minutes(5), statistic="Sum"),
                threshold=1,
                evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                alarm_description=f"{_alarm_name} Lambda is reporting errors.",
            ).add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        ## --- AMAZON COGNITO (API authentication) --- ##
        # The API is protected by a Cognito JSON Web Token (JWT) authorizer. Self sign-up is
        # disabled; the only user is the admin created below from `admin_email`.
        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"pharmalabel-users-{unique_suffix}",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=False),
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            # multi-factor authentication (MFA) left optional
            mfa=cognito.Mfa.OPTIONAL,
            mfa_second_factor=cognito.MfaSecondFactor(otp=True, sms=False),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            feature_plan=cognito.FeaturePlan.PLUS,
            standard_threat_protection_mode=cognito.StandardThreatProtectionMode.FULL_FUNCTION,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Hosted UI domain for the login flow.
        self.user_pool_domain = self.user_pool.add_domain(
            "UserPoolDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"pharmalabel-{unique_suffix}",
            ),
        )

        # Public single-page application (SPA) app client (no secret) using OAuth Authorization Code + Proof Key for Code Exchange (PKCE).
        _callback_urls = [
            self.frontend_origin,
            cdk.Fn.join("", [self.frontend_origin, "/"]),
            cdk.Fn.join("", [self.frontend_origin, "/index.html"]),
            cdk.Fn.join("", [self.frontend_origin, "/project.html"]),
            cdk.Fn.join("", [self.frontend_origin, "/settings.html"]),
        ]
        self.user_pool_client = self.user_pool.add_client(
            "WebClient",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(user_srp=True),
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO,
            ],
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=_callback_urls,
                logout_urls=_callback_urls,
            ),
            prevent_user_existence_errors=True,
            access_token_validity=cdk.Duration.hours(1),
            id_token_validity=cdk.Duration.hours(1),
            refresh_token_validity=cdk.Duration.days(1),
        )

        # Create the initial admin user from the deployer-provided email. Cognito
        # emails them a temporary password (no credential is stored in the repo).
        self.admin_user = cognito.CfnUserPoolUser(
            self,
            "AdminUser",
            user_pool_id=self.user_pool.user_pool_id,
            username=self.admin_email,
            desired_delivery_mediums=["EMAIL"],
            user_attributes=[
                cognito.CfnUserPoolUser.AttributeTypeProperty(name="email", value=self.admin_email),
                cognito.CfnUserPoolUser.AttributeTypeProperty(name="email_verified", value="true"),
            ],
        )

        ## --- AMAZON API GATEWAY --- ##

        # HTTP API with CORS configuration
        self.api = apigwv2.CfnApi(
            self,
            "HttpApi",
            name="PharmaLabelApi",
            protocol_type="HTTP",
            cors_configuration=apigwv2.CfnApi.CorsProperty(
                allow_origins=[self.frontend_origin],
                allow_methods=["POST", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization"],
            ),
        )

        # JWT authorizer backed by the Cognito user pool. Every route below
        # requires a valid Cognito ID token, so the API authenticates all callers.
        self.api_authorizer = apigwv2.CfnAuthorizer(
            self,
            "CognitoJwtAuthorizer",
            api_id=self.api.ref,
            authorizer_type="JWT",
            name="CognitoJwtAuthorizer",
            identity_source=["$request.header.Authorization"],
            jwt_configuration=apigwv2.CfnAuthorizer.JWTConfigurationProperty(
                audience=[self.user_pool_client.user_pool_client_id],
                issuer=cdk.Fn.join("", [
                    "https://cognito-idp.",
                    cdk.Aws.REGION,
                    ".amazonaws.com/",
                    self.user_pool.user_pool_id,
                ]),
            ),
        )

        # CloudWatch log group for HTTP API access logs.
        self.api_log_group = logs.LogGroup(
            self,
            "HttpApiAccessLogs",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Auto-deploy stage with access logging enabled
        self.api_stage = apigwv2.CfnStage(
            self,
            "HttpApiDefaultStage",
            api_id=self.api.ref,
            stage_name="$default",
            auto_deploy=True,
            access_log_settings=apigwv2.CfnStage.AccessLogSettingsProperty(
                destination_arn=self.api_log_group.log_group_arn,
                format=json.dumps({
                    "requestId": "$context.requestId",
                    "ip": "$context.identity.sourceIp",
                    "requestTime": "$context.requestTime",
                    "httpMethod": "$context.httpMethod",
                    "routeKey": "$context.routeKey",
                    "status": "$context.status",
                    "protocol": "$context.protocol",
                    "responseLength": "$context.responseLength",
                }),
            ),
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

        # Routes for Compliance API AWS Lambda
        compliance_routes = ["/upload", "/check", "/projects/list", "/projects/save", "/projects/delete"]
        for route_path in compliance_routes:
            route_id = route_path.strip("/").replace("/", "-").title()
            apigwv2.CfnRoute(
                self,
                f"Route{route_id}",
                api_id=self.api.ref,
                route_key=f"POST {route_path}",
                target=cdk.Fn.join("/", ["integrations", compliance_integration.ref]),
                authorization_type="JWT",
                authorizer_id=self.api_authorizer.ref,
            )

        # Routes for Document Management AWS Lambda
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
                authorization_type="JWT",
                authorizer_id=self.api_authorizer.ref,
            )

        # Grant API Gateway permission to invoke the AWS Lambda functions
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

        # Deploy config.js with the real API Gateway URL + Cognito config (must
        # happen after the API and the Cognito client are created).
        config_content = cdk.Fn.sub(
            "const API_ENDPOINT = 'https://${ApiId}.execute-api.${AWS::Region}.amazonaws.com';\n"
            f"const COGNITO = {{ domain: 'https://pharmalabel-{unique_suffix}.auth.${{AWS::Region}}.amazoncognito.com', "
            "clientId: '${ClientId}', region: '${AWS::Region}' };\n",
            {
                "ApiId": self.api.ref,
                "ClientId": self.user_pool_client.user_pool_client_id,
            },
        )
        self.frontend_config_deployment = s3deploy.BucketDeployment(
            self, "FrontendConfigDeployment",
            sources=[
                s3deploy.Source.data("config.js", config_content),
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
        cdk.CfnOutput(self, "AdminUserEmail", value=self.admin_email)
        cdk.CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        cdk.CfnOutput(self, "CognitoHostedUiDomain", value=cdk.Fn.sub(f"https://pharmalabel-{unique_suffix}.auth.${{AWS::Region}}.amazoncognito.com"))
        cdk.CfnOutput(self, "FrontendCloudFrontUrl", value=cdk.Fn.join("", ["https://", self.frontend_cf.distribution_domain_name]))
        cdk.CfnOutput(self, "AgentRuntimeArn", value=self.agent_runtime_arn)
        cdk.CfnOutput(self, "KnowledgeBaseId", value=self.knowledge_base_id)

    def _require_admin_email(self) -> str:
        """Return the validated admin email from context, or fail synth/deploy.

        Access to the deployed app is gated by Cognito, and the initial user is
        created from this email. Refusing to synthesize without it guarantees the
        solution is never deployed with an unauthenticated API.
        """
        email = self.node.try_get_context("admin_email")
        if (
            not isinstance(email, str)
            or email.count("@") != 1
            or not email.split("@")[0]
            or "." not in email.split("@")[1]
            or email.split("@")[1].startswith(".")
            or email.split("@")[1].endswith(".")
        ):
            raise RuntimeError(
                "A valid admin email is required to deploy this solution. The initial "
                "Cognito user is created from it and receives a temporary password by "
                "email. Provide it via context:\n"
                "  cdk deploy -c admin_email=you@example.com"
            )
        return email

    def _verify_bundled_dependencies(self) -> None:
        """Reject synth/deploy if bundled dependencies have not been installed.

        The AgentCore runtime and the OpenSearch index-creator Lambda require
        third-party packages to be installed into their asset directories before
        deployment (see the Deployment section of the README). If they are
        missing, deployment produces a runtime that fails to import its modules.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # asset directory -> a package directory that only exists once deps are installed
        required = {
            "agent_package": "strands",
            os.path.join("custom_resources", "aoss_index_creator"): "opensearchpy",
        }
        missing = [
            bundle for bundle, sentinel in required.items()
            if not os.path.isdir(os.path.join(project_root, bundle, sentinel))
        ]
        if missing:
            raise RuntimeError(
                "Bundled dependencies are not installed for: " + ", ".join(missing) + ".\n"
                "Install them before deploying (see the README 'Deployment' section):\n"
                "  pip install --platform manylinux2014_aarch64 --implementation cp "
                "--python-version 3.12 --only-binary=:all: --target agent_package/ "
                "-r agent_runtime_requirements.txt\n"
                "  pip install -r custom_resources/aoss_index_creator/requirements.txt "
                "-t custom_resources/aoss_index_creator\n"
                "  pip install -r custom_resources/runtime_resource_policy/requirements.txt "
                "-t custom_resources/runtime_resource_policy"
            )
