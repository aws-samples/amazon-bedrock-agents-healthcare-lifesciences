"""System tests for Clinical PVQ agent — end-to-end against deployed agent."""
import json, uuid, boto3, pytest
from botocore.config import Config

AGENT_NAME = "clinical_pvq"

def _invoke(prompt, timeout=120):
    config = Config(read_timeout=timeout)
    ctrl = boto3.client("bedrock-agentcore-control")
    rt = boto3.client("bedrock-agentcore", config=config)
    resp = ctrl.list_agent_runtimes(maxResults=100)
    arn = next((r["agentRuntimeArn"] for r in resp.get("agentRuntimes", []) if r["agentRuntimeName"] == AGENT_NAME), None)
    if not arn: pytest.skip(f"Agent '{AGENT_NAME}' not deployed")
    r = rt.invoke_agent_runtime(agentRuntimeArn=arn, runtimeSessionId=str(uuid.uuid4()), payload=json.dumps({"message": prompt}).encode())
    content = []
    try:
        for chunk in r.get("response", []): content.append(chunk.decode("utf-8"))
    except Exception: pass
    return "".join(content)

@pytest.mark.system
class TestPVQScenarios:
    def test_questionnaire_start(self):
        """Agent acknowledges symptoms and begins questionnaire."""
        resp = _invoke("Hello, I need to fill out my pre-visit questionnaire. I have a headache.")
        assert len(resp) > 20
        assert any(t in resp.lower() for t in ["headache", "name", "questionnaire", "help", "record"])

    def test_full_data_submission(self):
        """Agent processes complete patient data in one message."""
        resp = _invoke("My name is Jane Doe, DOB 03/15/1985. I have asthma and take albuterol. No allergies. Non-smoker. Please save and summarize.")
        assert any(t in resp.lower() for t in ["jane", "asthma", "albuterol", "saved", "summary", "record"])

    def test_medication_recording(self):
        """Agent records medication information."""
        resp = _invoke("I take lisinopril 10mg daily for blood pressure and metformin 500mg twice daily for diabetes.")
        assert any(t in resp.lower() for t in ["lisinopril", "metformin", "medication", "saved", "record"])
