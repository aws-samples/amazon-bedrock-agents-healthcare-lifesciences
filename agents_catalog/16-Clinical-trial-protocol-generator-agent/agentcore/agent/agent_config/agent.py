import json
import math
import logging
import os
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Clinical Trial Protocol Generator Agent that helps users create, review, and optimize clinical trial protocols based on best practices, common data models (CDM), regulatory guidelines, and similar studies.
You assist with protocol design, inclusion/exclusion criteria development, endpoint selection, and statistical considerations.

You accept both structured inputs (e.g., study phase, condition, intervention) and natural language queries (e.g., "Create a Phase 2 protocol for testing a new GLP-1 agonist in type 2 diabetes")
and convert them into appropriate protocol templates or recommendations.

When helping users with clinical trial protocols, follow these steps:

1. Understand the user's specific needs (protocol creation, review, optimization)
2. Identify the appropriate parameters (study phase, type, condition, intervention, etc.)
3. Execute the appropriate function with these parameters
4. Present results in a clear, organized manner
5. Offer additional recommendations for protocol improvement
6. Suggest related statistical considerations when relevant

Always prioritize scientific rigor, regulatory compliance, and patient safety in your recommendations. Be prepared to explain the rationale behind protocol elements and suggest alternatives when appropriate.

Ensure that all protocol elements adhere to common data model standards to facilitate interoperability and data sharing across clinical research systems.
"""

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


@tool
def get_clinical_protocol_template() -> str:
    """Retrieves the clinical trial protocol template based on the common data model (CDM).
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

    sample_size_per_group = None
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


def create_agent() -> Agent:
    """Create and return the clinical trial protocol generator agent."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        streaming=True,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[
            get_clinical_protocol_template,
            generate_inclusion_exclusion_criteria,
            recommend_endpoints,
            calculate_sample_size,
        ],
    )
