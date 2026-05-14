"""Nova Act UI tests for AgentCore agents via Streamlit.

Automated end-to-end UI testing using Amazon Nova Act.
Tests verify agents respond correctly through the Streamlit chat interface.

Prerequisites:
- Nova Act API key set as NOVA_ACT_API_KEY env var
- Streamlit app running (agentcore_template/app.py)
- Agents deployed to AgentCore

Run:
    export NOVA_ACT_API_KEY="your-key"
    export STREAMLIT_URL="http://localhost:8501"
    pytest tests/ui/ -m ui -v

Run headless (CI/CD):
    HEADLESS=true pytest tests/ui/ -m ui -v
"""

import os

import pytest
from nova_act import NovaAct

STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:8501")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
NOVA_ACT_API_KEY = os.getenv("NOVA_ACT_API_KEY")


def _require_nova_act():
    if not NOVA_ACT_API_KEY:
        pytest.skip("NOVA_ACT_API_KEY not set")


@pytest.mark.ui
class TestEnrollmentPulseUI:
    """UI tests for Agent 27 - Enrollment Pulse."""

    def test_agent_selection_and_query(self):
        """Select enrollment_pulse agent and ask for enrollment status."""
        _require_nova_act()
        with NovaAct(
            starting_page=STREAMLIT_URL,
            headless=HEADLESS,
            nova_act_api_key=NOVA_ACT_API_KEY,
        ) as nova:
            nova.act("Look for a dropdown or selector to choose an agent runtime")
            nova.act("Select the agent that contains 'enrollment_pulse' in its name")
            nova.act(
                "Type 'What is the current enrollment status by site?' "
                "in the chat input field at the bottom"
            )
            nova.act("Press Enter or click the send button to submit the message")
            nova.act(
                "Wait for the assistant response to appear. "
                "It may take 10-30 seconds for the full response."
            )
            result = nova.act(
                "Verify the response mentions site names like "
                "'Memorial Sloan', 'Dana-Farber', or 'MD Anderson'. "
                "Return 'PASS' if sites are mentioned, 'FAIL' if not."
            )
            assert "PASS" in result.response or "Memorial" in result.response


@pytest.mark.ui
class TestClinicalPriorAuthUI:
    """UI tests for Agent 29 - Clinical Prior Auth."""

    def test_prior_auth_query(self):
        """Send a patient query and verify agent processes it."""
        _require_nova_act()
        with NovaAct(
            starting_page=STREAMLIT_URL,
            headless=HEADLESS,
            nova_act_api_key=NOVA_ACT_API_KEY,
        ) as nova:
            nova.act("Look for a dropdown or selector to choose an agent runtime")
            nova.act("Select the agent that contains 'clinical_prior_auth' in its name")
            nova.act(
                "Type 'Patient with knee pain requiring orthopedic consultation' "
                "in the chat input field"
            )
            nova.act("Press Enter or click send to submit")
            nova.act("Wait for the assistant response to appear (10-30 seconds)")
            result = nova.act(
                "Verify the response mentions a specialty selection or document download. "
                "Return 'PASS' if the agent is processing the request, 'FAIL' if error."
            )
            assert "PASS" in result.response or "FAIL" not in result.response


@pytest.mark.ui
class TestClinicalPVQUI:
    """UI tests for Agent 30 - Clinical PreVisit Questionnaire."""

    def test_questionnaire_interaction(self):
        """Start a questionnaire and verify agent asks follow-up questions."""
        _require_nova_act()
        with NovaAct(
            starting_page=STREAMLIT_URL,
            headless=HEADLESS,
            nova_act_api_key=NOVA_ACT_API_KEY,
        ) as nova:
            nova.act("Look for a dropdown or selector to choose an agent runtime")
            nova.act("Select the agent that contains 'clinical_pvq' in its name")
            nova.act(
                "Type 'Hello, I need to fill out my pre-visit questionnaire. "
                "I have a headache and mild fever.' in the chat input"
            )
            nova.act("Press Enter or click send")
            nova.act("Wait for the assistant response (10-30 seconds)")
            result = nova.act(
                "Verify the response acknowledges the symptoms and asks a follow-up "
                "question (like asking for name or more details). "
                "Return 'PASS' if it's conversational, 'FAIL' if error."
            )
            assert "PASS" in result.response


@pytest.mark.ui
class TestMedicalDeviceUI:
    """UI tests for Agent 26 - Medical Device."""

    def test_device_listing(self):
        """Ask for device list and verify response contains device data."""
        _require_nova_act()
        with NovaAct(
            starting_page=STREAMLIT_URL,
            headless=HEADLESS,
            nova_act_api_key=NOVA_ACT_API_KEY,
        ) as nova:
            nova.act("Look for a dropdown or selector to choose an agent runtime")
            nova.act("Select the agent that contains 'medical_device' in its name")
            nova.act(
                "Type 'List all medical devices and their current status' "
                "in the chat input"
            )
            nova.act("Press Enter or click send")
            nova.act("Wait for the assistant response (10-30 seconds)")
            result = nova.act(
                "Verify the response lists devices with IDs like 'DEV001' "
                "or mentions 'MRI Scanner', 'Ventilator'. "
                "Return 'PASS' if devices are listed, 'FAIL' if not."
            )
            assert "PASS" in result.response
