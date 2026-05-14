"""Drug Development Pipeline Data Harmonization Agent.

This agent harmonizes pharmaceutical pipeline data from multiple companies,
enriches it with biomedical ontologies, and validates the results.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from bedrock_agentcore.app import tool
except ImportError:
    # Fallback for environments where bedrock_agentcore is not installed (e.g., testing)
    def tool(fn):
        return fn

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are a pharmaceutical pipeline data assistant specialized in analyzing drug development data.
Your primary task is to interpret user queries about drug development pipelines, clinical trials,
and pharmaceutical research, and provide relevant insights based on the knowledge base.

Follow these instructions carefully:

1. When responding to queries about drug development pipelines:
   a. Provide information about drug candidates, their targets, mechanisms of action, and development stages
   b. Include details about therapeutic areas, indications, and clinical trial phases when available
   c. Explain the significance of the data in the context of pharmaceutical research and development

2. For queries about specific diseases or therapeutic areas:
   a. Identify relevant drug candidates in the pipeline
   b. Provide information about the disease mechanisms and how the drugs target them
   c. Include details about clinical trials and development status

3. When providing your response:
   a. Start with a brief summary of your understanding of the user's query
   b. Organize information in a clear, structured manner
   c. Use technical pharmaceutical terminology appropriately
   d. Cite specific information from the knowledge base
   e. Conclude with a concise summary of the key insights

Remember that you are working with pharmaceutical pipeline data that includes information about
drug candidates, clinical trials, therapeutic areas, and development stages. Your goal is to help
users understand and analyze this data effectively."""

# --- Ontology Mappings ---

THERAPEUTIC_AREA_MAPPINGS = {
    "Cardiovascular/Metabolic": {"efo_id": "EFO_0000319", "efo_label": "cardiovascular disease", "mesh_id": "D002318", "atc_class": "C"},
    "Diabetes": {"efo_id": "EFO_0000400", "efo_label": "diabetes mellitus", "mesh_id": "D003920", "mondo_id": "MONDO_0005015"},
    "Immunology": {"efo_id": "EFO_0000540", "efo_label": "immune system disease", "mesh_id": "D007154", "atc_class": "L"},
    "Neuroscience": {"efo_id": "EFO_0000618", "efo_label": "nervous system disease", "mesh_id": "D009422", "atc_class": "N"},
    "Obesity": {"efo_id": "EFO_0001073", "efo_label": "obesity", "mesh_id": "D009765", "mondo_id": "MONDO_0011122"},
    "Oncology": {"efo_id": "EFO_0000616", "efo_label": "neoplasm", "mesh_id": "D009369", "mondo_id": "MONDO_0004992", "atc_class": "L01"},
    "Rare Diseases": {"efo_id": "EFO_0000651", "efo_label": "rare disease", "mesh_id": "D035583", "mondo_id": "MONDO_0021136"},
    "Vaccines": {"efo_id": "EFO_0000876", "efo_label": "vaccine", "mesh_id": "D014612", "atc_class": "J07"},
}

INDICATION_MAPPINGS = {
    "Type 2 diabetes": {"mondo_id": "MONDO_0005148", "mesh_id": "D003924", "icd10": "E11"},
    "Obesity": {"mondo_id": "MONDO_0011122", "mesh_id": "D009765", "icd10": "E66"},
    "Alzheimer's disease": {"mondo_id": "MONDO_0004975", "mesh_id": "D000544", "icd10": "G30"},
    "Breast cancer": {"mondo_id": "MONDO_0007254", "mesh_id": "D001943", "icd10": "C50"},
    "Prostate cancer": {"mondo_id": "MONDO_0008315", "mesh_id": "D011471", "icd10": "C61"},
    "Heart failure": {"mondo_id": "MONDO_0005252", "mesh_id": "D006333", "icd10": "I50"},
    "Rheumatoid Arthritis": {"mondo_id": "MONDO_0008383", "mesh_id": "D001172", "icd10": "M06"},
    "Multiple sclerosis": {"mondo_id": "MONDO_0005301", "mesh_id": "D009103", "icd10": "G35"},
    "Sickle Cell Disease": {"mondo_id": "MONDO_0011382", "mesh_id": "D000755", "icd10": "D57"},
}

