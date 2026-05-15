"""Clinical Trial Protocol Assistant - unified agent combining study search and protocol generation."""

import json
import logging
import math
import os
import re
import uuid

import boto3
import requests
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are an intelligent Clinical Protocol Builder Assistant powered by AI. Your purpose is to help trial sponsors, clinical operations teams, and medical writers create high-quality clinical trial protocol documents efficiently, using evidence from previous studies and a regulatory-aligned structure.

Your Capabilities:

1. Study Search: Find and summarize past clinical trials based on therapeutic area, phase, interventions, endpoints, and population criteria from ClinicalTrials.gov and FDA drug databases.

2. Protocol Writing: Generate detailed protocol documents using medical writing templates and contextual inputs. Understand regulatory requirements (e.g., ICH-GCP) and standard protocol structure.

3. Smart Feature: When generating protocols, automatically search for similar past trials to extract relevant study elements—such as objectives, eligibility criteria, design, and endpoints—so the user doesn't need to provide everything from scratch.

Working Process:
1. Understand the user's high-level goal (e.g., "Create a Phase 2 trial protocol for a new Alzheimer's drug")
2. Offer to automatically search for similar past trials to extract protocol elements
3. Present relevant findings to the user for selection or review
4. Use extracted data and best practices to fill protocol sections
5. Generate a full draft document with prefilled content and editable placeholders
6. Respond to feedback or refinement requests

Guidelines:
- Prioritize reuse of validated designs from similar studies where appropriate
- Clearly indicate when a section is based on a past trial and cite the source
- Avoid asking the user for details if they can be inferred or sourced from public trial data
- Ensure protocol sections are comprehensive, compliant, and formatted professionally
- Maintain traceability for all reused or referenced content
- Provide fallback to manual creation if no relevant studies are found
- Maintain a professional, scientific tone consistent with industry standards
"""

# --- ClinicalTrials.gov search constants ---

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

# --- Protocol generation constants ---

CDM_PATH = os.path.join(os.path.dirname(__file__), "cdm.json")

CRITERIA_TEMPLATES = {
    "type 2 diabetes": {
        "inclusion": [
            "Diagnosis of type 2 diabetes for at least 6 months",
            "HbA1c between 7.0% and 10.0%",
            "Age 18-75 years",
            "Body mass index (BMI) between 25 and 40 kg/m²",
            "Stable dose of current antidiabetic medication for at least 3 months",
        ],
        "exclusion": [
            "Type 1 diabetes",
            "History of diabetic ketoacidosis",
            "Severe hypoglycemia requiring hospitalization within the past 6 months",
            "Estimated glomerular filtration rate (eGFR) < 45 mL/min/1.73m²",
            "History of pancreatitis or pancreatic cancer",
            "Current use of insulin or GLP-1 receptor agonists",
            "Pregnant or breastfeeding women",
        ],
    },
    "breast cancer": {
        "inclusion": [
            "Histologically confirmed breast cancer",
            "ECOG performance status 0-1",
            "Adequate bone marrow function",
            "Adequate liver and renal function",
            "Measurable disease according to RECIST v1.1 criteria",
        ],
        "exclusion": [
            "Prior chemotherapy within 4 weeks of study entry",
            "Known brain metastases",
            "History of other malignancy within the past 5 years",
            "Significant cardiovascular disease",
            "Pregnant or breastfeeding women",
            "Known hypersensitivity to study drug or its excipients",
        ],
    },
    "depression": {
        "inclusion": [
            "DSM-5 diagnosis of major depressive disorder",
            "Hamilton Depression Rating Scale (HAM-D) score ≥ 18",
            "Age 18-65 years",
            "Inadequate response to at least one antidepressant treatment in the current episode",
            "Stable dose of current antidepressant for at least 4 weeks",
        ],
        "exclusion": [
            "Bipolar disorder or psychotic features",
            "Substance use disorder within the past 6 months",
            "Significant risk of suicide",
            "History of seizure disorder",
            "Electroconvulsive therapy within the past 3 months",
            "Pregnant or breastfeeding women",
        ],
    },
}

ENDPOINT_RECOMMENDATIONS = {
    "type 2 diabetes": {
        "Phase 1": {
            "primary": ["Safety and tolerability", "Pharmacokinetic parameters"],
            "secondary": ["Changes in fasting plasma glucose", "Changes in postprandial glucose"],
        },
        "Phase 2": {
            "primary": ["Change in HbA1c from baseline to week 12"],
            "secondary": [
                "Proportion of patients achieving HbA1c < 7.0%",
                "Change in fasting plasma glucose",
                "Change in body weight",
                "Incidence of hypoglycemia",
            ],
        },
        "Phase 3": {
            "primary": ["Change in HbA1c from baseline to week 26"],
            "secondary": [
                "Proportion of patients achieving HbA1c < 7.0%",
                "Change in fasting plasma glucose",
                "Change in body weight",
                "Time to rescue medication",
                "Patient-reported outcomes",
                "Cardiovascular safety endpoints",
            ],
        },
    },
    "heart failure": {
        "Phase 1": {
            "primary": ["Safety and tolerability", "Pharmacokinetic parameters"],
            "secondary": ["Changes in NT-proBNP levels", "Hemodynamic parameters"],
        },
        "Phase 2": {
            "primary": ["Change in NT-proBNP levels from baseline to week 12"],
            "secondary": [
                "Change in 6-minute walk distance",
                "Change in NYHA functional class",
                "Change in quality of life scores",
                "Incidence of worsening heart failure",
            ],
        },
        "Phase 3": {
            "primary": ["Composite of cardiovascular death or heart failure hospitalization"],
            "secondary": [
                "All-cause mortality",
                "Total heart failure hospitalizations",
                "Change in quality of life scores",
                "Change in 6-minute walk distance",
                "Change in NYHA functional class",
            ],
        },
    },
    "depression": {
        "Phase 1": {
            "primary": ["Safety and tolerability", "Pharmacokinetic parameters"],
            "secondary": ["Changes in mood assessment scales"],
        },
        "Phase 2": {
            "primary": ["Change in MADRS from baseline to week 6"],
            "secondary": [
                "Response rate (≥50% reduction in MADRS)",
                "Remission rate (MADRS ≤10)",
                "Change in Hamilton Anxiety Rating Scale",
                "Change in Clinical Global Impression scale",
            ],
        },
        "Phase 3": {
            "primary": ["Change in MADRS from baseline to week 8"],
            "secondary": [
                "Response and remission rates",
                "Change in Hamilton Anxiety Rating Scale",
                "Change in Clinical Global Impression scale",
                "Change in quality of life measures",
                "Relapse rates during follow-up phase",
            ],
        },
    },
}


# ============================================================
# Study Search Tools (from Clinical-Study-Search-Agent)
# ============================================================


@tool(name="search_trials")
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
    """Search ClinicalTrials.gov for studies matching criteria such as condition, intervention, outcome, sponsor, location, or patient characteristics.

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
        "condition": condition, "intervention": intervention, "outcome": outcome,
        "sponsor": sponsor, "patient": patient, "location": location,
        "study_id": study_id, "title": title,
    }
    for key, value in query_fields.items():
        if key in QUERY_MAP and value:
            params[QUERY_MAP[key]] = value.strip()

    res = requests.get(base_url, params=params, timeout=30)
    if res.status_code != 200:
        return json.dumps({"error": f"API call failed: {res.status_code} - {res.text}"})

    studies = res.json().get("studies", [])
    return json.dumps(studies, separators=(",", ":"))


