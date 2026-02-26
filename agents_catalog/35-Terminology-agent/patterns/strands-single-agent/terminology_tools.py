"""
Terminology Agent Tools

Entity recognition and query standardization tools for medical/scientific terminology.
Uses Amazon Bedrock Converse API for LLM-based extraction and classification.
"""

from strands.tools import tool
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import boto3
import re
import os


class EntityType(str, Enum):
    """Supported entity types for medical/scientific terminology."""
    DISEASE = "DISEASE"
    DRUG = "DRUG"
    PROCEDURE = "PROCEDURE"
    LAB_TEST = "LAB_TEST"
    ANATOMY = "ANATOMY"
    PHENOTYPE = "PHENOTYPE"
    GENE = "GENE"
    PROTEIN = "PROTEIN"
    ORGANISM = "ORGANISM"
    CHEMICAL = "CHEMICAL"
    UNKNOWN = "UNKNOWN"


# Initialize Bedrock client (reused across tool calls)
_bedrock_client = None


def _get_bedrock_client():
    """Get or create Bedrock client."""
    global _bedrock_client
    if _bedrock_client is None:
        region = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
        _bedrock_client = boto3.client("bedrock-runtime", region_name=region)
    return _bedrock_client


def _call_bedrock_converse(prompt: str, system_prompt: str = None) -> str:
    """
    Call Bedrock Converse API with Claude Sonnet 4.5.

    Args:
        prompt: User prompt
        system_prompt: Optional system prompt

    Returns:
        Model response text
    """
    client = _get_bedrock_client()

    messages = [{"role": "user", "content": [{"text": prompt}]}]

    kwargs = {
        "modelId": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",  # Claude Sonnet 4.5
        "messages": messages,
        "inferenceConfig": {"temperature": 0.0, "maxTokens": 2000},
    }

    if system_prompt:
        kwargs["system"] = [{"text": system_prompt}]

    response = client.converse(**kwargs)
    return response["output"]["message"]["content"][0]["text"]


@tool
def extract_entities(query: str) -> List[Dict[str, Any]]:
    """
    Extract medical and scientific entities from a natural language query.

    This tool identifies entities such as diseases, drugs, genes, procedures,
    anatomical structures, and other medical/scientific terms in user queries.
    Uses Amazon Bedrock with Claude for intelligent entity extraction.

    Args:
        query: User's natural language query containing medical/scientific terms

    Returns:
        List of dictionaries containing entity information:
        - text: Original entity text from the query
        - entity_type: Classified type (DISEASE, DRUG, GENE, etc.)
        - start_pos: Start position in original query
        - end_pos: End position in original query
        - confidence: Extraction confidence score (0.0-1.0)
        - context: Surrounding context from the query

    Example:
        >>> extract_entities("Show me trials for lymphocytic leukemia")
        [
            {
                "text": "lymphocytic leukemia",
                "entity_type": "DISEASE",
                "start_pos": 20,
                "end_pos": 40,
                "confidence": 0.95,
                "context": "Show me trials for lymphocytic leukemia"
            }
        ]
    """
    system_prompt = """You are a medical entity extraction expert. Extract ALL medical and scientific entities from the query.

Entity types:
- DISEASE: Diseases, conditions, syndromes
- DRUG: Medications, drugs, treatments
- GENE: Genes, gene symbols (e.g., IL-23, TNF, BDNF)
- PROTEIN: Proteins, protein names
- ANATOMY: Anatomical structures, tissues, organs
- LAB_TEST: Laboratory tests, measurements, assays
- PROCEDURE: Medical procedures, surgeries
- PHENOTYPE: Observable characteristics, symptoms
- ORGANISM: Species, organisms
- CHEMICAL: Chemical compounds
- UNKNOWN: Unclear medical terms

Return ONLY a JSON array with this exact structure:
[
  {
    "text": "exact entity text from query",
    "entity_type": "TYPE",
    "confidence": 0.95
  }
]

Rules:
- Extract ALL medical/scientific entities
- Use exact text from the query
- Confidence: 0.9-1.0 (certain), 0.7-0.9 (likely), 0.5-0.7 (possible)
- Return empty array [] if no entities found"""

    prompt = f"""Query: "{query}"

Extract all medical/scientific entities. Return JSON array only."""

    try:
        response_text = _call_bedrock_converse(prompt, system_prompt)

        # Extract JSON from response
        json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
        if json_match:
            entities_raw = json.loads(json_match.group())
        else:
            entities_raw = []

        # Enrich with position information
        entities = []
        for entity in entities_raw:
            text = entity.get("text", "")
            # Find position in query (case-insensitive)
            start_pos = query.lower().find(text.lower())
            if start_pos != -1:
                end_pos = start_pos + len(text)
                entities.append(
                    {
                        "text": query[start_pos:end_pos],  # Use exact case from query
                        "entity_type": entity.get("entity_type", "UNKNOWN"),
                        "start_pos": start_pos,
                        "end_pos": end_pos,
                        "confidence": entity.get("confidence", 0.7),
                        "context": query,
                    }
                )

        return entities

    except Exception as e:
        # Fallback: return empty list on error
        print(f"[TOOL ERROR] extract_entities failed: {e}")
        return []


