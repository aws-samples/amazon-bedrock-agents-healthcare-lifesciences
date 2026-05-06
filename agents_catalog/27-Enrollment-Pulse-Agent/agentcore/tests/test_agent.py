"""Tests for Enrollment Pulse agent."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataProcessors:
    def test_ctms_processor_loads(self):
        from agent.data.processors import CTMSDataProcessor

        processor = CTMSDataProcessor()
        processor.load_csv_files()
        studies = processor.process_studies()
        assert len(studies) > 0

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
    def test_get_overall_enrollment_status(self):
        from agent.agent_config.tools import get_overall_enrollment_status

        result = get_overall_enrollment_status()
        assert isinstance(result, dict)

    def test_get_epidemiology_overview(self):
        from agent.agent_config.epidemiology_tools import get_epidemiology_overview

        result = get_epidemiology_overview()
        assert result is not None


class TestModelConfig:
    def test_model_id_is_current(self):
        from agent.agent_config.agent import MODEL_ID

        assert "claude-sonnet-4-5" in MODEL_ID


@pytest.mark.integration
class TestLiveInvocation:
    def test_model_responds(self):
        from strands import Agent
        from strands.models import BedrockModel
        from agent.agent_config.agent import MODEL_ID

        agent = Agent(model=BedrockModel(model_id=MODEL_ID), system_prompt="Reply: OK", tools=[])
        result = agent("Hello")
        assert result.message is not None