COMPOUND_TYPE_MAPPINGS = {
    "Biologic": {"chebi_id": "CHEBI_33695", "ncit_id": "C1909", "ncit_label": "Biological Products"},
    "Small Molecule": {"chebi_id": "CHEBI_25367", "ncit_id": "C1908", "ncit_label": "Chemical"},
    "Vaccine": {"chebi_id": "CHEBI_59132", "ncit_id": "C906", "ncit_label": "Vaccine"},
    "Cell Therapy": {"ncit_id": "C15262", "ncit_label": "Cell Therapy"},
    "RNA Therapy": {"chebi_id": "CHEBI_33697", "ncit_id": "C13280", "ncit_label": "RNA"},
    "Radioligand": {"ncit_id": "C17262", "ncit_label": "Radioligand"},
}

PHASE_MAPPINGS = {
    "Phase 1": {"ncit_id": "C15600", "ncit_label": "Phase I Trial"},
    "Phase 2": {"ncit_id": "C15601", "ncit_label": "Phase II Trial"},
    "Phase 3": {"ncit_id": "C15602", "ncit_label": "Phase III Trial"},
    "Registration/Filed": {"ncit_id": "C25646", "ncit_label": "Regulatory Submission"},
}


def _normalize_phase(phase: str) -> str:
    mapping = {
        "phase 1": "Phase 1", "phase_1": "Phase 1",
        "phase 2": "Phase 2", "phase_2": "Phase 2",
        "phase 3": "Phase 3", "phase_3": "Phase 3",
        "filed": "Registration/Filed", "registration": "Registration/Filed",
    }
    return mapping.get(phase.lower().strip(), phase)


def _normalize_therapeutic_area(area: str) -> str:
    mapping = {
        "inflammation & immunology": "Immunology",
        "internal medicine": "Cardiovascular/Metabolic",
        "cardiovascular disease": "Cardiovascular/Metabolic",
        "oncology: solid tumors": "Oncology",
        "oncology: hematology": "Oncology",
        "emerging therapy areas": "Other/Emerging",
        "rare blood disorders": "Rare Diseases",
        "rare endocrine disorders": "Rare Diseases",
        "neuroscience": "Neuroscience",
        "vaccines": "Vaccines",
    }
    return mapping.get(area.lower(), area)


def _get_indication_ontology(indication: str) -> dict:
    if indication in INDICATION_MAPPINGS:
        return INDICATION_MAPPINGS[indication]
    for key, value in INDICATION_MAPPINGS.items():
        if key.lower() in indication.lower() or indication.lower() in key.lower():
            return value
    return {}


