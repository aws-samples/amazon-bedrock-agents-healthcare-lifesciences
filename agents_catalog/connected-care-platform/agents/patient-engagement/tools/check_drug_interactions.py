"""Tool: Check for known drug interactions in a patient's medication list."""

import os
import boto3
from strands import tool
from boto3.dynamodb.conditions import Key
from .sanitize import sanitize

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
medications_table = dynamodb.Table(os.environ.get("DYNAMODB_MEDICATIONS_TABLE", "connected-care-medications"))

# Hardcoded common interaction pairs for demonstration
KNOWN_INTERACTIONS = [
    {"drug_a": "Lisinopril", "drug_b": "Metformin", "severity": "MODERATE",
     "description": "ACE inhibitors may enhance the hypoglycemic effect of Metformin. Monitor blood glucose closely."},
    {"drug_a": "Lisinopril", "drug_b": "Furosemide", "severity": "MODERATE",
     "description": "Combined use may cause excessive blood pressure reduction. Monitor BP and electrolytes."},
    {"drug_a": "Aspirin", "drug_b": "Ibuprofen", "severity": "HIGH",
     "description": "Concurrent use increases risk of GI bleeding and may reduce Aspirin's cardioprotective effect."},
    {"drug_a": "Metformin", "drug_b": "Furosemide", "severity": "LOW",
     "description": "Furosemide may slightly increase Metformin plasma levels. Generally well tolerated."},
    {"drug_a": "Metoprolol", "drug_b": "Amlodipine", "severity": "MODERATE",
     "description": "Both lower heart rate and blood pressure. Risk of excessive bradycardia or hypotension."},
    {"drug_a": "Warfarin", "drug_b": "Aspirin", "severity": "HIGH",
     "description": "Significantly increased bleeding risk. Requires close INR monitoring."},
    {"drug_a": "Atorvastatin", "drug_b": "Amlodipine", "severity": "LOW",
     "description": "Amlodipine may slightly increase Atorvastatin levels. Usually clinically insignificant."},
    {"drug_a": "Insulin Glargine", "drug_b": "Metformin", "severity": "LOW",
     "description": "Additive hypoglycemic effect. Monitor blood glucose when used together."},
    {"drug_a": "Azithromycin", "drug_b": "Amiodarone", "severity": "HIGH",
     "description": "Both prolong QT interval. Combined use increases risk of cardiac arrhythmia."},
    {"drug_a": "Ibuprofen", "drug_b": "Lisinopril", "severity": "MODERATE",
     "description": "NSAIDs may reduce the antihypertensive effect of ACE inhibitors and increase renal risk."},
]


@tool
def check_drug_interactions(patient_id: str) -> dict:
    """Check for known drug interactions in a patient's current medication list.

    Retrieves the patient's medications and checks all pairs against a database
    of known interactions.

    Args:
        patient_id: The patient identifier (e.g., P-10001)

    Returns:
        List of detected interactions with severity and clinical description.
    """
    response = medications_table.query(
        KeyConditionExpression=Key("patient_id").eq(patient_id),
    )
    items = response.get("Items", [])
    if not items:
        return {"error": f"No medications found for patient {patient_id}"}

    med_names = [m.get("name") for m in items]
    med_names_set = set(med_names)

    interactions_found = []
    for interaction in KNOWN_INTERACTIONS:
        if interaction["drug_a"] in med_names_set and interaction["drug_b"] in med_names_set:
            interactions_found.append({
                "drug_a": interaction["drug_a"],
                "drug_b": interaction["drug_b"],
                "severity": interaction["severity"],
                "description": interaction["description"],
            })

    high_count = sum(1 for i in interactions_found if i["severity"] == "HIGH")
    moderate_count = sum(1 for i in interactions_found if i["severity"] == "MODERATE")
    low_count = sum(1 for i in interactions_found if i["severity"] == "LOW")

    return sanitize({
        "patient_id": patient_id,
        "medications_checked": med_names,
        "interaction_count": len(interactions_found),
        "high_severity": high_count,
        "moderate_severity": moderate_count,
        "low_severity": low_count,
        "interactions": interactions_found,
    })
