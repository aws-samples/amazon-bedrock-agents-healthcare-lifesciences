"""Tear down the oncology-hub-data MCP server: AgentCore runtime + endpoint, IAM role/policy, and this
server's SSM params. Does NOT touch the OLS Cognito (owned by the ontology-lookup-service component).

Usage: python cleanup.py [--region us-west-2]   (reads runtime_config.json written by deploy.py)
"""
import argparse
import json
from pathlib import Path

import boto3

_DIR = Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("--region", default=None)
args = ap.parse_args()

cfg_path = _DIR / "runtime_config.json"
if not cfg_path.exists():
    raise SystemExit("runtime_config.json not found — nothing to clean up (deploy.py writes it).")
cfg = json.loads(cfg_path.read_text())
REGION = args.region or cfg.get("region", "us-west-2")
agent_id = cfg["agent_id"]
role_name = cfg["role_arn"].split("/")[-1]

ctrl = boto3.client("bedrock-agentcore-control", region_name=REGION)
iam = boto3.client("iam", region_name=REGION)
ssm = boto3.client("ssm", region_name=REGION)


def _try(desc, fn):
    try:
        fn()
        print(f"  ok: {desc}")
    except Exception as e:  # noqa: BLE001
        print(f"  skip: {desc} ({e.__class__.__name__})")


print(f"Cleaning up {agent_id} in {REGION}")
# Endpoints then runtime.
try:
    for ep in ctrl.list_agent_runtime_endpoints(agentRuntimeId=agent_id).get("runtimeEndpoints", []):
        _try(f"delete endpoint {ep.get('name')}",
             lambda ep=ep: ctrl.delete_agent_runtime_endpoint(agentRuntimeId=agent_id, endpointName=ep["name"]))
except Exception as e:  # noqa: BLE001
    print(f"  skip: list endpoints ({e.__class__.__name__})")
_try("delete agent runtime", lambda: ctrl.delete_agent_runtime(agentRuntimeId=agent_id))

# IAM inline policy + role.
for pol in (f"{role_name.rsplit('_role', 1)[0]}_policy", "policy"):
    _try(f"delete role policy {pol}", lambda pol=pol: iam.delete_role_policy(RoleName=role_name, PolicyName=pol))
_try("delete role", lambda: iam.delete_role(RoleName=role_name))

# SSM params (this server only).
for k in ("mcp_url", "agent_arn", "agent_id"):
    _try(f"delete SSM /app/oncology-hub-data/agentcore/{k}",
         lambda k=k: ssm.delete_parameter(Name=f"/app/oncology-hub-data/agentcore/{k}"))

print("Done. (OLS Cognito left intact — it is owned by the ontology-lookup-service component.)")