@tool
def harmonize_pipeline_data(data_json: str) -> str:
    """Harmonize pharmaceutical pipeline data from multiple companies into a common data model.

    Takes raw pipeline data from Novo Nordisk, Pfizer, and Novartis and produces
    a unified JSON structure with normalized phases, therapeutic areas, and compound types.

    Args:
        data_json: JSON string containing raw pipeline data with keys for each company
                   (novo_nordisk, pfizer, novartis), each containing pipeline_candidates.

    Returns:
        JSON string with harmonized pipeline data including unified_pipeline,
        summary_statistics, and metadata.
    """
    raw_data = json.loads(data_json)
    all_candidates = []
    companies_info = []
    candidate_id_counter = 1

    for company_key, company_data in raw_data.items():
        if company_key == "novo_nordisk":
            code, name = "NVO", "Novo Nordisk"
            for phase_key, candidates in company_data.get("pipeline_candidates", {}).items():
                phase = _normalize_phase(phase_key)
                for c in candidates:
                    all_candidates.append({
                        "candidate_id": f"{code}_{candidate_id_counter:03d}",
                        "company": name, "company_code": code,
                        "compound_name": c.get("name", ""),
                        "indication": c.get("indication", ""),
                        "therapeutic_area": _normalize_therapeutic_area(c.get("therapy_area", "")),
                        "development_phase": phase,
                        "compound_type": "Biologic" if any(w in c.get("description", "").lower() for w in ["insulin", "peptide", "antibody"]) else "Unknown",
                        "mechanism_of_action": c.get("description", ""),
                        "status": "Current",
                    })
                    candidate_id_counter += 1

        elif company_key == "pfizer":
            code, name = "PFE", "Pfizer"
            for phase_key, candidates in company_data.get("sample_pipeline_candidates", {}).items():
                phase = _normalize_phase(phase_key)
                for c in candidates:
                    all_candidates.append({
                        "candidate_id": f"{code}_{candidate_id_counter:03d}",
                        "company": name, "company_code": code,
                        "compound_name": c.get("name", ""),
                        "indication": c.get("indication", ""),
                        "therapeutic_area": _normalize_therapeutic_area(c.get("area_of_focus", "")),
                        "development_phase": phase,
                        "compound_type": c.get("compound_type", "Unknown"),
                        "mechanism_of_action": None,
                        "status": c.get("status", "Current"),
                    })
                    candidate_id_counter += 1

        elif company_key == "novartis":
            code, name = "NVS", "Novartis"
            for c in company_data.get("pipeline_candidates", []):
                phase = _normalize_phase(c.get("phase", ""))
                mechanism = c.get("mechanism", "")
                if "radioligand" in mechanism.lower():
                    ctype = "Radioligand"
                elif "monoclonal antibody" in mechanism.lower():
                    ctype = "Biologic"
                else:
                    ctype = "Unknown"
                all_candidates.append({
                    "candidate_id": f"{code}_{candidate_id_counter:03d}",
                    "company": name, "company_code": code,
                    "compound_name": c.get("compound", ""),
                    "indication": c.get("indication", ""),
                    "therapeutic_area": _normalize_therapeutic_area(c.get("therapeutic_area", "")),
                    "development_phase": phase,
                    "compound_type": ctype,
                    "mechanism_of_action": mechanism,
                    "status": "Current",
                })
                candidate_id_counter += 1

    # Build summary
    by_company: dict[str, int] = {}
    by_phase: dict[str, int] = {}
    by_area: dict[str, int] = {}
    for c in all_candidates:
        by_company[c["company"]] = by_company.get(c["company"], 0) + 1
        by_phase[c["development_phase"]] = by_phase.get(c["development_phase"], 0) + 1
        by_area[c["therapeutic_area"]] = by_area.get(c["therapeutic_area"], 0) + 1

    result = {
        "metadata": {
            "harmonization_date": datetime.now().isoformat(),
            "version": "1.0",
            "total_candidates": len(all_candidates),
        },
        "unified_pipeline": all_candidates,
        "summary_statistics": {
            "total_candidates": len(all_candidates),
            "by_company": by_company,
            "by_phase": by_phase,
            "by_therapeutic_area": by_area,
        },
    }
    return json.dumps(result, indent=2)


@tool
def enrich_with_ontologies(harmonized_data_json: str) -> str:
    """Enrich harmonized pipeline data with biomedical ontology annotations.

    Adds semantic annotations from MONDO, ChEBI, EFO, NCIT, MeSH, ATC, ICD-10
    to each drug candidate based on therapeutic area, indication, compound type,
    and development phase.

    Args:
        harmonized_data_json: JSON string of harmonized pipeline data (output of harmonize_pipeline_data).

    Returns:
        JSON string with enriched pipeline data including ontological_annotations per candidate
        and enrichment_statistics.
    """
    data = json.loads(harmonized_data_json)
    candidates = data.get("unified_pipeline", [])
    enriched = []

    for candidate in candidates:
        enriched_c = candidate.copy()
        annotations: dict[str, Any] = {}

        if candidate.get("therapeutic_area"):
            annotations["therapeutic_area"] = THERAPEUTIC_AREA_MAPPINGS.get(candidate["therapeutic_area"], {})

        if candidate.get("indication"):
            annotations["indication"] = _get_indication_ontology(candidate["indication"])

        if candidate.get("compound_type"):
            annotations["compound_type"] = COMPOUND_TYPE_MAPPINGS.get(candidate["compound_type"], {})

        if candidate.get("development_phase"):
            annotations["development_phase"] = PHASE_MAPPINGS.get(candidate["development_phase"], {})

        enriched_c["ontological_annotations"] = annotations
        enriched.append(enriched_c)

    # Stats
    enriched_count = sum(1 for c in enriched if any(c.get("ontological_annotations", {}).values()))
    total = len(enriched)

    result = {
        "metadata": {
            "enrichment_date": datetime.now().isoformat(),
            "ontologies_used": ["MONDO", "ChEBI", "EFO", "NCIT", "MeSH", "ATC", "ICD-10"],
            "total_candidates": total,
            "enrichment_coverage_pct": round((enriched_count / total * 100) if total else 0, 1),
        },
        "enriched_pipeline": enriched,
        "summary_statistics": data.get("summary_statistics", {}),
    }
    return json.dumps(result, indent=2)


