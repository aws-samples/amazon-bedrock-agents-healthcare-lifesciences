"""Prior authorization tools for document retrieval, parsing, and claim calculation."""

import os
import json

import pandas as pd
import requests
from PyPDF2 import PdfReader
from strands import tool

import pathlib

_THIS_DIR = pathlib.Path(__file__).resolve().parent
RESOURCES_DIR = os.environ.get("RESOURCES_DIR", str(_THIS_DIR / "data"))
DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/tmp/downloaded_files")


def load_billing_data() -> dict:
    """Load billing guides metadata from resources."""
    path = os.path.join(RESOURCES_DIR, "hca_billing_guides_structured.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@tool
def get_guidance_document_list(speciality: str) -> str:
    """Get the list of PDF document URLs for a given specialty and the fee schedule document."""
    billing_data = load_billing_data()
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
    """Parse an Excel fee schedule file and return its content as text.

    Only return costs from this fee schedule document. Include any cost modifiers.
    """
    df = pd.read_excel(fee_schedule_file)
    return df.to_string()


@tool
def calculate_claim_approval(parsed_data: str, fee_schedule: str) -> str:
    """Calculate claim approval based on parsed data and fee schedule.

    Determines if the claim is approved and the amount to be paid, or the reason for denial.
    """
    import boto3

    client = boto3.client("bedrock-runtime")
    model_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    prompt = (
        f"Based on the following parsed data:\n{parsed_data}\n"
        f"and fee schedule:\n{fee_schedule}\n"
        "Calculate the cost and determine if the claim is approved or not. "
        "If approved, return the amount that will be paid to the provider. "
        "If not approved, return the reason for denial. "
        "Do not ask follow up questions."
    )
    try:
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 1024, "temperature": 0},
        )
        return response["output"]["message"]["content"][0]["text"]
    except Exception as e:
        return f"Error calculating claim approval: {e}"
