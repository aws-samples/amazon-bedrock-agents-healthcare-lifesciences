from aws_cdk import (
    Stack,
    aws_iam as iam,
    CfnOutput,
    RemovalPolicy
)
from aws_cdk.aws_neptunegraph import CfnGraph
from constructs import Construct

class OMOPOntologyStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Neptune Analytics Graph
        graph = CfnGraph(
            self, "MyNeptuneAnalyticsGraph",
            graph_name="omop-ontology-graph",
            provisioned_memory=128,  # Minimum provisioned memory in GiB
            public_connectivity=True,  # Set to True if you need public access
            replica_count=0,  # Number of replicas for high availability
            deletion_protection=False,  # Set to True for production
            vector_search_configuration=CfnGraph.VectorSearchConfigurationProperty(
                vector_search_dimension=1024
            ),
            tags=[
                {
                    "key": "Environment",
                    "value": "development"
                },
                {
                    "key": "Project", 
                    "value": "OMOP-Ontology"
                }
            ]
        )

        # Apply removal policy for development
        graph.apply_removal_policy(RemovalPolicy.DESTROY)

        # Create IAM role for Neptune Analytics access
        # neptune_role = iam.Role(
        #     self, "NeptuneAnalyticsRole",
        #     assumed_by=iam.ServicePrincipal("neptuneanalytics.amazonaws.com"),
        #     inline_policies={
        #         "NeptuneAnalyticsPolicy": iam.PolicyDocument(
        #             statements=[
        #                 iam.PolicyStatement(
        #                     effect=iam.Effect.ALLOW,
        #                     actions=[
        #                         "neptune-analytics:*"
        #                     ],
        #                     resources=["*"]
        #                 )
        #             ]
        #         )
        #     }
        # )

        # Output the graph details
        CfnOutput(
            self, "GraphId",
            value=graph.attr_graph_id,
            description="Neptune Analytics Graph ID"
        )

        CfnOutput(
            self, "GraphArn", 
            value=graph.attr_graph_arn,
            description="Neptune Analytics Graph ARN"
        )

        CfnOutput(
            self, "GraphName",
            value=graph.graph_name,
            description="Neptune Analytics Graph Name"
        )