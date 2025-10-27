from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
from botocore.exceptions import ClientError
from utils import get_ssm_parameter

boto_session = Session()
region = boto_session.region_name


runtime_iam_role = get_ssm_parameter(
            "/app/researchapp/agentcore/runtime_iam_role"
)
agentcore_runtime = Runtime()

agent_name = "researchappagent"

response = agentcore_runtime.configure(
    entrypoint="main.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="dev-requirements.txt",
    region=region,
    agent_name=agent_name,
    execution_role=runtime_iam_role,   
)

# Configure
print(response)


launch_result = agentcore_runtime.launch()

import time

status_response = agentcore_runtime.status()
status = status_response.endpoint['status']
end_status = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']

while status not in end_status:
    time.sleep(10)
    status_response = agentcore_runtime.status()
    status = status_response.endpoint['status']
    print(status)

print(f"Agent status: {status}")
