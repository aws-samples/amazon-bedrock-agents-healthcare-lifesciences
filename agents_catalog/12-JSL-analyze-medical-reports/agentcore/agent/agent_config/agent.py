import boto3
import json
import logging
import os
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a medical text analysis assistant powered by a large language model.
You help analyze clinical and medical documentation using specialized NLP tools, but you DO NOT provide clinical guidance, diagnosis, treatment recommendations, or interpret medical implications for individual patients.

Guidelines for Use:
1. Always clarify that you are performing text analysis, not providing medical advice.
2. When analyzing clinical text, suggest de-identification first if text might contain PHI.
3. Explain which tool you're using and why it's appropriate for the task.
4. Present analysis results clearly with appropriate context and limitations.
5. Never interpret clinical implications for individual patients.
6. Do not make diagnostic or treatment suggestions.
7. Refer users to qualified healthcare professionals for clinical questions.
"""

# SageMaker endpoint names from environment
ENDPOINT_NAME_1 = os.environ.get("ENDPOINT_NAME_1", "JSL-Extract-Social-Determinants-of-Health")
ENDPOINT_NAME_2 = os.environ.get("ENDPOINT_NAME_2", "ICD-10-CM-Sentence-Entity-Resolver")

_sagemaker_client = None


def _get_sagemaker_client():
    global _sagemaker_client
    if _sagemaker_client is None:
        _sagemaker_client = boto3.client("sagemaker-runtime")
    return _sagemaker_client


def _call_sagemaker_endpoint(text: str, endpoint_name: str) -> str:
    """Invoke a SageMaker endpoint with a text string."""
    logger.debug(f"call_sagemaker_endpoint: {text=}, {endpoint_name=}")
    client = _get_sagemaker_client()
    response = client.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps({"text": text}),
        ContentType="application/json",
    )
    response_body = json.loads(response["Body"].read().decode("utf-8"))
    return json.dumps(response_body, separators=(",", ":"))


@tool
def extract_social_determinants_of_health(medical_text: str) -> str:
    """Identify socio-environmental health determinants like access to care, diet, employment, and housing from health records.

    Tailored for professionals and researchers, this pipeline extracts key factors
    influencing health in social, economic, and environmental contexts.

    Args:
        medical_text: Unstructured medical text to analyze for social determinants of health.
    """
    if not medical_text or not medical_text.strip():
        return "Error: medical_text parameter is required."
    result = _call_sagemaker_endpoint(medical_text, ENDPOINT_NAME_1)
    return f"Social Determinants of Health extraction results:\n{result}"


@tool
def extract_icd_10_cm_sentence_entities(medical_text: str) -> str:
    """Extract clinical entities and map them to ICD-10-CM codes using sbiobert_base_cased_mli sentence embeddings.

    Predicts ICD-10-CM codes up to 3 characters (the first three characters represent
    the general type of injury or disease according to ICD-10-CM code structure).

    Args:
        medical_text: Unstructured medical text to analyze for ICD-10-CM entity extraction.
    """
    if not medical_text or not medical_text.strip():
        return "Error: medical_text parameter is required."
    result = _call_sagemaker_endpoint(medical_text, ENDPOINT_NAME_2)
    return f"ICD-10-CM entity extraction results:\n{result}"


def create_agent() -> Agent:
    """Create and return the JSL medical report analysis agent."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        streaming=True,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[extract_social_determinants_of_health, extract_icd_10_cm_sentence_entities],
    )
