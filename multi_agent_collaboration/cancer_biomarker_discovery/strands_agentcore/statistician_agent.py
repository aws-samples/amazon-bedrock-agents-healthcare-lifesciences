
import boto3
import json
import uuid
import requests
from typing import Dict, Any, List
from strands import Agent, tool
from strands.models import BedrockModel

# Get AWS account information
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
region = boto3.Session().region_name

# Lambda function configurations (reusing existing infrastructure)
bar_chart_lambda_function_name = "MatPlotBarChartLambda"  # Change if different in your account
scientific_plot_lambda_function_name = "ScientificPlotLambda"  # Change if different in your account

bar_chart_lambda_function_arn = f"arn:aws:lambda:{region}:{account_id}:function:{bar_chart_lambda_function_name}"
scientific_plot_lambda_function_arn = f"arn:aws:lambda:{region}:{account_id}:function:{scientific_plot_lambda_function_name}"

# Initialize AWS clients
lambda_client = boto3.client('lambda', region_name=region)
bedrock_client = boto3.client('bedrock-runtime', region_name=region)

print(f"Bar Chart Lambda ARN: {bar_chart_lambda_function_arn}")
print(f"Scientific Plot Lambda ARN: {scientific_plot_lambda_function_arn}")
print(f"Region: {region}")
print(f"Account ID: {account_id}")

statistician_agent_name = 'Statistician-strands'
statistician_agent_description = "scientific analysis for survival analysis using Strands framework"
statistician_agent_instruction = """You are a medical research assistant AI specialized in survival analysis with biomarkers. 
Your primary job is to interpret user queries, run scientific analysis tasks, and provide relevant medical insights 
with available visualization tools. Use only the appropriate tools as required by the specific question. 
Follow these instructions carefully: 

1. If the user query requires a Kaplan-Meier chart: 
   a. Map survival status as 0 for Alive and 1 for Dead for the event parameter. 
   b. Use survival duration as the duration parameter. 
   c. Use the group_survival_data tool to create baseline and condition group based on expression value threshold provided by the user. 

2. If a survival regression analysis is needed: 
   a. You need access to all records with columns start with survival status as first column, then survival duration, and the required biomarkers. 
   b. Use the fit_survival_regression tool to identify the best-performing biomarker based on the p-value summary. 
   c. Ask for S3 data location if not provided, do not assume S3 bucket names or object names. 

3. When you need to create a bar chart or plot: 
   a. Always pass x_values and y_values in Array type to the function. 
   If the user says x values are apple,egg and y values are 3,4 or as [apple,egg] and [3,4] pass their value as 
   ['apple', 'egg'] and [3,4] 

4. When providing your response: 
   a. Start with a brief summary of your understanding of the user's query. 
   b. Explain the steps you're taking to address the query. 
   Ask for clarifications from the user if required. 
   c. If you generate any charts or perform statistical analyses, 
   explain their significance in the context of the user's query. 
   d. Conclude with a concise summary of the findings and their potential implications for medical research. 
   e. Make sure to explain any medical or statistical concepts in a clear, accessible manner.
""" 