@tool
def classify_entity_type(entity_text: str, context: str) -> str:
    """
    Classify an entity into a specific medical/scientific type.

    This tool determines the most appropriate entity type for a given term
    based on the entity text and its surrounding context.
    Uses Amazon Bedrock with Claude for intelligent classification.

    Args:
        entity_text: The entity text to classify
        context: Surrounding context from the original query

    Returns:
        Entity type as string: DISEASE, DRUG, PROCEDURE, LAB_TEST, ANATOMY,
        PHENOTYPE, GENE, PROTEIN, ORGANISM, CHEMICAL, or UNKNOWN

    Example:
        >>> classify_entity_type("aspirin", "patient taking aspirin daily")
        "DRUG"

        >>> classify_entity_type("IL-23", "expression of IL-23 in tissue")
        "GENE"
    """
    system_prompt = """You are a medical terminology classification expert.

Entity types:
- DISEASE: Diseases, conditions, syndromes
- DRUG: Medications, drugs, treatments
- GENE: Genes, gene symbols
- PROTEIN: Proteins
- ANATOMY: Anatomical structures, tissues, organs
- LAB_TEST: Laboratory tests, measurements
- PROCEDURE: Medical procedures, surgeries
- PHENOTYPE: Observable characteristics, symptoms
- ORGANISM: Species, organisms
- CHEMICAL: Chemical compounds
- UNKNOWN: Unclear

Return ONLY the entity type, nothing else."""

    prompt = f"""Entity: "{entity_text}"
Context: "{context}"

What type is this entity? Return only the type."""

    try:
        response = _call_bedrock_converse(prompt, system_prompt)
        # Extract the type from response
        response_upper = response.strip().upper()

        # Match to valid entity types
        for entity_type in EntityType:
            if entity_type.value in response_upper:
                return entity_type.value

        return EntityType.UNKNOWN.value

    except Exception as e:
        print(f"[TOOL ERROR] classify_entity_type failed: {e}")
        return EntityType.UNKNOWN.value


