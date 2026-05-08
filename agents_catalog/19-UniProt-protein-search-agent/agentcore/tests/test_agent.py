import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.agent import (
    search_proteins,
    get_protein_details,
    _construct_search_query,
    _search_uniprot_proteins,
    _get_protein_details,
    create_agent,
)


class TestConstructSearchQuery(unittest.TestCase):
    def test_single_term_human(self):
        q = _construct_search_query("BRCA1", "human")
        assert 'organism_name:"Homo sapiens"' in q
        assert 'protein_name:"BRCA1"' in q
        assert 'gene:"BRCA1"' in q

    def test_multi_term(self):
        q = _construct_search_query("tumor suppressor", "mouse")
        assert 'organism_name:"Mus musculus"' in q
        assert 'protein_name:"tumor suppressor"' in q
        assert "(tumor AND suppressor)" in q

    def test_custom_organism(self):
        q = _construct_search_query("insulin", "Danio rerio")
        assert 'organism_name:"Danio rerio"' in q


class TestSearchProteins(unittest.TestCase):
    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_successful_search(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "results": [{
                "primaryAccession": "P04637",
                "proteinDescription": {"recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}},
                "genes": [{"geneName": {"value": "TP53"}}],
                "organism": {"scientificName": "Homo sapiens"},
                "sequence": {"length": 393},
                "comments": [{"commentType": "FUNCTION", "texts": [{"value": "Acts as a tumor suppressor"}]}],
            }]
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = _search_uniprot_proteins('protein_name:"p53" AND organism_name:"Homo sapiens"', 10)
        assert "P04637" in result
        assert "TP53" in result
        assert "tumor suppressor" in result.lower()

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_no_results(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({"results": []}).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = _search_uniprot_proteins("nonexistent", 10)
        assert "No proteins found" in result

    @patch("agent.agent_config.agent._search_uniprot_proteins")
    def test_empty_query_returns_error(self, mock_search):
        # Call the decorated tool function directly
        result = search_proteins(query="  ", organism="human", limit=10)
        assert "Error" in result or "required" in result.lower()
        mock_search.assert_not_called()

    @patch("agent.agent_config.agent._search_uniprot_proteins")
    def test_limit_capped_at_50(self, mock_search):
        mock_search.return_value = "results"
        search_proteins(query="p53", organism="human", limit=100)
        # The limit passed to _search_uniprot_proteins should be capped at 50
        mock_search.assert_called_once()
        args = mock_search.call_args[0]
        assert args[1] == 50


class TestGetProteinDetails(unittest.TestCase):
    def test_invalid_accession(self):
        result = get_protein_details(accession_id="invalid!", include_sequence=False, include_features=True)
        assert "Invalid" in result or "Error" in result

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_successful_details(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "proteinDescription": {"recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}},
            "genes": [{"geneName": {"value": "TP53"}}],
            "organism": {"scientificName": "Homo sapiens"},
            "sequence": {"length": 393, "value": "MEEPQ" * 20},
            "comments": [
                {"commentType": "FUNCTION", "texts": [{"value": "Acts as a tumor suppressor"}]},
                {"commentType": "SUBCELLULAR_LOCATION", "subcellularLocations": [{"location": {"value": "Nucleus"}}]},
                {"commentType": "DISEASE", "disease": {"diseaseId": "Li-Fraumeni syndrome"}, "texts": [{"value": "Inherited cancer predisposition"}]},
            ],
            "features": [{"type": "Domain", "description": "Transactivation", "location": {"start": {"value": 1}, "end": {"value": 40}}}],
            "uniProtKBCrossReferences": [{"database": "PDB", "id": "1TUP"}],
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = _get_protein_details("P04637", False, True)
        assert "Cellular tumor antigen p53" in result
        assert "TP53" in result
        assert "Nucleus" in result
        assert "Li-Fraumeni" in result
        assert "1TUP" in result

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_include_sequence(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = json.dumps({
            "proteinDescription": {"recommendedName": {"fullName": {"value": "Test"}}},
            "genes": [],
            "organism": {"scientificName": "Homo sapiens"},
            "sequence": {"length": 100, "value": "ACDEFGHIKLMNPQRSTVWY" * 5},
            "comments": [],
            "features": [],
            "uniProtKBCrossReferences": [],
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = _get_protein_details("P12345", True, False)
        assert "SEQUENCE:" in result

    @patch("agent.agent_config.agent.urllib.request.urlopen")
    def test_404_not_found(self, mock_urlopen):
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            url="http://test", code=404, msg="Not Found", hdrs={}, fp=None
        )
        result = _get_protein_details("ZZZZZZ", False, False)
        assert "not found" in result.lower()


class TestCreateAgent(unittest.TestCase):
    @patch("agent.agent_config.agent.BedrockModel")
    @patch("agent.agent_config.agent.Agent")
    def test_creates_agent(self, mock_agent_cls, mock_model_cls):
        mock_model_cls.return_value = MagicMock()
        mock_agent_cls.return_value = MagicMock()
        agent = create_agent()
        mock_model_cls.assert_called_once_with(
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            streaming=True,
        )
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args[1]
        assert len(call_kwargs["tools"]) == 2


if __name__ == "__main__":
    unittest.main()