@tool
def validate_harmonized_data(harmonized_data_json: str) -> str:
    """Validate harmonized pharmaceutical pipeline data for schema compliance and data quality.

    Checks required fields, candidate ID format, controlled vocabulary values,
    data consistency, and calculates a data quality score.

    Args:
        harmonized_data_json: JSON string of harmonized pipeline data to validate.

    Returns:
        JSON string with validation results including overall_status (PASS/FAIL),
        errors, warnings, and data_quality_score.
    """
    data = json.loads(harmonized_data_json)
    errors = []
    warnings = []

    candidates = data.get("unified_pipeline", [])
    valid_companies = {"Novo Nordisk", "Pfizer", "Novartis"}
    valid_codes = {"NVO", "PFE", "NVS"}
    valid_phases = {"Phase 1", "Phase 2", "Phase 3", "Registration/Filed"}
    required_fields = ["candidate_id", "company", "company_code", "compound_name", "indication", "therapeutic_area", "development_phase"]

    seen_ids: set[str] = set()
    for i, c in enumerate(candidates):
        for field in required_fields:
            if not c.get(field):
                errors.append(f"Record {i+1}: missing or empty '{field}'")

        cid = c.get("candidate_id", "")
        if cid in seen_ids:
            errors.append(f"Duplicate candidate_id: {cid}")
        seen_ids.add(cid)

        if cid and not re.match(r"^(NVO|PFE|NVS)_\d{3}$", cid):
            errors.append(f"Invalid candidate_id format: {cid}")

        if c.get("company") and c["company"] not in valid_companies:
            errors.append(f"Record {i+1}: invalid company '{c['company']}'")

        if c.get("company_code") and c["company_code"] not in valid_codes:
            errors.append(f"Record {i+1}: invalid company_code '{c['company_code']}'")

        if c.get("development_phase") and c["development_phase"] not in valid_phases:
            errors.append(f"Record {i+1}: invalid phase '{c['development_phase']}'")

    # Quality score
    critical_fields = ["compound_name", "indication", "therapeutic_area", "development_phase"]
    completeness = 0
    for field in critical_fields:
        filled = sum(1 for c in candidates if c.get(field))
        completeness += (filled / len(candidates) * 100) if candidates else 0
    completeness /= len(critical_fields)

    error_penalty = min(len(errors) * 5, 50)
    warning_penalty = min(len(warnings) * 2, 20)
    quality_score = max(0, completeness - error_penalty - warning_penalty)

    result = {
        "overall_status": "PASS" if not errors else "FAIL",
        "total_candidates": len(candidates),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors[:20],
        "warnings": warnings[:10],
        "data_quality_score": round(quality_score, 1),
    }
    return json.dumps(result, indent=2)


