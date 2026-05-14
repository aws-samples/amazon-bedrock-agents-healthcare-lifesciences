"""Tests for Medical Device Coordinator agent.

All tests automated via pytest. No manual steps required.
Run: pytest tests/ -m "not integration"
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDeviceTools:
    """Test device status tools with SQLite data."""

    def test_list_all_devices_returns_data(self):
        from agent.agent_config.tools.device_status import list_all_devices
        result = list_all_devices()
        assert "DEV001" in result
        assert "DEV002" in result
        assert "DEV003" in result

    def test_list_devices_includes_types(self):
        from agent.agent_config.tools.device_status import list_all_devices
        result = list_all_devices()
        assert "Imaging" in result
        assert "Life Support" in result

    def test_get_device_status_valid(self):
        from agent.agent_config.tools.device_status import get_device_status
        result = get_device_status(device_id="DEV001")
        assert "MRI Scanner" in result
        assert "Operational" in result
        assert "Room 101" in result

    def test_get_device_status_maintenance_required(self):
        from agent.agent_config.tools.device_status import get_device_status
        result = get_device_status(device_id="DEV002")
        assert "Ventilator" in result
        assert "Maintenance Required" in result

    def test_get_device_not_found(self):
        from agent.agent_config.tools.device_status import get_device_status
        result = get_device_status(device_id="INVALID_ID")
        assert "not found" in result

    def test_html_in_device_id_handled(self):
        """Device ID with special chars returns not found."""
        from agent.agent_config.tools.device_status import get_device_status
        result = get_device_status(device_id="<script>alert('xss')</script>")
        assert "not found" in result


class TestClinicalTrialsTools:
    """Test clinical trials API tool."""

    def test_search_returns_string(self):
        from agent.agent_config.tools.clinical_trials import search_clinical_trials
        result = search_clinical_trials(condition="diabetes", max_results=2)
        # Should return results or a "no results" message
        assert isinstance(result, str)
        assert len(result) > 0


class TestPubMedTools:
    """Test PubMed search tool."""

    def test_search_returns_string(self):
        from agent.agent_config.tools.pubmed_search import search_pubmed
        result = search_pubmed(query="MRI safety", max_results=2)
        assert isinstance(result, str)
        assert len(result) > 0


class TestModelConfig:
    def test_model_id_is_current(self):
        from agent.agent_config.agent import MODEL_ID
        assert "claude-sonnet-4-5" in MODEL_ID
        assert "20250929" in MODEL_ID


class TestAgentConfig:
    def test_system_prompt_covers_capabilities(self):
        from agent.agent_config.agent import SYSTEM_PROMPT
        assert "Medical Device" in SYSTEM_PROMPT or "medical device" in SYSTEM_PROMPT
        assert "PubMed" in SYSTEM_PROMPT
        assert "Clinical trials" in SYSTEM_PROMPT or "clinical trials" in SYSTEM_PROMPT

    def test_all_tools_registered(self):
        from agent.agent_config.agent import ALL_TOOLS
        assert len(ALL_TOOLS) == 4


@pytest.mark.integration
class TestLiveInvocation:
    def test_model_responds(self):
        from strands import Agent
        from strands.models import BedrockModel
        from agent.agent_config.agent import MODEL_ID
        agent = Agent(model=BedrockModel(model_id=MODEL_ID), system_prompt="Reply: OK", tools=[])
        result = agent("Hello")
        assert result.message is not None

    def test_agent_with_device_tools(self):
        """Full agent can use device tools."""
        from strands import Agent
        from strands.models import BedrockModel
        from agent.agent_config.agent import MODEL_ID, ALL_TOOLS
        agent = Agent(
            model=BedrockModel(model_id=MODEL_ID),
            system_prompt="You manage medical devices. Use tools to answer.",
            tools=ALL_TOOLS[:2],  # device tools only
        )
        result = agent("List all devices")
        assert result.message is not None
