import os
os.environ['MPLCONFIGDIR'] = '/tmp'
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import io
import boto3
import ast

import logging
import uuid

from typing import Dict, Any
from http import HTTPStatus

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

import re

def parse_non_json_data_string(data_str: str):
    """
    Convert non-JSON string to a proper list of dicts.
    Example: "[{label=Foo, value=1}, {label=Bar, value=2}]"
    """
    print("[DEBUG] Raw data string before parsing:")
    print(data_str)

    # Convert it to JSON-like syntax
    data_str = data_str.replace('=', ':')
    data_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_ ]*)(\s*):', r'\1"\2"\3:', data_str)
    data_str = re.sub(r':\s*([^"{\[\]},]+)', lambda m: f': "{m.group(1).strip()}"' if not m.group(1).strip().isdigit() else f': {m.group(1).strip()}', data_str)

    print("[DEBUG] Data string after fix-up:")
    print(data_str)

    return json.loads(data_str)

def generate_pie_chart_and_upload(title, data, colors=None, bucket_name=None, folder="charts"):
    print("[INFO] Starting pie chart generation")
    data = parse_non_json_data_string(data)

    labels = [item['label'] for item in data]
    values = [item['value'] for item in data]

    filename = f"{uuid.uuid4()}.png"
    file_path = f"/tmp/{filename}"
    s3_key = f"{folder}/{filename}" if folder else filename

    # Generate pie chart
    plt.figure(figsize=(6, 6))
    plt.title(title)
    plt.pie(values, labels=labels, autopct='%1.1f%%', colors=colors)
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig(file_path)
    plt.close()
    print(f"[INFO] Chart saved at {file_path}")

    # Upload to S3
    s3 = boto3.client('s3')
    print(f"[INFO] Uploading to S3 bucket: {bucket_name}, key: {s3_key}")
    s3.upload_file(file_path, bucket_name, s3_key, ExtraArgs={"ContentType": "image/png"})

    presigned_url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket_name, "Key": s3_key},
        ExpiresIn=3600
    )

    os.remove(file_path)
    print("[INFO] Temporary file deleted")
    print("[INFO] Presigned URL generated")

    return presigned_url

def lambda_handler(event, context):
    agent = event.get('agent', '')
    actionGroup = event.get('actionGroup', '')
    function = event.get('function', '')
    parameter_list = event.get('parameters', [])

    print("[INFO] Lambda function invoked")
    print(f"Agent: {agent}")
    print(f"Action Group: {actionGroup}")
    print(f"Function: {function}")
    print(f"Raw Parameter List:\n{json.dumps(parameter_list, indent=2)}")

    parameters = {param["name"]: param["value"] for param in parameter_list if "name" in param and "value" in param}

    print("[DEBUG] Converted Parameters Dictionary:")
    print(json.dumps(parameters, indent=2))

    try:
        if function == "create_pie_chart":
            # Required parameters
            title = parameters.get("title")
            data = parameters.get("data")

            if not title or not data:
                raise ValueError("Missing 'title' or 'data' parameters for pie chart.")

            colors = parameters.get("colors")
            folder = parameters.get("folder", "charts")

            bucket_name = os.environ.get("CHART_IMAGE_BUCKET")
            if not bucket_name:
                raise RuntimeError("Missing required environment variable: CHART_IMAGE_BUCKET")

            presigned_url = generate_pie_chart_and_upload(
                title=title,
                data=data,
                colors=colors,
                bucket_name=bucket_name,
                folder=folder
            )

            response_body = {
                "TEXT": {
                    "body": f"I have saved the pie chart image in the following URL: {presigned_url}"
                }
            }

        else:
            raise ValueError(f"Unsupported function: {function}")

        function_response = {
            'actionGroup': actionGroup,
            'function': function,
            'functionResponse': {
                'responseBody': response_body
            }
        }

    except Exception as e:
        print(f"[ERROR] Exception occurred: {str(e)}")
        response_body = {
            "TEXT": {
                "body": f"An error occurred: {str(e)}"
            }
        }

        function_response = {
            'actionGroup': actionGroup,
            'function': function,
            'functionResponse': {
                'responseState': "FAILURE",
                'responseBody': response_body
            }
        }

    action_response = {
        'messageVersion': '1.0',
        'response': function_response,
        'sessionAttributes': event.get('sessionAttributes', {}),
        'promptSessionAttributes': event.get('promptSessionAttributes', {})
    }

    print("[INFO] Final Formatted Lambda Response:")
    print(json.dumps(action_response, indent=2))

    return action_response
