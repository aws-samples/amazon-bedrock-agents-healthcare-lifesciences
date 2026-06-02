"""System tests for Enrollment Pulse agent — end-to-end against deployed agent."""
import json, uuid, boto3, pytest
from botocore.config import Config

AGENT_NAME = "enrollment_pulse"

def _invoke(prompt, timeout=120):
    config = Config(read_timeout=timeout)
    ctrl = boto3.client("bedrock-agentcore-control")
    rt = boto3.client("bedrock-agentcore", config=config)
    resp = ctrl.list_agent_runtimes(maxResults=100)
    arn = next((r["agentRuntimeArn"] for r in resp.get("agentRuntimes", []) if r["agentRuntimeName"] == AGENT_NAME), None)
    if not arn: pytest.skip(f"Agent '{AGENT_NAME}' not deployed")
    r = rt.invoke_agent_runtime(agentRuntimeArn=arn, runtimeSessionId=str(uuid.uuid4()), payload=json.dumps({"prompt": prompt}).encode())
    content = []
    try:
        for chunk in r.get("response", []): content.append(chunk.decode("utf-8"))
    except Exception: pass
    return "".join(content)

@pytest.mark.system
class TestEnrollmentScenarios:
    def test_enrollment_status_by_site(self):
        """Agent returns site-level enrollment data."""
        resp = _invoke("What is the current enrollment status by site?")
        assert any(s in resp for s in ["Memorial", "Dana-Farber", "MD Anderson", "UCLA", "Mayo"]), f"No sites found: {resp[:200]}"

    def test_underperforming_sites(self):
        """Agent identifies underperforming sites."""
        resp = _invoke("Which sites are underperforming?")
        assert any(t in resp.lower() for t in ["underperform", "behind", "critical", "ucla", "mayo"]), f"No underperformers: {resp[:200]}"

    def test_site_recommendations(self):
        """Agent provides actionable recommendations."""
        resp = _invoke("What interventions do you recommend for the lowest performing site?")
        assert len(resp) > 100, "Response too short"
        assert any(t in resp.lower() for t in ["recommend", "intervention", "action", "site visit", "specialist"])
