import boto3
import json
import time
from typing import List
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from strands_tools.code_interpreter.models import ExecuteCodeAction, ExecuteCommandAction
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter as CodeInterpreterClient
from utils.boto3_helper import find_s3_bucket_name_by_suffix, get_role_arn

# Get AWS account information
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
region = boto3.Session().region_name

# Define Bedrock model id
MODEL_ID = "global.anthropic.claude-sonnet-4-20250514-v1:0"

# Retrieve bucket information
s3_bucket = find_s3_bucket_name_by_suffix('-agent-build-bucket')
if not s3_bucket:
    print("Error: S3 bucket with suffix '-agent-build-bucket' not found!")

# Retrieve the IAM execution role for the code interpreter sandbox
execution_role_arn = get_role_arn('BedrockAgentCoreStrands')
print(f"Execution Role ARN: {execution_role_arn}")

# Create a custom code interpreter with the execution role
ci_client = CodeInterpreterClient(region)
interpreter_name = "statistician_interpreter"

try:
    ci_response = ci_client.create_code_interpreter(
        name=interpreter_name,
        execution_role_arn=execution_role_arn,
        description="Code interpreter with S3 access for statistician agent",
        network_configuration={"networkMode": "PUBLIC"}
    )
    custom_identifier = ci_response["codeInterpreterId"]
    print(f"Created custom code interpreter: {custom_identifier}")

    # Wait for the interpreter to become READY
    print("Waiting for code interpreter to be ready...")
    while True:
        status_response = ci_client.get_code_interpreter(interpreter_id=custom_identifier)
        status = status_response.get("status", "UNKNOWN")
        if status == "READY":
            print("Code interpreter is READY.")
            break
        elif status in ("FAILED", "DELETING"):
            raise RuntimeError(f"Code interpreter entered unexpected status: {status}")
        time.sleep(5)

except ci_client.control_plane_client.exceptions.ConflictException:
    # Interpreter already exists, retrieve its ID
    interpreters = ci_client.list_code_interpreters()
    custom_identifier = None
    for ci in interpreters.get("codeInterpreterSummaries", []):
        if ci["name"] == interpreter_name:
            custom_identifier = ci["codeInterpreterId"]
            break
    if not custom_identifier:
        raise RuntimeError(f"Code interpreter '{interpreter_name}' conflict but could not find existing one")
    print(f"Using existing custom code interpreter: {custom_identifier}")

# Initialize AgentCore CodeInterpreter with the custom identifier
code_interpreter = AgentCoreCodeInterpreter(
    region=region,
    identifier=custom_identifier,
    session_name="statistician-session"
)

# One-time sandbox setup: install required packages
_sandbox_initialized = False

def ensure_sandbox():
    """Install required packages in the CodeInterpreter sandbox on first use."""
    global _sandbox_initialized
    if not _sandbox_initialized:
        print("Installing packages in CodeInterpreter sandbox...")
        code_interpreter.execute_command(
            ExecuteCommandAction(
                type="executeCommand",
                command="pip install lifelines boto3 pandas numpy matplotlib"
            )
        )
        _sandbox_initialized = True
        print("Sandbox packages installed.")

print(f"Region: {region}")
print(f"Account ID: {account_id}")
print(f"S3 bucket: {s3_bucket}")

statistician_agent_name = 'Statistician-strands'
statistician_agent_description = "scientific analysis for survival analysis using Strands framework"
statistician_agent_instruction = f"""You are a medical research assistant AI specialized in survival analysis with biomarkers.
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

3. When you need to create a bar chart or any visualization not covered by the specialized tools:
   a. Use the run_code tool to write and execute Python code in the sandbox.
   b. Use matplotlib to create the chart and save the image to S3.
   c. The S3 bucket is: {s3_bucket}
   d. Save charts under the 'graphs/' prefix in the bucket.
   e. Use 'Agg' backend for matplotlib (matplotlib.use('Agg')).
   f. Use boto3 to upload the image to S3.

4. When providing your response:
   a. Start with a brief summary of your understanding of the user's query.
   b. Explain the steps you're taking to address the query.
   Ask for clarifications from the user if required.
   c. If you generate any charts or perform statistical analyses,
   explain their significance in the context of the user's query.
   d. Conclude with a concise summary of the findings and their potential implications for medical research.
   e. Make sure to explain any medical or statistical concepts in a clear, accessible manner.
"""


