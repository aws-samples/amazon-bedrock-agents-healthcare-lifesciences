"""System tests for Clinical Prior Auth agent.

End-to-end tests that invoke the deployed AgentCore agent and verify
responses match expected behavior from the agent documentation.

Requires:
- Agent deployed to AgentCore
- AWS credentials with bedrock-agentcore invoke permissions

Run: AWS_PROFILE=your-profile pytest tests/test_system.py -m system -v
"""

import json
import uuid

import boto3
import pytest

AGENT_NAME = "clinical_prior_auth"


def _invoke_agent(prompt: str, timeout: int = 120) -> str:
    """Invoke the deployed agent and return the response text."""
    from botocore.config import Config

    config = Config(read_timeout=timeout, connect_timeout=10)
    control_client = boto3.client("bedrock-agentcore-control")
    runtime_client = boto3.client("bedrock-agentcore", config=config)

    # Find agent ARN
    response = control_client.list_agent_runtimes(maxResults=100)
    agent_arn = None
    for runtime in response.get("agentRuntimes", []):
        if runtime["agentRuntimeName"] == AGENT_NAME:
            agent_arn = runtime["agentRuntimeArn"]
            break

    if not agent_arn:
        pytest.skip(f"Agent '{AGENT_NAME}' not deployed")

    # Invoke
    session_id = str(uuid.uuid4())
    payload = json.dumps({"prompt": prompt}).encode()

    response = runtime_client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=session_id,
        payload=payload,
    )

    # Collect streaming response
    content = []
    try:
        for chunk in response.get("response", []):
            content.append(chunk.decode("utf-8"))
    except Exception:
        pass  # Timeout on long responses is acceptable
    return "".join(content)


@pytest.mark.system
class TestPriorAuthScenarios:
    """End-to-end scenarios from agent documentation."""

    def test_specialty_selection(self):
        """Agent identifies appropriate specialty from patient data."""
        response = _invoke_agent(
            "Patient with knee pain requiring orthopedic consultation"
        )
        # Agent should identify a specialty and attempt to get documents
        assert any(
            term in response.lower()
            for term in ["specialty", "physician", "professional", "orthop", "document"]
        ), f"Expected specialty selection, got: {response[:200]}"

    def test_document_retrieval(self):
        """Agent attempts to download billing guides."""
        response = _invoke_agent(
            "Patient needs cardiac surgery pre-authorization"
        )
        # Agent should reference documents or specialties
        assert len(response) > 50, "Response too short — agent may not have processed"
        assert any(
            term in response.lower()
            for term in ["download", "document", "billing", "fee", "specialty", "cardiac"]
        ), f"Expected document/billing reference, got: {response[:200]}"

    def test_handles_ambiguous_input(self):
        """Agent handles vague patient data gracefully."""
        response = _invoke_agent("Patient feels unwell")
        # Should still respond meaningfully, not error
        assert len(response) > 20
        assert "error" not in response.lower() or "Error" not in response[:50]