@tool
def generate_standardized_query(
    original_query: str,
    entities: List[Dict[str, Any]],
    ontology_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate standardized query output with terminology mappings.

    This tool creates a structured output containing the original query,
    extracted entities, standardized ontology codes, and metadata for
    downstream processing by domain-specific agents.

    Args:
        original_query: Original user query text
        entities: List of extracted entities from extract_entities()
        ontology_results: Results from ontology lookups (OLS MCP tools)

    Returns:
        Dictionary containing:
        - original_query: Original text
        - standardized_query: Structured query with codes and mappings
        - metadata: Processing information (time, tools used, confidence)

    Example:
        >>> generate_standardized_query(
        ...     "Show me trials for lymphocytic leukemia",
        ...     entities=[{"text": "lymphocytic leukemia", "entity_type": "DISEASE"}],
        ...     ontology_results=[{"code": "MONDO:0004948", "label": "lymphoid leukemia"}]
        ... )
        {
            "original_query": "Show me trials for lymphocytic leukemia",
            "standardized_query": {
                "entities": [
                    {
                        "original_text": "lymphocytic leukemia",
                        "entity_type": "DISEASE",
                        "standardized_terms": [
                            {
                                "ontology": "MONDO",
                                "code": "MONDO:0004948",
                                "preferred_label": "lymphoid leukemia",
                                "synonyms": ["lymphocytic leukemia"]
                            }
                        ]
                    }
                ]
            },
            "metadata": {
                "processing_time_ms": 450,
                "confidence_score": 0.95
            }
        }
    """
    # Build standardized query structure
    standardized_entities = []

    for entity in entities:
        # Find matching ontology results for this entity
        matching_results = [
            r
            for r in ontology_results
            if r.get("entity_text", "").lower() == entity["text"].lower()
        ]

        standardized_entity = {
            "original_text": entity["text"],
            "entity_type": entity["entity_type"],
            "standardized_terms": matching_results if matching_results else [],
            "confidence": entity.get("confidence", 0.0),
        }

        # Add hierarchical terms if available
        if matching_results and any(
            "parents" in r or "children" in r for r in matching_results
        ):
            standardized_entity["hierarchical_terms"] = {
                "parents": [
                    r.get("parents", []) for r in matching_results if "parents" in r
                ],
                "children": [
                    r.get("children", []) for r in matching_results if "children" in r
                ],
            }

        standardized_entities.append(standardized_entity)

    # Determine query intent based on entities and context
    query_intent = _infer_query_intent(original_query, entities)

    # Generate suggested filters for downstream agents
    suggested_filters = _generate_filters(standardized_entities)

    return {
        "original_query": original_query,
        "standardized_query": {
            "entities": standardized_entities,
            "query_intent": query_intent,
            "suggested_filters": suggested_filters,
        },
        "metadata": {
            "processing_time_ms": 0,  # Placeholder
            "tools_used": [
                "extract_entities",
                "ontology_lookup",
                "generate_standardized_query",
            ],
            "confidence_score": _calculate_overall_confidence(standardized_entities),
            "warnings": _generate_warnings(standardized_entities),
        },
    }


def _infer_query_intent(query: str, entities: List[Dict[str, Any]]) -> str:
    """Infer the intent of the query based on keywords and entities."""
    query_lower = query.lower()

    if any(keyword in query_lower for keyword in ["trial", "study", "clinical"]):
        return "clinical_trial_search"

    if any(
        keyword in query_lower
        for keyword in ["expression", "concordance", "biomarker"]
    ):
        return "biomarker_analysis"

    if any(
        keyword in query_lower for keyword in ["symptom", "phenotype", "characteristic"]
    ):
        return "phenotype_query"

    if any(keyword in query_lower for keyword in ["drug", "medication", "treatment"]):
        return "drug_information"

    return "general_query"


def _generate_filters(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate suggested filters for downstream agents."""
    filters = {}

    for entity in entities:
        entity_type = entity["entity_type"]
        codes = [
            term.get("code")
            for term in entity.get("standardized_terms", [])
            if "code" in term
        ]

        if entity_type == "DISEASE" and codes:
            filters["disease_codes"] = codes
            filters["include_subtypes"] = True

        elif entity_type == "GENE" and codes:
            filters["gene_symbols"] = [entity["original_text"]]

        elif entity_type == "ANATOMY" and codes:
            filters["tissue_codes"] = codes

        elif entity_type == "DRUG" and codes:
            filters["drug_codes"] = codes

    return filters


def _calculate_overall_confidence(entities: List[Dict[str, Any]]) -> float:
    """Calculate overall confidence score for the standardization."""
    if not entities:
        return 0.0

    confidences = [e.get("confidence", 0.0) for e in entities]
    return sum(confidences) / len(confidences)


def _generate_warnings(entities: List[Dict[str, Any]]) -> List[str]:
    """Generate warnings for incomplete or low-confidence standardization."""
    warnings = []

    for entity in entities:
        if not entity.get("standardized_terms"):
            warnings.append(
                f"No ontology mapping found for '{entity['original_text']}'"
            )

        if entity.get("confidence", 1.0) < 0.5:
            warnings.append(
                f"Low confidence extraction for '{entity['original_text']}'"
            )

    return warnings


@tool
def suggest_ontology_codes(
    term: str, entity_type: str, ontologies: List[str] = None
) -> Dict[str, Any]:
    """
    Suggest ontology codes using LLM's built-in knowledge of medical ontologies.

    This tool leverages Claude's training data knowledge of major medical ontologies
    (MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC, etc.) to provide preliminary
    code suggestions without requiring external API calls.

    Use this for:
    - Quick preliminary mappings before OLS lookup
    - Offline scenarios when OLS is unavailable
    - Pre-filtering to narrow down OLS search space
    - Suggesting likely codes for common terms

    Args:
        term: Medical/scientific term to map
        entity_type: Type of entity (DISEASE, DRUG, PROCEDURE, LAB_TEST, etc.)
        ontologies: Optional list of specific ontologies to search
                   (e.g., ["MedDRA", "SNOMED CT", "ICD-10"])

    Returns:
        Dictionary containing:
        - term: Original term
        - entity_type: Entity type
        - suggested_codes: List of suggested codes from various ontologies
        - confidence: Overall confidence in suggestions (0.0-1.0)
        - note: Explanation that these are LLM-based suggestions

    Example:
        >>> suggest_ontology_codes("myocardial infarction", "DISEASE", ["MedDRA", "ICD-10"])
        {
            "term": "myocardial infarction",
            "entity_type": "DISEASE",
            "suggested_codes": [
                {
                    "ontology": "MedDRA",
                    "code": "10028596",
                    "preferred_term": "Myocardial infarction",
                    "level": "PT (Preferred Term)",
                    "confidence": 0.85
                },
                {
                    "ontology": "ICD-10",
                    "code": "I21.9",
                    "description": "Acute myocardial infarction, unspecified",
                    "confidence": 0.90
                }
            ],
            "confidence": 0.88,
            "note": "LLM-based suggestions from training data. Verify with authoritative sources."
        }

    Note:
        These are suggestions based on Claude's training data, not authoritative
        lookups from official ontology APIs. Always verify critical mappings using
        OLS or other authoritative sources.
    """
    ontology_list = ontologies if ontologies else ["MedDRA", "SNOMED CT", "ICD-10"]
    ontology_str = ", ".join(ontology_list)

    system_prompt = f"""You are a medical terminology expert with extensive knowledge of medical ontologies.

Your task: Suggest likely ontology codes for medical terms based on your training data knowledge.

Ontologies in your knowledge:
- MedDRA (Medical Dictionary for Regulatory Activities): Adverse events, medical history
- SNOMED CT: Clinical terminology for electronic health records
- ICD-10/11: Disease classification for mortality and morbidity
- RxNorm: Normalized drug names
- LOINC: Laboratory observations
- CPT: Procedures and services
- Others as relevant

Return ONLY a JSON object with this structure:
{{
  "suggested_codes": [
    {{
      "ontology": "MedDRA",
      "code": "code_id",
      "preferred_term": "official term",
      "level": "PT/LLT/HLT/etc (if applicable)",
      "confidence": 0.85,
      "notes": "optional context"
    }}
  ]
}}

Rules:
- Only suggest codes you have high confidence in from training data
- Include multiple ontologies if requested
- Confidence: 0.8-1.0 (very likely), 0.6-0.8 (likely), 0.4-0.6 (possible)
- Be conservative - better to return fewer high-quality suggestions
- If unsure, set lower confidence or omit"""

    prompt = f"""Term: "{term}"
Entity Type: {entity_type}
Target Ontologies: {ontology_str}

Suggest ontology codes from your training data knowledge. Return JSON only."""

    try:
        response_text = _call_bedrock_converse(prompt, system_prompt)

        # Extract JSON from response
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            suggested_codes = result.get("suggested_codes", [])
        else:
            suggested_codes = []

        # Calculate overall confidence
        if suggested_codes:
            confidences = [code.get("confidence", 0.5) for code in suggested_codes]
            overall_confidence = sum(confidences) / len(confidences)
        else:
            overall_confidence = 0.0

        return {
            "term": term,
            "entity_type": entity_type,
            "suggested_codes": suggested_codes,
            "confidence": overall_confidence,
            "note": "LLM-based suggestions from training data. Verify with authoritative sources (OLS, official APIs) for production use.",
        }

    except Exception as e:
        print(f"[TOOL ERROR] suggest_ontology_codes failed: {e}")
        return {
            "term": term,
            "entity_type": entity_type,
            "suggested_codes": [],
            "confidence": 0.0,
            "note": f"Error generating suggestions: {str(e)}",
        }