@tool(name="get_trial_details")
def get_trial_details(nctId: str) -> str:
    """Retrieve comprehensive information about a specific clinical trial using its NCT ID.

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


@tool(name="get_approved_drugs")
def get_approved_drugs(condition: str, route: str = None) -> str:
    """Retrieve information about FDA-approved drugs for a specific condition, optionally filtered by route of administration.

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

    return json.dumps({
        "total_drugs": len(unique_drugs),
        "routes": route_counts,
        "drug_names": list(unique_drugs)[:10],
    }, separators=(",", ":"))


@tool(name="create_pie_chart")
def create_pie_chart(title: str, data: str) -> str:
    """Create a pie chart from clinical trial data and upload it to S3. Returns a presigned URL.

    Args:
        title: Title of the pie chart.
        data: JSON list of data points, each with 'label' and 'value' keys.

    Returns:
        A presigned URL to the generated chart image.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    bucket_name = os.environ.get("CHART_IMAGE_BUCKET")
    if not bucket_name:
        return json.dumps({"error": "Missing CHART_IMAGE_BUCKET environment variable"})

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


# ============================================================
# Protocol Generation Tools (from Clinical-Trial-Protocol-Generator-Agent)
# ============================================================


@tool
def get_clinical_protocol_template() -> str:
    """Retrieve the clinical trial protocol template based on the common data model (CDM).
    Returns the full CDM structure that defines all sections of a clinical trial protocol.
    """
    try:
        with open(CDM_PATH, "r") as f:
            cdm = json.load(f)
        return f"Clinical Document Model (CDM): {json.dumps(cdm, indent=2)}"
    except Exception as e:
        logger.error(f"Failed to load CDM: {e}")
        return f"Error loading CDM: {e}"


@tool
def generate_inclusion_exclusion_criteria(
    condition: str, intervention: str, population: str, study_phase: str = ""
) -> str:
    """Generate inclusion and exclusion criteria for a clinical trial based on condition, intervention, and population.

    Args:
        condition: The medical condition being studied (e.g., 'type 2 diabetes', 'breast cancer')
        intervention: The intervention being tested (e.g., 'GLP-1 agonist', 'monoclonal antibody')
        population: The target population (e.g., 'adults', 'elderly', 'pediatric')
        study_phase: The study phase (e.g., 'Phase 1', 'Phase 2', 'Phase 3')
    """
    condition_lower = condition.lower()
    best_match = None
    for template_condition in CRITERIA_TEMPLATES:
        if template_condition in condition_lower:
            best_match = template_condition
            break

    if not best_match:
        if "diabetes" in condition_lower:
            best_match = "type 2 diabetes"
        elif "cancer" in condition_lower:
            best_match = "breast cancer"
        elif "depress" in condition_lower:
            best_match = "depression"

    if not best_match:
        return json.dumps({
            "inclusion": [
                f"Diagnosis of {condition}",
                "Age 18 years or older",
                "Able to provide informed consent",
                "Adequate organ function",
            ],
            "exclusion": [
                "Participation in another clinical trial within 30 days",
                "Known hypersensitivity to study drug or its components",
                "Pregnant or breastfeeding women",
                "Any condition that would compromise patient safety or study integrity",
            ],
            "note": "These are generic criteria. Consider consulting with clinical experts for condition-specific criteria.",
        }, indent=2)

    custom_criteria = {
        "inclusion": CRITERIA_TEMPLATES[best_match]["inclusion"].copy(),
        "exclusion": CRITERIA_TEMPLATES[best_match]["exclusion"].copy(),
    }

    intervention_lower = intervention.lower()
    if "monoclonal antibody" in intervention_lower or "biologic" in intervention_lower:
        custom_criteria["exclusion"].append("History of severe allergic reactions")
        custom_criteria["exclusion"].append("Active infection or recent live vaccination")
    if "gene therapy" in intervention_lower:
        custom_criteria["exclusion"].append("Prior gene therapy treatment")
        custom_criteria["exclusion"].append("Presence of neutralizing antibodies to the viral vector")

    population_lower = population.lower()
    if "elderly" in population_lower or "older" in population_lower:
        custom_criteria["inclusion"] = [c for c in custom_criteria["inclusion"] if "18-" not in c]
        custom_criteria["inclusion"].append("Age 65 years or older")
    if "pediatric" in population_lower or "children" in population_lower:
        custom_criteria["inclusion"] = [c for c in custom_criteria["inclusion"] if "18" not in c]
        custom_criteria["inclusion"].append("Age 2-17 years")
        custom_criteria["inclusion"].append("Parental/guardian informed consent and child assent (when appropriate)")

    if study_phase:
        phase = study_phase.lower()
        if "1" in phase:
            custom_criteria["inclusion"].append("Healthy volunteers or patients with mild disease")
            custom_criteria["exclusion"].append("Multiple comorbidities")
        elif "3" in phase:
            custom_criteria["inclusion"].append("Representative of the broader target population")

    return json.dumps(custom_criteria, indent=2)


@tool
def recommend_endpoints(condition: str, intervention: str, study_phase: str) -> str:
    """Recommend appropriate primary and secondary endpoints for a clinical trial.

    Args:
        condition: The medical condition being studied (e.g., 'type 2 diabetes', 'heart failure')
        intervention: The intervention being tested
        study_phase: The study phase (e.g., 'Phase 1', 'Phase 2', 'Phase 3')
    """
    condition_lower = condition.lower()
    best_match = None
    for template_condition in ENDPOINT_RECOMMENDATIONS:
        if template_condition in condition_lower:
            best_match = template_condition
            break

    if not best_match:
        if "diabetes" in condition_lower:
            best_match = "type 2 diabetes"
        elif "heart" in condition_lower or "cardiac" in condition_lower:
            best_match = "heart failure"
        elif "depress" in condition_lower or "mood" in condition_lower:
            best_match = "depression"

    if not best_match:
        return json.dumps({
            "primary": ["Safety and tolerability" if "1" in study_phase else "Efficacy measure specific to condition"],
            "secondary": [
                "Pharmacokinetic parameters" if "1" in study_phase else "Additional efficacy measures",
                "Patient-reported outcomes",
                "Quality of life assessments",
            ],
            "exploratory": ["Biomarker assessments", "Long-term outcomes"],
            "note": "These are generic endpoints. Consider consulting with clinical experts.",
        }, indent=2)

    phase = "Phase 2"
    if "1" in study_phase:
        phase = "Phase 1"
    elif "2" in study_phase:
        phase = "Phase 2"
    elif "3" in study_phase:
        phase = "Phase 3"

    endpoints = dict(ENDPOINT_RECOMMENDATIONS[best_match].get(phase, ENDPOINT_RECOMMENDATIONS[best_match]["Phase 2"]))

    exploratory = []
    intervention_lower = intervention.lower()
    if "monoclonal antibody" in intervention_lower or "biologic" in intervention_lower:
        exploratory.append("Immunogenicity assessments")
        exploratory.append("Biomarker analysis for target engagement")
    if "gene therapy" in intervention_lower:
        exploratory.append("Vector shedding analysis")
        exploratory.append("Long-term expression of therapeutic gene")
    endpoints["exploratory"] = exploratory

    return json.dumps(endpoints, indent=2)


@tool
def calculate_sample_size(
    study_design: str, power: str, effect_size: str, endpoint_type: str
) -> str:
    """Calculate the required sample size for a clinical trial based on statistical parameters.

    Args:
        study_design: The study design type (e.g., 'superiority', 'non-inferiority', 'equivalence')
        power: Statistical power as percentage or decimal (e.g., '80%', '0.8', '90%')
        effect_size: Expected effect size (e.g., '0.3', '15%', '0.5 point')
        endpoint_type: Type of primary endpoint ('binary', 'continuous', or 'time-to-event')
    """
    power_value = float(power.strip("%")) / 100 if "%" in power else float(power)
    alpha = 0.05
    z_alpha = 1.96
    z_beta = 0.84 if power_value <= 0.8 else 1.28

    if "%" in effect_size:
        effect_size_value = float(effect_size.strip("%")) / 100
    elif "point" in effect_size.lower():
        effect_size_value = float(effect_size.split()[0])
    else:
        try:
            effect_size_value = float(effect_size)
        except ValueError:
            effect_size_value = 0.3

    if endpoint_type.lower() == "binary":
        control_prop = 0.5
        treatment_prop = control_prop + effect_size_value
        pooled_prop = (control_prop + treatment_prop) / 2
        variance = 2 * pooled_prop * (1 - pooled_prop)
        sample_size_per_group = math.ceil(
            (z_alpha + z_beta) ** 2 * variance / (control_prop - treatment_prop) ** 2
        )
    elif endpoint_type.lower() == "continuous":
        sample_size_per_group = math.ceil(2 * ((z_alpha + z_beta) / effect_size_value) ** 2)
    elif endpoint_type.lower() == "time-to-event":
        hazard_ratio = 1 - effect_size_value if effect_size_value < 1 else effect_size_value
        sample_size_per_group = math.ceil(4 * ((z_alpha + z_beta) / math.log(hazard_ratio)) ** 2)
    else:
        sample_size_per_group = math.ceil(2 * ((z_alpha + z_beta) / effect_size_value) ** 2)

    if study_design.lower() in ("non-inferiority", "equivalence"):
        sample_size_per_group = math.ceil(sample_size_per_group * 1.25)

    total = sample_size_per_group * 2
    recommended = math.ceil(total * 1.15)

    return json.dumps({
        "sample_size_per_group": sample_size_per_group,
        "total_sample_size": total,
        "recommended_sample_size": recommended,
        "assumptions": {
            "alpha": alpha,
            "power": power_value,
            "effect_size": effect_size_value,
            "endpoint_type": endpoint_type,
            "dropout_rate": "15%",
        },
        "notes": "This is an approximate calculation. Consider consulting with a statistician for a more precise sample size calculation.",
    }, indent=2)


# ============================================================
# Helpers
# ============================================================


def _parse_data_string(data_str: str) -> list:
    """Parse a data string that may be JSON or a non-standard format."""
    try:
        return json.loads(data_str)
    except (json.JSONDecodeError, TypeError):
        pass
    data_str = data_str.replace("=", ":")
    data_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_ ]*)(\s*):', r'\1"\2"\3:', data_str)
    data_str = re.sub(
        r':\s*([^"{\[\]},]+)',
        lambda m: f': "{m.group(1).strip()}"' if not m.group(1).strip().replace(".", "").isdigit() else f": {m.group(1).strip()}",
        data_str,
    )
    parsed = json.loads(data_str)
    for item in parsed:
        if isinstance(item.get("value"), str):
            item["value"] = float(item["value"])
    return parsed


# ============================================================
# Agent factory
# ============================================================

ALL_TOOLS = [
    search_trials,
    get_trial_details,
    get_approved_drugs,
    create_pie_chart,
    get_clinical_protocol_template,
    generate_inclusion_exclusion_criteria,
    recommend_endpoints,
    calculate_sample_size,
]


def create_agent() -> Agent:
    """Create and return the unified Clinical Trial Protocol Assistant agent."""
    model = BedrockModel(
        model_id=MODEL_ID,
        streaming=True,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )
