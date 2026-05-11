"""Tests for Enrollment Pulse agent.

All tests automated via pytest. No manual steps required.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataProcessors:
    """Test CTMS data loading and processing."""

    def test_ctms_processor_loads_csv_files(self):
        from agent.data.processors import CTMSDataProcessor
        processor = CTMSDataProcessor()
        processor.load_csv_files()
        studies = processor.process_studies()
        assert len(studies) > 0

    def test_ctms_processor_has_sites(self):
        from agent.data.processors import CTMSDataProcessor
        processor = CTMSDataProcessor()
        processor.load_csv_files()
        sites = processor.process_sites()
        assert len(sites) >= 5  # 5 cancer centers

    def test_epidemiology_processor_loads(self):
        from agent.data.epidemiology_processor import EpidemiologyProcessor
        processor = EpidemiologyProcessor()
        df = processor.load_data()
        assert len(df) > 0

    def test_clinical_trials_processor_loads(self):
        from agent.data.clinical_trials_processor import ClinicalTrialsProcessor
        processor = ClinicalTrialsProcessor()
        df = processor.load_data()
        assert len(df) > 0


class TestTools:
    """Test agent tools return valid enrollment data."""

    def test_overall_enrollment_status(self):
        from agent.agent_config.tools import get_overall_enrollment_status
        result = get_overall_enrollment_status()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_site_performance_ranking(self):
        from agent.agent_config.tools import get_site_performance_ranking
        result = get_site_performance_ranking()
        assert isinstance(result, (dict, list))

    def test_identify_underperforming_sites(self):
        from agent.agent_config.tools import identify_underperforming_sites
        result = identify_underperforming_sites()
        assert result is not None

    def test_epidemiology_overview(self):
        from agent.agent_config.epidemiology_tools import get_epidemiology_overview
        result = get_epidemiology_overview()
        assert result is not None

    def test_clinical_trials_landscape(self):
        from agent.agent_config.clinical_trials_tools import get_clinical_trials_landscape
        result = get_clinical_trials_landscape()
        assert result is not None


class TestModelConfig:
    def test_model_id_is_current(self):
        from agent.agent_config.agent import MODEL_ID
        assert "claude-sonnet-4-5" in MODEL_ID
        assert "20250929" in MODEL_ID

    def test_all_tools_registered(self):
        from agent.agent_config.agent import ALL_TOOLS
        assert len(ALL_TOOLS) >= 30  # 40+ tools


class TestSystemPrompt:
    def test_prompt_mentions_site_level(self):
        from agent.agent_config.agent import SYSTEM_PROMPT
        assert "site" in SYSTEM_PROMPT.lower()


@pytest.mark.integration
class TestLiveInvocation:
    def test_model_responds(self):
        from strands import Agent
        from strands.models import BedrockModel
        from agent.agent_config.agent import MODEL_ID
        agent = Agent(model=BedrockModel(model_id=MODEL_ID), system_prompt="Reply: OK", tools=[])
        result = agent("Hello")
        assert result.message is not None
