"""SEC 10-K Search Agent with @tool functions wrapping EDGAR API functionality."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import boto3
import numpy as np
from rapidfuzz import fuzz, process, utils
from sec_edgar_api import EdgarClient
from sklearn.metrics.pairwise import cosine_similarity
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
DEFAULT_SCORE_CUTOFF = 80
USER_AGENT = os.environ.get("USER_AGENT", "AWS HCLS AGENTS").strip()

SYSTEM_PROMPT = """You are an expert financial analyst specializing in public company analysis using SEC 10-K data. Help users analyze companies by retrieving and interpreting financial data through the SEC EDGAR API tools.

You have access to the following tools:

  - find_relevant_tags: Find the most relevant SEC EDGAR database tags for a given query. May be used to identify the input values for the get_company_concept function.
  - get_company_concept: Retrieves us-gaap disclosures from the EDGAR API for a specified company and concept (tag), returning an array of facts organized by units of measure (such as profits in different currencies).

Analysis Process

  1. Begin by asking which company the user wants to analyze, if not provided.
  2. Use find_relevant_tags to determine which specific SEC EDGAR database tags are relevant based on the user's goals.
  3. Use get_company_concept to retrieve targeted financial data.
  4. Analyze trends, calculate financial ratios, and provide insights.
  5. Present your analysis in a clear, structured format with relevant visualizations or tables.

Response Guidelines

  - Provide concise, actionable insights based on the data
  - Explain financial concepts in accessible language
  - Include relevant metrics like revenue growth, profitability ratios, and balance sheet analysis
  - Highlight notable trends or concerns
  - Make appropriate comparisons to industry standards when possible
  - Acknowledge data limitations and gaps where they exist
"""


def _get_embedding(bedrock_runtime, text: str, model_id: str = "amazon.titan-embed-text-v2:0") -> np.ndarray:
    """Get embedding for a single text using Amazon Bedrock."""
    response = bedrock_runtime.invoke_model(
        modelId=model_id, body=json.dumps({"inputText": text})
    )
    response_body = json.loads(response["body"].read())
    return np.array(response_body["embedding"])


def _get_cik(query: str, data_file: Path, score_cutoff: int = DEFAULT_SCORE_CUTOFF) -> Optional[Dict]:
    """Look up the SEC CIK for a company name using fuzzy matching."""
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            company_tickers = json.load(f)
    except IOError as e:
        logger.error(f"Error opening file {data_file}: {e}")
        return None

    if not company_tickers:
        return None

    choices = [company.get("title", "") for company in company_tickers.values()]
    match = process.extractOne(
        query, choices, scorer=fuzz.WRatio, processor=utils.default_process, score_cutoff=score_cutoff
    )
    return list(company_tickers.values())[match[2]] if match else None


@tool(
    name="find_relevant_tags",
    description="Find the most relevant SEC tags for a given query. May be used to identify the input values to the get_company_concept function.",
)
def find_relevant_tags(query: str) -> str:
    """Find relevant SEC EDGAR tags for a query using semantic search.

    Args:
        query: Topic or question to search against all available SEC tags in the us-gaap taxonomy.

    Returns:
        JSON string with matching tags and descriptions.
    """
    descriptions_path = os.environ.get("DESCRIPTIONS_PATH", "/tmp/descriptions.csv")
    embeddings_path = os.environ.get("EMBEDDINGS_PATH", "/tmp/embeddings.npy")

    # Download files from S3 if not present
    if not os.path.exists(descriptions_path) or not os.path.exists(embeddings_path):
        s3 = boto3.client("s3")
        s3.download_file("5d1a4b76751b4c8a994ce96bafd91ec9", "us-gaap/embeddings.npy", embeddings_path)
        s3.download_file("5d1a4b76751b4c8a994ce96bafd91ec9", "us-gaap/descriptions.csv", descriptions_path)

    # Parse descriptions
    pattern = r"^([^,]+),([^,]+),(.+)$"
    available_facts = []
    with open(descriptions_path, "r") as f:
        for line in f:
            match = re.match(pattern, line.strip())
            if match:
                taxonomy, tag, description = match.groups()
                available_facts.append({"taxonomy": taxonomy, "tag": tag, "description": description})

    # Compute semantic search
    bedrock_runtime = boto3.client("bedrock-runtime")
    embeddings = np.load(embeddings_path)
    descriptions = [i["description"] for i in available_facts if i["description"] is not None]

    query_embedding = _get_embedding(bedrock_runtime, query)
    similarities = cosine_similarity(query_embedding.reshape(1, -1), embeddings)[0]
    top_indices = np.argsort(similarities)[::-1][:5]

    results = [{"tag": available_facts[i]["tag"], "description": available_facts[i]["description"]} for i in top_indices]
    return json.dumps(results, separators=(",", ":"))


@tool(
    name="get_company_concept",
    description="Get all the us-gaap disclosures for a single company and concept (tag), with a separate array of facts for each unit of measure.",
)
def get_company_concept(company_name: str, tag: str) -> str:
    """Retrieve us-gaap disclosures from EDGAR for a company and concept tag.

    Args:
        company_name: Company name, e.g. Amazon or Pfizer.
        tag: SEC EDGAR tag identifier, e.g. 'EntityCommonStockSharesOutstanding'.

    Returns:
        JSON string with entity name, label, unit, and 10-K filing data.
    """
    cik_file = os.environ.get("CIK_FILE", "cik-ref.json")
    cik_info = _get_cik(company_name, cik_file)
    if cik_info is None:
        return json.dumps({"error": f"Could not find CIK for company: {company_name}"})

    cik = cik_info.get("cik_str", "")
    edgar = EdgarClient(user_agent=USER_AGENT)

    try:
        concept = edgar.get_company_concept(cik, "us-gaap", tag)
    except Exception as e:
        logger.error(f"Error retrieving company concept: {e}")
        return json.dumps({"error": f"Error retrieving concept: {e}"})

    unit, data = next(iter(concept.get("units", {}).items()), ("", []))
    short_data = [
        {"date": i.get("end", ""), "value": i.get("val", 0)}
        for i in data
        if i.get("form", "") == "10-K" and "frame" in i
    ]
    formatted = {
        "entity_name": concept.get("entityName", ""),
        "label": concept.get("label", ""),
        "unit": unit,
        "data": short_data,
    }
    return json.dumps(formatted, separators=(",", ":"))


def create_agent() -> Agent:
    """Create and return the SEC 10-K Search Agent."""
    model = BedrockModel(model_id=MODEL_ID)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[find_relevant_tags, get_company_concept],
    )
