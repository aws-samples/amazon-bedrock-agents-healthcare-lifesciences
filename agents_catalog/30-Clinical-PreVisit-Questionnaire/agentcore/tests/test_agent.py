"""Tests for Clinical PreVisit Questionnaire agent.

All tests automated via pytest. No manual steps required.
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataModels:
    """Test patient data models."""

    def test_pvq_data_initializes_empty(self):
        from agent.models.patient_data import PVQData
        data = PVQData()
        assert data.patient_name == ""
        assert isinstance(data.current_medications, list)
        assert len(data.current_medications) == 0

    def test_completion_status_initially_incomplete(self):
        from agent.models.patient_data import PVQData
        data = PVQData()
        status = data.get_completion_status()
        assert not status["basic_info"]
        assert not status["has_medical_history"]

    def test_medical_categories_defined(self):
        from agent.models.patient_data import MedicalConditionCategories
        assert hasattr(MedicalConditionCategories, "EYE_EAR")
        assert hasattr(MedicalConditionCategories, "LUNGS")
        assert hasattr(MedicalConditionCategories, "HEART")
        assert len(MedicalConditionCategories.EYE_EAR) > 0


class TestAgentCreation:
    """Test agent instantiation with tools."""

    def test_pvq_agent_creates_with_tools(self):
        from agent.agent_config.pvq_agent import PVQStrandsAgent
        agent = PVQStrandsAgent()
        assert agent.agent is not None
        assert agent.pvq_data is not None
        assert agent.basic_info is not None
        assert agent.medical_history is not None

    def test_fast_agent_creates(self):
        from agent.agent_config.pvq_agent_fast import FastPVQAgent
        agent = FastPVQAgent()
        assert agent.agent is not None

    def test_pvq_agent_handles_quit(self):
        from agent.agent_config.pvq_agent import PVQStrandsAgent
        agent = PVQStrandsAgent()
        response = agent.chat("quit")
        assert "Saved" in response or "Thank you" in response


class TestToolFunctionality:
    """Test tool classes work correctly."""

    def test_basic_info_tools_exist(self):
        from agent.agent_config.pvq_agent import PVQStrandsAgent
        agent = PVQStrandsAgent()
        assert hasattr(agent.basic_info, "save_basic_info")

    def test_medical_history_tools_exist(self):
        from agent.agent_config.pvq_agent import PVQStrandsAgent
        agent = PVQStrandsAgent()
        assert hasattr(agent.medical_history, "save_medical_condition")
        assert hasattr(agent.medical_history, "save_surgery")

    def test_utilities_progress(self):
        from agent.agent_config.pvq_agent import PVQStrandsAgent
        agent = PVQStrandsAgent()
        progress = agent.utilities.get_progress()
        assert "progress" in progress.lower() or "%" in progress or "complete" in progress.lower()


class TestModelConfig:
    def test_model_ids_are_current(self):
        from agent.agent_config.agent import MODEL_ID, FAST_MODEL_ID
        assert "claude-sonnet-4-5" in MODEL_ID
        assert "claude-haiku-4-5" in FAST_MODEL_ID


@pytest.mark.integration
class TestLiveInvocation:
    def test_agent_responds_to_greeting(self):
        from agent.agent_config.pvq_agent import PVQStrandsAgent
        agent = PVQStrandsAgent()
        response = agent.chat("Hello, I need to fill out my pre-visit form")
        assert response is not None
        assert len(response) > 0
        assert "Error" not in response

    def test_agent_saves_medical_condition(self):
        """Agent can process and save a medical condition."""
        from agent.agent_config.pvq_agent import PVQStrandsAgent
        agent = PVQStrandsAgent()
        response = agent.chat("I have diabetes and high blood pressure")
        assert response is not None
        assert len(response) > 0
