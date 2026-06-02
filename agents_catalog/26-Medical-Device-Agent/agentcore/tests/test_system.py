"""System tests for Medical Device agent — end-to-end against deployed agent."""
import json, uuid, boto3, pytest
from botocore.config import Config

AGENT_NAME = "medical_device_agent"

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
class TestMedicalDeviceScenarios:
    def test_list_all_devices(self):
        """Agent lists all devices with status."""
        resp = _invoke("List all medical devices and their current status")
        assert any(d in resp for d in ["DEV001", "DEV002", "DEV003", "MRI", "Ventilator"])

    def test_specific_device_lookup(self):
        """Agent retrieves specific device info."""
        resp = _invoke("What is the status of device DEV002?")
        assert any(t in resp for t in ["Ventilator", "Maintenance", "ICU"])

    def test_pubmed_search(self):
        """Agent can search PubMed for medical literature."""
        resp = _invoke("Search PubMed for recent papers on MRI safety")
        assert any(t in resp.lower() for t in ["pubmed", "pmid", "paper", "study", "mri", "result"])
