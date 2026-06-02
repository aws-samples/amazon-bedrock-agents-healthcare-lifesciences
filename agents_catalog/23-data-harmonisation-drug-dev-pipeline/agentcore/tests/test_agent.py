"""Unit tests for Drug Development Pipeline Data Harmonization Agent."""

import json
import pytest
from unittest.mock import patch, MagicMock

from agent.agent_config.agent import (
    harmonize_pipeline_data,
    enrich_with_ontologies,
    validate_harmonized_data,
    analyze_pipeline_statistics,
    agent_task,
    _normalize_phase,
    _normalize_therapeutic_area,
    _get_indication_ontology,
    MODEL_ID,
)


# --- Test data fixtures ---

@pytest.fixture
def raw_pipeline_data():
    return {
        "novo_nordisk": {
            "pipeline_candidates": {
                "phase_1": [
                    {"name": "NN1234", "indication": "Type 2 diabetes", "therapy_area": "internal medicine", "description": "Insulin analog"}
                ],
                "phase_2": [
                    {"name": "NN5678", "indication": "Obesity", "therapy_area": "internal medicine", "description": "GLP-1 peptide receptor agonist"}
                ],
            }
        },
        "pfizer": {
            "sample_pipeline_candidates": {
                "phase_3": [
                    {"name": "PF-001", "indication": "Breast cancer", "area_of_focus": "Oncology: Solid Tumors", "compound_type": "Small Molecule", "status": "Current"}
                ]
            }
        },
        "novartis": {
            "pipeline_candidates": [
                {"compound": "NVS-100", "indication": "Prostate cancer", "therapeutic_area": "Oncology: Hematology", "phase": "Phase 2", "mechanism": "Radioligand therapy"}
            ]
        },
    }


@pytest.fixture
def harmonized_data(raw_pipeline_data):
    result = harmonize_pipeline_data(json.dumps(raw_pipeline_data))
    return json.loads(result)


# --- Normalization tests ---

class TestNormalization:
    def test_normalize_phase_standard(self):
        assert _normalize_phase("phase_1") == "Phase 1"
        assert _normalize_phase("phase 2") == "Phase 2"
        assert _normalize_phase("Phase 3") == "Phase 3"

    def test_normalize_phase_filed(self):
        assert _normalize_phase("filed") == "Registration/Filed"
        assert _normalize_phase("registration") == "Registration/Filed"

    def test_normalize_phase_unknown(self):
        assert _normalize_phase("Preclinical") == "Preclinical"

    def test_normalize_therapeutic_area(self):
        assert _normalize_therapeutic_area("internal medicine") == "Cardiovascular/Metabolic"
        assert _normalize_therapeutic_area("Oncology: Solid Tumors") == "Oncology"
        assert _normalize_therapeutic_area("rare blood disorders") == "Rare Diseases"

    def test_normalize_therapeutic_area_passthrough(self):
        assert _normalize_therapeutic_area("SomeNewArea") == "SomeNewArea"

    def test_get_indication_ontology_exact(self):
        result = _get_indication_ontology("Type 2 diabetes")
        assert result["mondo_id"] == "MONDO_0005148"
        assert result["icd10"] == "E11"

    def test_get_indication_ontology_fuzzy(self):
        result = _get_indication_ontology("Advanced breast cancer stage IV")
        assert result["mondo_id"] == "MONDO_0007254"

    def test_get_indication_ontology_no_match(self):
        result = _get_indication_ontology("Completely unknown disease XYZ")
        assert result == {}


# --- Tool function tests ---

class TestHarmonizePipelineData:
    def test_returns_valid_json(self, raw_pipeline_data):
        result = harmonize_pipeline_data(json.dumps(raw_pipeline_data))
        data = json.loads(result)
        assert "unified_pipeline" in data
        assert "summary_statistics" in data
        assert "metadata" in data

    def test_candidate_count(self, raw_pipeline_data):
        result = json.loads(harmonize_pipeline_data(json.dumps(raw_pipeline_data)))
        assert result["metadata"]["total_candidates"] == 4
        assert len(result["unified_pipeline"]) == 4

    def test_candidate_ids_unique(self, raw_pipeline_data):
        result = json.loads(harmonize_pipeline_data(json.dumps(raw_pipeline_data)))
        ids = [c["candidate_id"] for c in result["unified_pipeline"]]
        assert len(ids) == len(set(ids))

    def test_novo_nordisk_harmonization(self, raw_pipeline_data):
        result = json.loads(harmonize_pipeline_data(json.dumps(raw_pipeline_data)))
        nvo = [c for c in result["unified_pipeline"] if c["company_code"] == "NVO"]
        assert len(nvo) == 2
        assert nvo[0]["development_phase"] == "Phase 1"
        assert nvo[0]["therapeutic_area"] == "Cardiovascular/Metabolic"

    def test_pfizer_harmonization(self, raw_pipeline_data):
        result = json.loads(harmonize_pipeline_data(json.dumps(raw_pipeline_data)))
        pfe = [c for c in result["unified_pipeline"] if c["company_code"] == "PFE"]
        assert len(pfe) == 1
        assert pfe[0]["compound_type"] == "Small Molecule"
        assert pfe[0]["development_phase"] == "Phase 3"

    def test_novartis_harmonization(self, raw_pipeline_data):
        result = json.loads(harmonize_pipeline_data(json.dumps(raw_pipeline_data)))
        nvs = [c for c in result["unified_pipeline"] if c["company_code"] == "NVS"]
        assert len(nvs) == 1
        assert nvs[0]["compound_type"] == "Radioligand"

    def test_summary_statistics(self, harmonized_data):
        stats = harmonized_data["summary_statistics"]
        assert stats["total_candidates"] == 4
        assert "by_company" in stats
        assert "by_phase" in stats


