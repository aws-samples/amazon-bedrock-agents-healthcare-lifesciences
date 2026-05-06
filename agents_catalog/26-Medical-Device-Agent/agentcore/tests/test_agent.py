"""Tests for Medical Device Coordinator agent."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTools:
    def test_list_all_devices(self):
        from agent.agent_config.tools.device_status import list_all_devices
        result = list_all_devices()
        assert "DEV001" in result
        assert "MRI Scanner" in result

    def test_get_device_status(self):
        from agent.agent_config.tools.device_status import get_device_status
        result = get_device_status(device_id="DEV001")
        assert "Operational" in result

    def test_get_device_not_found(self):
        from agent.agent_config.tools.device_status import get_device_status
        result = get_device_status(device_id="INVALID")
        assert "not found" in result


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
