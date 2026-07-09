"""Generate the AWS architecture diagram for the Connected Care Platform."""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.general import User
from diagrams.aws.compute import Lambda
from diagrams.aws.database import DynamodbTable
from diagrams.aws.network import CloudFront
from diagrams.aws.storage import S3
from diagrams.aws.security import Cognito
from diagrams.aws.integration import Eventbridge
from diagrams.aws.ml import Bedrock, Kendra

with Diagram("Connected Care Platform", show=False, direction="TB", filename="generated-diagrams/connected-care-aws-architecture",
             graph_attr={"fontsize": "12", "bgcolor": "white", "pad": "0.5", "nodesep": "0.5", "ranksep": "0.7", "dpi": "150"}):

    user = User("Clinician\n(React + Cloudscape)")

    with Cluster("Tier 1: Frontend & Authentication", graph_attr={"bgcolor": "#e8f4fd"}):
        cf = CloudFront("CloudFront CDN")
        s3_fe = S3("S3 Frontend")
        cognito = Cognito("Cognito\nUser Pool +\nIdentity Pool")

    with Cluster("Tier 2: API Layer (IAM Auth)", graph_attr={"bgcolor": "#fef3e0"}):
        proxy = Lambda("AgentCore Proxy\nFunction URL (AWS_IAM)")
        ddb_traces = DynamodbTable("Traces Table")

    with Cluster("Tier 3: Amazon Bedrock AgentCore", graph_attr={"bgcolor": "#e8f5e9"}):
        with Cluster("Orchestrator Agent"):
            orch = Bedrock("Orchestrator\n4 tools")
        with Cluster("Domain Agents (Strands SDK)"):
            pm = Bedrock("Patient Monitoring\n8 tools")
            dm = Bedrock("Device Management\n17 tools")
            pe = Bedrock("Patient Engagement\n20 tools")
        memory = Bedrock("AgentCore Memory\n(Short + Long Term)")

    with Cluster("Tier 4: AI Services", graph_attr={"bgcolor": "#f3e5f5"}):
        claude = Bedrock("Claude Opus 4")
        kb = Kendra("Knowledge Base\n37K Guidelines")
        s3v = S3("S3 Vectors")

    with Cluster("Tier 5: Data Layer", graph_attr={"bgcolor": "#fff8e1"}):
        ddb_pm = DynamodbTable("Patients + Vitals")
        ddb_dm = DynamodbTable("Devices + Telemetry")
        ddb_pe = DynamodbTable("Engagement + Meds")

    with Cluster("Tier 6: Events & Knowledge", graph_attr={"bgcolor": "#fce4ec"}):
        eb = Eventbridge("EventBridge\nClinical Events")
        s3_guide = S3("S3 Guidelines\n37K docs")

    # Connections
    user >> cf >> s3_fe
    user >> cognito >> Edge(label="SigV4", style="bold", color="darkblue") >> proxy
    proxy >> ddb_traces

    proxy >> orch
    orch >> pm
    orch >> dm
    orch >> pe

    pm >> claude
    dm >> claude
    pe >> claude
    orch >> claude

    pm - Edge(style="dashed", color="purple") - memory
    dm - Edge(style="dashed", color="purple") - memory
    pe - Edge(style="dashed", color="purple") - memory

    dm >> kb >> s3v
    s3_guide >> kb

    pm >> ddb_pm
    dm >> ddb_dm
    pe >> ddb_pe

    pm >> eb
    dm >> eb
    pe >> eb

print("Diagram generated: generated-diagrams/connected-care-aws-architecture.png")
