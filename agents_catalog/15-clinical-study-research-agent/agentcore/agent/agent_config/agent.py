"""Clinical Study Research Agent with @tool functions."""

import json
import logging
import os
import re
import uuid

import boto3
import requests
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are a Clinical Study Search Agent that helps users explore, filter, and analyze clinical trial data from public registries like ClinicalTrials.gov.
You assist with condition-specific study identification, intervention tracking, sponsor profiling, and outcome analysis using structured search criteria.

You accept both structured inputs (e.g., condition, intervention, outcome) and natural language queries (e.g., "Find double-arm diabetes trials in males under 60")
and convert them into valid API queries using the ClinicalTrials.gov v2 syntax.

When analyzing clinical trial data, follow these steps:

1. Understand the user's specific research question or information need
2. Identify the appropriate search parameters (condition, intervention, outcome, etc.)
3. Execute the appropriate search function with these parameters
4. Present results in a clear, organized manner
5. Offer to create visualizations when appropriate
6. Suggest related drug information when relevant

Always prioritize accuracy and relevance in your responses, and be prepared to refine searches based on user feedback.
"""

# ClinicalTrials.gov API v2 query key mapping
QUERY_MAP = {
    "condition": "query.cond",
    "location": "query.locn",
    "title": "query.titles",
    "intervention": "query.intr",
    "outcome": "query.outc",
    "sponsor": "query.spons",
    "lead_sponsor": "query.lead",
    "study_id": "query.id",
    "patient": "query.patient",
}

OPEN_FDA_URL = "https://api.fda.gov/drug/drugsfda.json"


@tool(
    name="search_trials",
    description="Finds clinical studies matching criteria such as condition, intervention, comparison, outcome, sponsor, location, patient characteristics, study ID, or title.",
)
def search_trials(
    condition: str,
    intervention: str,
    outcome: str,
    comparison: str,
    sponsor: str = None,
    patient: str = None,
    location: str = None,
    study_id: str = None,
    title: str = None,
) -> str:
    """Search ClinicalTrials.gov for studies matching the given criteria.

    Args:
        condition: Disease or medical condition being studied (e.g., "diabetes", "asthma").
        intervention: Treatment/drug/device used in the study (e.g., "metformin", "placebo").
        outcome: Clinical outcome or endpoint being measured (e.g., "blood glucose", "HbA1c reduction").
        comparison: Alternate treatment or control used as comparator (e.g., "placebo", "standard of care").
        sponsor: Organization funding or collaborating on the trial.
        patient: Description of eligible patient characteristics or population.
        location: Geographic location of the study.
        study_id: Clinical trial identifier (e.g., NCT number).
        title: Words or phrases appearing in the trial title.

    Returns:
        JSON string with search results from ClinicalTrials.gov.
    """
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    fields = [
        "NCTId", "BriefTitle", "OverallStatus", "InterventionName",
        "Phase", "StartDate", "CompletionDate", "LeadSponsorName",
    ]

    params = {"format": "json", "pageSize": 10, "fields": ",".join(fields)}

    query_fields = {
        "condition": condition,
        "intervention": intervention,
        "outcome": outcome,
        "sponsor": sponsor,
        "patient": patient,
        "location": location,
        "study_id": study_id,
        "title": title,
    }

    for key, value in query_fields.items():
        if key in QUERY_MAP and value:
            params[QUERY_MAP[key]] = value.strip()

    logger.info(f"Searching ClinicalTrials.gov with params: {params}")
    res = requests.get(base_url, params=params, timeout=30)

    if res.status_code != 200:
        return json.dumps({"error": f"API call failed: {res.status_code} - {res.text}"})

    studies = res.json().get("studies", [])
    logger.info(f"Retrieved {len(studies)} studies")
    return json.dumps(studies, separators=(",", ":"))


@tool(
    name="get_trial_details",
    description="Retrieves comprehensive information about a specific clinical trial using its NCT ID.",
)
def get_trial_details(nctId: str) -> str:
    """Get detailed information about a specific clinical trial.

    Args:
        nctId: The NCT identifier of the clinical study (e.g., "NCT056789").

    Returns:
        JSON string with detailed study information.
    """
    url = f"https://clinicaltrials.gov/api/v2/studies/{nctId}"
    params = {
        "format": "json",
        "markupFormat": "markdown",
        "fields": ",".join([
            "NCTId", "BriefTitle", "BriefSummary", "Phase",
            "StartDate", "CompletionDate", "OverallStatus",
            "ConditionsModule", "EligibilityModule",
            "ArmsInterventionsModule", "SponsorCollaboratorsModule",
            "OutcomesModule",
        ]),
    }

    res = requests.get(url, params=params, timeout=30)
    if res.status_code != 200:
        return json.dumps({"error": f"Study details API failed: {res.status_code}"})

    return json.dumps(res.json(), separators=(",", ":"))


@tool(
    name="get_approved_drugs",
    description="Retrieves information about FDA-approved drugs for a specific condition, optionally filtered by route of administration.",
)
def get_approved_drugs(condition: str, route: str = None) -> str:
    """Query the OpenFDA API for approved drugs.

    Args:
        condition: The disease or indication to filter approved drugs by (e.g., "diabetes").
        route: Optional route of administration (e.g., "nasal", "oral", "intravenous").

    Returns:
        JSON string with approved drug information.
    """
    search_terms = []
    if condition:
        val = f'"{condition}"' if " " in condition else condition
        search_terms.append(f"indications_and_usage:{val}")
    if route:
        val = f'"{route}"' if " " in route else route
        search_terms.append(f"route:{val}")

    params = {"search": "+AND+".join(search_terms), "limit": 100}
    logger.info(f"Querying OpenFDA: {params}")

    res = requests.get(OPEN_FDA_URL, params=params, timeout=30)
    if res.status_code != 200:
        return json.dumps({"error": f"OpenFDA API failed: {res.status_code} - {res.text}"})

    results = res.json().get("results", [])

    unique_drugs = set()
    route_counts = {}
    for item in results:
        for product in item.get("products", []):
            brand = product.get("brand_name")
            r = product.get("route")
            if brand:
                unique_drugs.add(brand)
            if r:
                route_counts[r] = route_counts.get(r, 0) + 1

    summary = {
        "total_drugs": len(unique_drugs),
        "routes": route_counts,
        "drug_names": list(unique_drugs)[:10],
    }
    return json.dumps(summary, separators=(",", ":"))


@tool(
    name="create_pie_chart",
    description="Creates a pie chart from clinical trial data and uploads it to S3. Returns a presigned URL to view the chart.",
)
def create_pie_chart(title: str, data: str) -> str:
    """Generate a pie chart and upload to S3.

    Args:
        title: Title of the pie chart.
        data: JSON-like list of data points, each with 'label' and 'value' keys.

    Returns:
        A presigned URL to the generated chart image.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    bucket_name = os.environ.get("CHART_IMAGE_BUCKET")
    if not bucket_name:
        return json.dumps({"error": "Missing CHART_IMAGE_BUCKET environment variable"})

    # Parse data string (handles non-standard JSON-like formats)
    parsed = _parse_data_string(data)
    labels = [item["label"] for item in parsed]
    values = [item["value"] for item in parsed]

    filename = f"{uuid.uuid4()}.png"
    file_path = f"/tmp/{filename}"
    s3_key = f"charts/{filename}"

    plt.figure(figsize=(6, 6))
    plt.title(title)
    plt.pie(values, labels=labels, autopct="%1.1f%%")
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(file_path)
    plt.close()

    s3 = boto3.client("s3")
    s3.upload_file(file_path, bucket_name, s3_key, ExtraArgs={"ContentType": "image/png"})
    os.remove(file_path)

    presigned_url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket_name, "Key": s3_key},
        ExpiresIn=3600,
    )
    return json.dumps({"url": presigned_url})


def _parse_data_string(data_str: str) -> list:
    """Parse a data string that may be JSON or a non-standard format."""
    try:
        return json.loads(data_str)
    except (json.JSONDecodeError, TypeError):
        pass

    # Handle non-JSON format like [{label=Foo, value=1}]
    data_str = data_str.replace("=", ":")
    data_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_ ]*)(\s*):', r'\1"\2"\3:', data_str)
    data_str = re.sub(
        r':\s*([^"{\[\]},]+)',
        lambda m: f': "{m.group(1).strip()}"' if not m.group(1).strip().replace(".", "").isdigit() else f": {m.group(1).strip()}",
        data_str,
    )
    parsed = json.loads(data_str)
    # Ensure values are numeric
    for item in parsed:
        if isinstance(item.get("value"), str):
            item["value"] = float(item["value"])
    return parsed


def create_agent() -> Agent:
    """Create and return the Clinical Study Research Agent."""
    model = BedrockModel(model_id=MODEL_ID)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_trials, get_trial_details, get_approved_drugs, create_pie_chart],
    )