@tool
def run_code(code: str) -> str:
    """
    Execute Python code in the CodeInterpreter sandbox.
    Use this tool to write and run any Python code, including creating
    charts, performing calculations, or processing data.

    The sandbox has matplotlib, pandas, numpy, lifelines, and boto3 available.
    To save charts to S3, use boto3 to upload to the bucket and prefix shown below.

    S3 bucket: {s3_bucket}
    S3 prefix: graphs/

    Args:
        code (str): Python code to execute in the sandbox

    Returns:
        str: Output from the code execution
    """
    ensure_sandbox()

    print(f"\nExecuting code in sandbox...\n")
    result = code_interpreter.execute_code(
        ExecuteCodeAction(type="executeCode", code=code, language="python")
    )
    print(f"\nExecution result: {json.dumps(result, indent=2)}\n")
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
    ensure_sandbox()

    code = f"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter
import io
import boto3

biomarker_name = {repr(biomarker_name)}
duration_baseline = {duration_baseline}
event_baseline = {event_baseline}
duration_condition = {duration_condition}
event_condition = {event_condition}
s3_bucket = {repr(s3_bucket)}

baseline_label = '<=10'
condition_label = '>10'

kmf_baseline = KaplanMeierFitter()
kmf_baseline.fit(durations=duration_baseline, event_observed=event_baseline, label=baseline_label)

kmf_condition = KaplanMeierFitter()
kmf_condition.fit(durations=duration_condition, event_observed=event_condition, label=condition_label)

fig, ax = plt.subplots(figsize=(10, 6))
kmf_baseline.plot_survival_function(ax=ax, ci_show=True, color='blue')
kmf_condition.plot_survival_function(ax=ax, ci_show=True, color='darkorange')
ax.set_title(biomarker_name)
ax.set_xlabel('Timeline (days)')
ax.set_ylabel('Survival Probability')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)

img_data = io.BytesIO()
fig.savefig(img_data, format='png', dpi=150, bbox_inches='tight')
img_data.seek(0)

s3 = boto3.resource('s3')
key = f'graphs/{{biomarker_name}}_KMplot.png'
s3.Bucket(s3_bucket).put_object(Body=img_data, ContentType='image/png', Key=key)
print(f"Kaplan-Meier plot saved to s3://{{s3_bucket}}/{{key}}")
"""
    print(f"\nCreating Kaplan-Meier plot for: {biomarker_name}\n")
    result = code_interpreter.execute_code(
        ExecuteCodeAction(type="executeCode", code=code, language="python")
    )
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
    ensure_sandbox()

    code = f"""
import json
import boto3
import pandas as pd
import numpy as np
from lifelines import CoxPHFitter

bucket = {repr(bucket)}
key = {repr(key)}

# Read data from S3
s3 = boto3.client('s3')
obj = s3.get_object(Bucket=bucket, Key=key)
data = json.loads(obj['Body'].read().decode('utf-8'))

# Process clinical genomic data
columns = [col['name'] for col in data['ColumnMetadata']]
processed_records = []
for record in data['Records']:
    row = []
    for value in record:
        if 'stringValue' in value:
            row.append(value['stringValue'])
        elif 'doubleValue' in value:
            row.append(value['doubleValue'])
        elif 'booleanValue' in value:
            row.append(value['booleanValue'])
        else:
            row.append(None)
    processed_records.append(row)

df = pd.DataFrame(processed_records, columns=columns)

# Map survival status
df['survival_status'] = df['survival_status'].map({{False: 0, True: 1}})

# Data adjustments for alive patients
df.loc[df['survival_status'] == 0, 'survival_duration'] = 100
for biomarker in ['gdf15', 'lrig1', 'cdh2', 'postn', 'vcan']:
    if biomarker in df.columns:
        mask = df['survival_status'] == 0
        df.loc[mask, biomarker] = df.loc[mask, biomarker] + (np.random.rand(mask.sum()) * 30)

df_numeric = df.select_dtypes(include='number')

# Fit Cox Proportional Hazards model
cph = CoxPHFitter(penalizer=0.01)
cph.fit(df_numeric, duration_col='survival_duration', event_col='survival_status')
summary = cph.summary

print("Cox Proportional Hazards Regression Summary:")
print(summary.to_string())
"""
    print(f"\nFitting survival regression with data from s3://{bucket}/{key}\n")
    result = code_interpreter.execute_code(
        ExecuteCodeAction(type="executeCode", code=code, language="python")
    )
    print(f"\nSurvival Regression Output: {json.dumps(result, indent=2)}\n")
    return json.dumps(result, indent=2)


# Create list of tools
statistician_tools = [run_code, plot_kaplan_meier, fit_survival_regression]
print(f"Created {len(statistician_tools)} tools for the Strands agent")

# Create Bedrock model for Strands
model = BedrockModel(
    model_id=MODEL_ID,
    region_name=region,
    temperature=0.1,
    streaming=True
)
