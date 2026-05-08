# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import boto3
import json
import logging
import os

from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful AI assistant designed to help physicians answer questions. You have access to a medical reasoning LLM that was specially trained to handle healthcare-specific questions. As an AI medical assistant, always consult the medical reasoning LLM (Model 14B) for any healthcare-specific questions before responding. When doing so, provide all relevant patient information available. Present the medical reasoning LLM's structured analysis clearly, emphasizing when information comes from this specialized system rather than your general knowledge. Include the reasoning pathways, alternative hypotheses, and any uncertainties identified by the medical reasoning LLM. Never provide medical advice based solely on your general knowledge. For non-medical questions, respond using your general capabilities while maintaining patient confidentiality at all times."""

# SageMaker client
session = boto3.session.Session()
sagemaker_runtime = session.client("sagemaker-runtime")


def _get_endpoint_name() -> str:
    """Get the SageMaker endpoint name from environment."""
    name = os.environ.get("ENDPOINT_NAME_1")
    if not name:
        raise RuntimeError("ENDPOINT_NAME_1 environment variable is not set")
    return name


def call_sagemaker_endpoint(text: str, endpoint_name: str) -> str:
    """Invoke the JSL Medical Reasoning SageMaker endpoint."""
    prompt = {
        "model": "/opt/ml/model",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a medical expert that reviews the problem, does reasoning, "
                    "and then gives a final answer.\nStrictly follow this exact format for "
                    "giving your output:\n\n<think>\nreasoning steps\n</think>\n\n"
                    "**Final Answer**: [Conclusive Answer]"
                ),
            },
            {"role": "user", "content": text},
        ],
        "max_tokens": 2048,
        "temperature": 0.8,
        "top_p": 0.95,
    }

    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps(prompt),
        ContentType="application/json",
    )

    response_body = json.loads(response["Body"].read().decode("utf-8"))
    return json.dumps(response_body, separators=(",", ":"))


@tool
def consult_with_medical_reasoning_model(medical_text: str) -> str:
    """Consult with a healthcare-specific LLM that provides advanced clinical decision support.

    Use this tool when you need to mimic a clinician's thought process rather than simple
    information lookup. This model excels at analyzing complex patient cases by evaluating
    multiple diagnostic hypotheses, acknowledging medical uncertainties, and following
    structured reasoning frameworks. Healthcare professionals should deploy it when
    transparency in decision-making is crucial, as it provides clear explanations for its
    conclusions while incorporating up-to-date medical knowledge. Unlike reference tools,
    this cognitive assistant supports nuanced diagnostic and treatment decisions by processing
    symptoms, test results, and patient histories to recommend evidence-based next steps
    aligned with clinical guidelines.

    Args:
        medical_text: Unstructured medical text describing the patient case or clinical question.
    """
    endpoint_name = _get_endpoint_name()
    result = call_sagemaker_endpoint(medical_text, endpoint_name)
    return f"Results from medical reasoning model:\n{result}"


def create_agent() -> Agent:
    """Create and return the JSL Medical Reasoning agent."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        streaming=True,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[consult_with_medical_reasoning_model],
    )