def invoke_lambda_function(function_arn: str, operation: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Helper function to invoke the existing Lambda functions with Bedrock Agent compatible event structure
    """
    if payload is None:
        payload = {}
    
    # Prepare the event payload to match what the Lambda function expects from Bedrock Agents
    if operation == 'bar_chart':
        event = {
            'agent': 'strands-agent',
            'actionGroup': 'matplotbarchart',
            'function': 'bar_chart',
            'messageVersion': '1.0',
            'parameters': [
                {
                    'name': 'title',
                    'type': 'string',
                    'value': payload.get('title', '')
                },
                {
                    'name': 'x_label',
                    'type': 'string',
                    'value': payload.get('x_label', '')
                },
                {
                    'name': 'x_values',
                    'type': 'array',
                    'value': json.dumps(payload.get('x_values', []))  # Convert to JSON string
                },
                {
                    'name': 'y_label',
                    'type': 'string',
                    'value': payload.get('y_label', '')
                },
                {
                    'name': 'y_values',
                    'type': 'array',
                    'value': str(payload.get('y_values', []))  # Convert to string representation
                }
            ],
            'sessionAttributes': {},
            'promptSessionAttributes': {}
        }
    elif operation == 'plot_kaplan_meier':
        event = {
            'agent': 'strands-agent',
            'actionGroup': 'scientificAnalysisActionGroup',
            'function': 'plot_kaplan_meier',
            'messageVersion': '1.0',
            'parameters': [
                {
                    'name': 'biomarker_name',
                    'type': 'string',
                    'value': payload.get('biomarker_name', '')
                },
                {
                    'name': 'duration_baseline',
                    'type': 'array',
                    'value': str(payload.get('duration_baseline', []))  # Convert to string
                },
                {
                    'name': 'duration_condition',
                    'type': 'array',
                    'value': str(payload.get('duration_condition', []))  # Convert to string
                },
                {
                    'name': 'event_baseline',
                    'type': 'array',
                    'value': str(payload.get('event_baseline', []))  # Convert to string
                },
                {
                    'name': 'event_condition',
                    'type': 'array',
                    'value': str(payload.get('event_condition', []))  # Convert to string
                }
            ],
            'sessionAttributes': {},
            'promptSessionAttributes': {}
        }
    elif operation == 'fit_survival_regression':
        event = {
            'agent': 'strands-agent',
            'actionGroup': 'scientificAnalysisActionGroup',
            'function': 'fit_survival_regression',
            'messageVersion': '1.0',
            'parameters': [
                {
                    'name': 'bucket',
                    'type': 'string',
                    'value': payload.get('bucket', '')
                },
                {
                    'name': 'key',
                    'type': 'string',
                    'value': payload.get('key', '')
                }
            ],
            'sessionAttributes': {},
            'promptSessionAttributes': {}
        }
    else:
        raise ValueError(f"Unknown operation: {operation}")
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_arn,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        result = json.loads(response['Payload'].read())
        
        # Extract the actual result from the response
        if isinstance(result, dict) and 'response' in result:
            return result['response']
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

# Define the tools using Strands @tool decorator
@tool
def create_bar_chart(title: str, x_label: str, x_values: List[str], y_label: str, y_values: List[float]) -> str:
    """
    Create a bar chart with the specified parameters.
    
    Args:
        title (str): Title of the bar chart
        x_label (str): Label for the x-axis
        x_values (List[str]): Values for the x-axis (categories)
        y_label (str): Label for the y-axis
        y_values (List[float]): Values for the y-axis (numerical data)
    
    Returns:
        str: Result of the bar chart creation
    """
    payload = {
        'title': title,
        'x_label': x_label,
        'x_values': x_values,
        'y_label': y_label,
        'y_values': y_values
    }
    
    print(f"\nBar Chart Input: {json.dumps(payload, indent=2)}\n")
    result = invoke_lambda_function(bar_chart_lambda_function_arn, 'bar_chart', payload)
    print(f"\nBar Chart Output: {json.dumps(result, indent=2)}\n")
    return json.dumps(result, indent=2)

@tool
def plot_kaplan_meier(biomarker_name: str, duration_baseline: List[float], duration_condition: List[float], 
                     event_baseline: List[int], event_condition: List[int]) -> str:
    """
    Create a Kaplan-Meier survival plot for comparing two groups.
    
    Args:
        biomarker_name (str): Name of the biomarker being analyzed
        duration_baseline (List[float]): Survival duration in days for baseline group
        duration_condition (List[float]): Survival duration in days for condition group
        event_baseline (List[int]): Survival events for baseline (0=alive, 1=dead)
        event_condition (List[int]): Survival events for condition (0=alive, 1=dead)
    
    Returns:
        str: Result of the Kaplan-Meier plot creation
    """
    payload = {
        'biomarker_name': biomarker_name,
        'duration_baseline': duration_baseline,
        'duration_condition': duration_condition,
        'event_baseline': event_baseline,
        'event_condition': event_condition
    }
    
    print(f"\nKaplan-Meier Input: {json.dumps(payload, indent=2)}\n")
    result = invoke_lambda_function(scientific_plot_lambda_function_arn, 'plot_kaplan_meier', payload)
    print(f"\nKaplan-Meier Output: {json.dumps(result, indent=2)}\n")
    return json.dumps(result, indent=2)

@tool
def fit_survival_regression(bucket: str, key: str) -> str:
    """
    Fit a survival regression model using data from an S3 object.
    
    Args:
        bucket (str): S3 bucket where the data is stored
        key (str): JSON file name in the S3 bucket containing the data for model fitting
    
    Returns:
        str: Results of the survival regression analysis
    """
    payload = {
        'bucket': bucket,
        'key': key
    }
    
    print(f"\nSurvival Regression Input: {json.dumps(payload, indent=2)}\n")
    result = invoke_lambda_function(scientific_plot_lambda_function_arn, 'fit_survival_regression', payload)
    print(f"\nSurvival Regression Output: {json.dumps(result, indent=2)}\n")
    return json.dumps(result, indent=2)

# Create list of tools
statistician_tools = [create_bar_chart, plot_kaplan_meier, fit_survival_regression]
print(f"Created {len(statistician_tools)} tools for the Strands agent")

# Create Bedrock model for Strands
model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name=region,
    temperature=0.1,
    streaming=False
)