class TestEnrichWithOntologies:
    def test_returns_valid_json(self, harmonized_data):
        result = enrich_with_ontologies(json.dumps(harmonized_data))
        data = json.loads(result)
        assert "enriched_pipeline" in data
        assert "metadata" in data

    def test_adds_ontological_annotations(self, harmonized_data):
        result = json.loads(enrich_with_ontologies(json.dumps(harmonized_data)))
        for candidate in result["enriched_pipeline"]:
            assert "ontological_annotations" in candidate

    def test_therapeutic_area_annotation(self, harmonized_data):
        result = json.loads(enrich_with_ontologies(json.dumps(harmonized_data)))
        nvo = [c for c in result["enriched_pipeline"] if c["company_code"] == "NVO"][0]
        ta = nvo["ontological_annotations"]["therapeutic_area"]
        assert ta.get("efo_id") == "EFO_0000319"

    def test_indication_annotation(self, harmonized_data):
        result = json.loads(enrich_with_ontologies(json.dumps(harmonized_data)))
        nvo = [c for c in result["enriched_pipeline"] if c["company_code"] == "NVO"][0]
        ind = nvo["ontological_annotations"]["indication"]
        assert ind.get("mondo_id") == "MONDO_0005148"

    def test_phase_annotation(self, harmonized_data):
        result = json.loads(enrich_with_ontologies(json.dumps(harmonized_data)))
        candidate = result["enriched_pipeline"][0]
        phase = candidate["ontological_annotations"]["development_phase"]
        assert phase.get("ncit_id") == "C15600"

    def test_enrichment_coverage(self, harmonized_data):
        result = json.loads(enrich_with_ontologies(json.dumps(harmonized_data)))
        assert result["metadata"]["enrichment_coverage_pct"] > 0


class TestValidateHarmonizedData:
    def test_valid_data_passes(self, harmonized_data):
        result = json.loads(validate_harmonized_data(json.dumps(harmonized_data)))
        assert result["overall_status"] == "PASS"
        assert result["error_count"] == 0

    def test_missing_field_fails(self, harmonized_data):
        harmonized_data["unified_pipeline"][0]["compound_name"] = ""
        result = json.loads(validate_harmonized_data(json.dumps(harmonized_data)))
        assert result["overall_status"] == "FAIL"
        assert result["error_count"] > 0

    def test_invalid_company_fails(self, harmonized_data):
        harmonized_data["unified_pipeline"][0]["company"] = "InvalidCo"
        result = json.loads(validate_harmonized_data(json.dumps(harmonized_data)))
        assert result["overall_status"] == "FAIL"

    def test_duplicate_id_fails(self, harmonized_data):
        harmonized_data["unified_pipeline"][1]["candidate_id"] = harmonized_data["unified_pipeline"][0]["candidate_id"]
        result = json.loads(validate_harmonized_data(json.dumps(harmonized_data)))
        assert result["overall_status"] == "FAIL"

    def test_quality_score_range(self, harmonized_data):
        result = json.loads(validate_harmonized_data(json.dumps(harmonized_data)))
        assert 0 <= result["data_quality_score"] <= 100


class TestAnalyzePipelineStatistics:
    def test_returns_valid_json(self, harmonized_data):
        result = analyze_pipeline_statistics(json.dumps(harmonized_data))
        data = json.loads(result)
        assert "total_candidates" in data
        assert "by_company" in data
        assert "insights" in data

    def test_counts_match(self, harmonized_data):
        result = json.loads(analyze_pipeline_statistics(json.dumps(harmonized_data)))
        assert result["total_candidates"] == 4
        assert sum(result["by_company"].values()) == 4


# --- Agent task tests ---

class TestAgentTask:
    @patch("boto3.client")
    def test_agent_task_returns_response(self, mock_boto3_client):
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        mock_client.converse.return_value = {
            "output": {"message": {"role": "assistant", "content": [{"text": "Analysis complete."}]}},
            "stopReason": "end_turn",
        }

        result = agent_task("Analyze the pipeline data")
        assert result == "Analysis complete."
        mock_client.converse.assert_called_once()

    @patch("boto3.client")
    def test_agent_task_handles_tool_use(self, mock_boto3_client):
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        # First call returns tool_use, second returns final text
        mock_client.converse.side_effect = [
            {
                "output": {"message": {"role": "assistant", "content": [
                    {"toolUse": {"toolUseId": "id1", "name": "analyze_pipeline_statistics", "input": {"harmonized_data_json": '{"unified_pipeline": []}'}}}
                ]}},
                "stopReason": "tool_use",
            },
            {
                "output": {"message": {"role": "assistant", "content": [{"text": "Done."}]}},
                "stopReason": "end_turn",
            },
        ]

        result = agent_task("Analyze stats")
        assert result == "Done."
        assert mock_client.converse.call_count == 2

    def test_model_id_configured(self):
        assert MODEL_ID == "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