@tool
def analyze_pipeline_statistics(harmonized_data_json: str) -> str:
    """Analyze harmonized pipeline data and produce summary statistics.

    Provides distribution analysis by company, development phase, therapeutic area,
    and compound type.

    Args:
        harmonized_data_json: JSON string of harmonized pipeline data.

    Returns:
        JSON string with analysis results including distributions and key insights.
    """
    data = json.loads(harmonized_data_json)
    candidates = data.get("unified_pipeline", [])

    by_company: dict[str, int] = {}
    by_phase: dict[str, int] = {}
    by_area: dict[str, int] = {}
    by_type: dict[str, int] = {}

    for c in candidates:
        by_company[c.get("company", "Unknown")] = by_company.get(c.get("company", "Unknown"), 0) + 1
        by_phase[c.get("development_phase", "Unknown")] = by_phase.get(c.get("development_phase", "Unknown"), 0) + 1
        by_area[c.get("therapeutic_area", "Unknown")] = by_area.get(c.get("therapeutic_area", "Unknown"), 0) + 1
        by_type[c.get("compound_type", "Unknown")] = by_type.get(c.get("compound_type", "Unknown"), 0) + 1

    result = {
        "total_candidates": len(candidates),
        "by_company": by_company,
        "by_development_phase": by_phase,
        "by_therapeutic_area": by_area,
        "by_compound_type": by_type,
        "insights": [
            f"Total of {len(candidates)} drug candidates across {len(by_company)} companies",
            f"Most active therapeutic area: {max(by_area, key=by_area.get) if by_area else 'N/A'}",
            f"Most common phase: {max(by_phase, key=by_phase.get) if by_phase else 'N/A'}",
        ],
    }
    return json.dumps(result, indent=2)


def agent_task(task: str) -> str:
    """Process a drug development pipeline data harmonization task.

    This agent harmonizes pharmaceutical pipeline data from multiple companies,
    enriches it with biomedical ontologies (MONDO, ChEBI, EFO, NCIT, MeSH, ATC, ICD-10),
    validates data quality, and provides analytical insights.

    Args:
        task: Natural language description of the data harmonization or analysis task.

    Returns:
        Response from the agent with results of the requested operation.
    """
    import boto3

    client = boto3.client("bedrock-runtime")
    tools_config = [
        {
            "toolSpec": {
                "name": "harmonize_pipeline_data",
                "description": harmonize_pipeline_data.__doc__,
                "inputSchema": {"json": {"type": "object", "properties": {"data_json": {"type": "string", "description": "JSON string with raw pipeline data"}}, "required": ["data_json"]}},
            }
        },
        {
            "toolSpec": {
                "name": "enrich_with_ontologies",
                "description": enrich_with_ontologies.__doc__,
                "inputSchema": {"json": {"type": "object", "properties": {"harmonized_data_json": {"type": "string", "description": "JSON string of harmonized pipeline data"}}, "required": ["harmonized_data_json"]}},
            }
        },
        {
            "toolSpec": {
                "name": "validate_harmonized_data",
                "description": validate_harmonized_data.__doc__,
                "inputSchema": {"json": {"type": "object", "properties": {"harmonized_data_json": {"type": "string", "description": "JSON string of harmonized pipeline data"}}, "required": ["harmonized_data_json"]}},
            }
        },
        {
            "toolSpec": {
                "name": "analyze_pipeline_statistics",
                "description": analyze_pipeline_statistics.__doc__,
                "inputSchema": {"json": {"type": "object", "properties": {"harmonized_data_json": {"type": "string", "description": "JSON string of harmonized pipeline data"}}, "required": ["harmonized_data_json"]}},
            }
        },
    ]

    tool_map = {
        "harmonize_pipeline_data": harmonize_pipeline_data,
        "enrich_with_ontologies": enrich_with_ontologies,
        "validate_harmonized_data": validate_harmonized_data,
        "analyze_pipeline_statistics": analyze_pipeline_statistics,
    }

    messages = [{"role": "user", "content": [{"text": task}]}]

    while True:
        response = client.converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig={"tools": [{"toolSpec": t["toolSpec"]} for t in tools_config]},
        )

        output_message = response["output"]["message"]
        messages.append(output_message)

        if response["stopReason"] == "tool_use":
            tool_results = []
            for block in output_message["content"]:
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    fn = tool_map[tool_use["name"]]
                    result = fn(**tool_use["input"])
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use["toolUseId"],
                            "content": [{"text": result}],
                        }
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            # Extract final text response
            for block in output_message["content"]:
                if "text" in block:
                    return block["text"]
            return ""
