"""Tests for PVQ agent."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataModels:
    def test_pvq_data_initializes(self):
        from agent.models.patient_data import PVQData
        data = PVQData()
        assert data.patient_name == ""

    def test_medical_categories(self):
        from agent.models.patient_data import MedicalConditionCategories
        assert hasattr(MedicalConditionCategories, "EYE_EAR")


class TestAgentCreation:
    def test_pvq_agent_creates(self):
        from agent.agent_config.pvq_agent import PVQStrandsAgent
        agent = PVQStrandsAgent()
        assert agent.agent is not None

    def test_fast_agent_creates(self):
        from agent.agent_config.pvq_agent_fast import FastPVQAgent
        agent = FastPVQAgent()
        assert agent.agent is not None


class TestModelConfig:
    def test_model_ids(self):
        from agent.agent_config.agent import MODEL_ID, FAST_MODEL_ID
        assert "claude-sonnet-4-5" in MODEL_ID
        assert "claude-haiku-4-5" in FAST_MODEL_ID


@pytest.mark.integration
class TestLiveInvocation:
    def test_agent_responds(self):
        from agent.agent_config.pvq_agent import PVQStrandsAgent
        agent = PVQStrandsAgent()
        response = agent.chat("Hello, I need to fill out my form")
        assert response and len(response) > 0
