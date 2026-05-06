"""Clinical Prior Auth agent configuration and task logic."""

import json
import os
import pathlib

import pandas as pd
import requests
from PyPDF2 import PdfReader
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import use_llm

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
HAIKU_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent
RESOURCES_PATH = _DATA_DIR / "resources" / "hca_billing_guides_structured.json"
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/tmp/downloaded_files")


def _load_billing_data() -> dict:
    """Load billing guides metadata."""
    with open(RESOURCES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Tools ---


@tool
def get_guidance_document_list(speciality: str) -> str:
    """Get the list of PDF document URLs for a given specialty and the fee schedule document."""
    billing_data = _load_billing_data()
    if speciality in billing_data["categories"]:
        pdf_url_list = billing_data["categories"][speciality]["items"]
        return str(pdf_url_list) if pdf_url_list else "No documents found"
    available = list(billing_data["categories"].keys())
    return f"Specialty '{speciality}' not found. Available: {available}"


@tool
def download_appropriate_document(download_dict: dict) -> str:
    """Download billing guide PDFs and fee schedule for the given specialty."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    pdf_urls = download_dict["pdf_urls"]
    fee_schedule_url = download_dict.get("fee_schedule_url")
    downloaded_files = []

    for url in pdf_urls:
        try:
            response = requests.get(url, timeout=50)
            response.raise_for_status()
            filename = url.split("/")[-1] or "document.pdf"
            with open(os.path.join(DOWNLOAD_DIR, filename), "wb") as f:
                f.write(response.content)
            downloaded_files.append(filename)
        except Exception as e:
            return f"Error downloading: {e}"

    if fee_schedule_url:
        try:
            response = requests.get(fee_schedule_url, timeout=60)
            response.raise_for_status()
            filename = fee_schedule_url.split("/")[-1] or "fee_schedule.xls"
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(response.content)
            downloaded_files.append(filepath)
        except Exception as e:
            return f"Error downloading fee schedule: {e}"

    return f"Successfully downloaded: {', '.join(downloaded_files)}"


@tool
def parse_pdf(pdf_file: str) -> str:
    """Parse a downloaded PDF file and return its text content."""
    if not os.path.isabs(pdf_file):
        pdf_path = os.path.join(DOWNLOAD_DIR, pdf_file)
    else:
        pdf_path = pdf_file

    if not os.path.exists(pdf_path):
        return f"File not found: {pdf_path}"

    try:
        with open(pdf_path, "rb") as f:
            reader = PdfReader(f)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text.strip() if text.strip() else "No text content found in PDF"
    except Exception as e:
        return f"Error parsing PDF: {e}"


@tool
def parse_fee_schedule(fee_schedule_file: str) -> str:
    """Parse an Excel fee schedule file and return its content as text."""
    df = pd.read_excel(fee_schedule_file)
    return df.to_string()


@tool
def calculate_claim_approval(parsed_data: str, fee_schedule: str) -> str:
    """Calculate claim approval based on parsed billing data and fee schedule."""
    import boto3

    client = boto3.client("bedrock-runtime")
    prompt = (
        f"Based on the following parsed data:\n{parsed_data}\n"
        f"and fee schedule:\n{fee_schedule}\n"
        "Calculate the cost and determine if the claim is approved or not. "
        "If approved, return the amount paid to the provider. "
        "If not approved, return the reason for denial. "
        "Do not ask follow up questions."
    )
    try:
        response = client.converse(
            modelId=HAIKU_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 1024, "temperature": 0},
        )
        return response["output"]["message"]["content"][0]["text"]
    except Exception as e:
        return f"Error calculating claim approval: {e}"


# --- Agent Task ---

SYSTEM_PROMPT_TEMPLATE = """
From the following patient data, choose which specialty closely aligns with the patient data.
Please choose the one that is the latest document for the given input of the patient data.
1. Return them as a dictionary with the keys 'pdf_urls' and 'fee_schedule_url'.
2. Download the latest document
3. Parse the fee schedule document.
4. Only rely on the fee schedule document to calculate the claim approval cost
5. Only rely on the claim approval document to determine if the claim is approved or not.
Give a clear "SUCCESS" flag if the document is downloaded successfully.
Do not use model's internal knowledge to answer the questions.
Give me the total cost along with the line items in the fee schedule document.
Only use the fee schedule document and the costs mentioned in the columns to calculate the cost.
Also do include a breakdown or explanation of the cost for each line item.
Here is the list of specialties:
{}
"""


async def agent_task(user_message: str, session_id: str):
    """Create and run the prior auth agent."""
    billing_data = _load_billing_data()
    specialties = list(billing_data["categories"].keys())
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format("\n".join(specialties))

    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=system_prompt,
        tools=[
            use_llm,
            get_guidance_document_list,
            download_appropriate_document,
            parse_pdf,
            parse_fee_schedule,
            calculate_claim_approval,
        ],
    )

    stream = agent.stream_async(user_message)
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]
