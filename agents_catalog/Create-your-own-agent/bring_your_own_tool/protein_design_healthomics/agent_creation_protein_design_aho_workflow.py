import boto3
import json
import uuid
import time
from IPython.display import display, Markdown

# Initialize AWS clients
region = boto3.Session().region_name
account_id = boto3.client('sts').get_caller_identity()['Account']
bedrock_agent_client = boto3.client('bedrock-agent')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
cloudformation = boto3.client('cloudformation')

# Get the HealthOmics workflow details from CloudFormation stack
def get_workflow_details():
    response = cloudformation.describe_stacks(
        StackName='hcls-bedrock-agents-byot-aho-stack'
    )
    
    outputs = {output['OutputKey']: output['OutputValue'] 
              for output in response['Stacks'][0]['Outputs']}
    
    return outputs

workflow_details = get_workflow_details()
workflow_id = workflow_details['WorkflowId']

# Create Lambda function for workflow invocation
lambda_client = boto3.client('lambda')

lambda_code = """
import boto3
import json

def handler(event, context):
    omics = boto3.client('omics')
    
    try:
        # Extract parameters from the event
        workflow_id = event['workflow_id']
        run_name = event.get('run_name', f'run-{int(time.time())}')
        parameters = event.get('parameters', {})
        output_uri = event['output_uri']
        
        # Start the workflow run
        response = omics.start_run(
            workflowId=workflow_id,
            name=run_name,
            parameters=parameters,
            outputUri=output_uri
        )
        
        return {
            'statusCode': 200,
            'body': {
                'runId': response['id'],
                'status': response['status']
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {
                'error': str(e)
            }
        }
"""

# Create Lambda function
lambda_role_arn = "arn:aws:iam::YOUR_ACCOUNT_ID:role/YOUR_LAMBDA_ROLE"  # Replace with your Lambda role ARN

response = lambda_client.create_function(
    FunctionName='healthomics-workflow-invoke',
    Runtime='python3.9',
    Role=lambda_role_arn,
    Handler='index.handler',
    Code={'ZipFile': lambda_code.encode()},
    Description='Lambda function to invoke HealthOmics workflow',
    Timeout=30,
    MemorySize=128,
    Publish=True
)

lambda_function_arn = response['FunctionArn']

# Define the agent
agent_name = 'HealthOmics-Workflow-Agent'
agent_description = "Agent for invoking HealthOmics workflows"
agent_instruction = """You are an expert at managing and running HealthOmics workflows. Your primary task is to help users run workflow analyses and provide relevant insights.

When providing your response:
a. Start with a brief summary of your understanding of the user's request
b. Explain the steps you're taking to execute the workflow
c. Present the results or status of the workflow execution

Always ensure to:
1. Validate input parameters before running workflows
2. Provide clear feedback about workflow status
3. Handle errors gracefully and suggest solutions
"""

# Define the function schema for workflow invocation
function_defs = [{
    'name': 'invoke_workflow',
    'description': 'Start a HealthOmics workflow run',
    'parameters': {
        'workflow_id': {
            'type': 'string',
            'description': 'ID of the workflow to run'
        },
        'run_name': {
            'type': 'string',
            'description': 'Name for the workflow run'
        },
        'parameters': {
            'type': 'object',
            'description': 'Parameters for the workflow run'
        },
        'output_uri': {
            'type': 'string',
            'description': 'S3 URI for workflow outputs'
        }
    },
    'requireConfirmation': 'DISABLED'
}]

# Create the agent
response = bedrock_agent_client.create_agent(
    agentName=agent_name,
    description=agent_description,
    instruction=agent_instruction,
    type='PROVIDED'
)

agent_id = response['agent']['agentId']
agent_arn = response['agent']['agentArn']

print(f"Created agent: {agent_id}")

# Create action group
response = bedrock_agent_client.create_agent_action_group(
    agentId=agent_id,
    actionGroupName='HealthOmics-Actions',
    actionGroupExecutor={
        'lambda': {
            'lambdaArn': lambda_function_arn
        }
    },
    description='Actions for invoking HealthOmics workflows',
    apiSchema=json.dumps({
        'openapi': '3.0.0',
        'info': {
            'title': 'HealthOmics Workflow API',
            'version': '1.0.0'
        },
        'paths': {
            '/invoke_workflow': {
                'post': {
                    'operationId': 'invoke_workflow',
                    'description': 'Start a HealthOmics workflow run',
                    'requestBody': {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'workflow_id': {'type': 'string'},
                                        'run_name': {'type': 'string'},
                                        'parameters': {'type': 'object'},
                                        'output_uri': {'type': 'string'}
                                    },
                                    'required': ['workflow_id', 'output_uri']
                                }
                            }
                        }
                    }
                }
            }
        }
    })
)

# Create agent alias
response = bedrock_agent_client.create_agent_alias(
    agentId=agent_id,
    agentAliasName='prod',
    description='Production version of the HealthOmics workflow agent'
)

agent_alias_id = response['agentAlias']['agentAliasId']

# Test the agent
def test_agent():
    session_id = str(uuid.uuid4())
    
    test_query = "Start a workflow run with the following parameters: output to s3://my-bucket/outputs/"
    
    response = bedrock_agent_runtime.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        inputText=test_query
    )
    
    for event in response['completion']:
        if 'chunk' in event:
            chunk = json.loads(event['chunk']['bytes'].decode())
            if 'content' in chunk:
                print(f"Agent response: {chunk['content']}")

# Run test
test_agent()

print("\nAgent setup complete!")
