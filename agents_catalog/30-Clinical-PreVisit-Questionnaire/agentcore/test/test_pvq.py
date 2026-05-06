"""Tests for Clinical PreVisit Questionnaire AgentCore agent."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestDataModels:
    """Test PVQ data models."""

    def test_pvq_data_initializes(self):
        from models.patient_data import PVQData

        data = PVQData()
        assert data.patient_name == ""
        assert isinstance(data.current_medications, list)
        assert len(data.current_medications) == 0

    def test_completion_status(self):
        from models.patient_data import PVQData

        data = PVQData()
        status = data.get_completion_status()
        assert not status["basic_info"]
        assert not status["has_medical_history"]

    def test_medical_categories(self):
        from models.patient_data import MedicalConditionCategories

        assert hasattr(MedicalConditionCategories, "EYE_EAR")
        assert hasattr(MedicalConditionCategories, "LUNGS")
        assert len(MedicalConditionCategories.EYE_EAR) > 0


class TestAgentCreation:
    """Test agent instantiation."""

    def test_pvq_agent_creates(self):
        from agents.pvq_agent import PVQStrandsAgent

        agent = PVQStrandsAgent()
        assert agent.agent is not None
        assert agent.pvq_data is not None

    def test_fast_agent_creates(self):
        from agents.pvq_agent_fast import FastPVQAgent

        agent = FastPVQAgent()
        assert agent.agent is not None


class TestModelConfig:
    """Test model configuration."""

    def test_model_ids_are_current(self):
        from model.load import MODEL_ID, FAST_MODEL_ID

        assert "claude-sonnet-4-5" in MODEL_ID
        assert "claude-haiku-4-5" in FAST_MODEL_ID


@pytest.mark.integration
class TestLiveInvocation:
    """Integration tests requiring AWS credentials."""

    def test_agent_responds(self):
        from agents.pvq_agent import PVQStrandsAgent

        agent = PVQStrandsAgent()
        response = agent.chat("Hello, I need to fill out my pre-visit form")
        assert response is not None
        assert len(response) > 0
        assert "Error" not in response
