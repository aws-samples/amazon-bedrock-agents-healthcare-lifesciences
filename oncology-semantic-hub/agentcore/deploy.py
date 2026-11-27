"""Deploy the Oncology Semantic Hub agent to Bedrock AgentCore Runtime.

Adapted from 06-observe-evaluate-optimize-your-agent/02-evaluate/utils/deploy.py. Packages
semantic_hub_agent.py + ARM64 deps, creates an IAM execution role scoped for the hub's data
access (Neptune / Athena / Glue / S3 / SSM / Bedrock), creates the Runtime with OTel
instrumentation, polls READY, and writes agent_config.json (used by run_agentcore_eval.py).

Usage: python deploy.py [--region us-west-2]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path

import boto3
from boto3.session import Session

_DIR = Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("--region", default=None)
ap.add_argument("--layer", default="L3", choices=["L0", "L0-web", "L1", "L2", "L3", "L3a", "L3b", "L3_no_graph", "L3_no_ols", "L3_no_kb"])
ap.add_argument("--suffix", default="")
args = ap.parse_args()
REGION = args.region or Session().region_name or "us-west-2"
LAYER = args.layer
SUFFIX = ("_" + args.suffix) if args.suffix else ""
_CONFIG = _DIR / (f"agent_config_{LAYER.lower()}{SUFFIX}.json" if (LAYER != "L3" or SUFFIX) else "agent_config.json")
print(f"Region: {REGION}  Layer: {LAYER}")

acct = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
iam = boto3.client("iam", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
ctrl = boto3.client("bedrock-agentcore-control", region_name=REGION)

NAME = f"oncology_semantic_hub_{LAYER.lower().replace(chr(45),chr(95))}{SUFFIX}_{uuid.uuid4().hex[:8]}"
ROLE = f"{NAME}_role"
BUCKET = f"bedrock-agentcore-code-{acct}-{REGION}"
KEY = f"{NAME}/deployment_package.zip"
BUILD = Path(f"/tmp/{NAME}_build")  # nosec B108

TRUST = json.dumps({"Version": "2012-10-17", "Statement": [{
    "Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"aws:SourceAccount": acct},
                  "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:*:{acct}:runtime/*"}}}]})

# IAM least-privilege (Holmes CSR finding #2): split the policy so the resource-scopeable actions are
# pinned to specific ARNs, and only the actions that are not cleanly ARN-scopeable (or whose resource
# is not known until runtime) keep "*", with a documented reason.
#   - Bedrock model invoke/retrieve: scoped to foundation-model + KB ARNs in this account/region.
#   - S3: scoped to the data bucket (lake + athena-results) and the agentcore code bucket.
#   - Athena/Glue/Neptune/CloudWatch/X-Ray: kept "*" — Athena workgroup + Glue catalog + the
#     neptune-graph id are injected at runtime (SEMHUB_*), and logs/metrics/traces are account-wide
#     by nature. These are read-or-telemetry actions, not data mutations.
_DATA_BUCKET = os.environ.get(
    "SEMHUB_DATA_BUCKET", f"oncology-semantic-hub-data-{acct}-{REGION}")
_SCOPED_S3 = [f"arn:aws:s3:::{_DATA_BUCKET}", f"arn:aws:s3:::{_DATA_BUCKET}/*",
              f"arn:aws:s3:::{BUCKET}", f"arn:aws:s3:::{BUCKET}/*"]
# Cross-region inference profiles (model id prefix "us."/"eu."/"apac.") dispatch InvokeModel* to a
# foundation-model ARN in whichever underlying region AWS currently routes to for that profile — NOT
# necessarily the deploy region. Scoping foundation-model to just {REGION} breaks those profiles
# (verified live: a us-east-1 deploy of "us.anthropic.claude-sonnet-4-5..." resolved to a us-east-2
# foundation-model ARN and was denied). Wildcard the region component for the foundation-model
# resource; still scoped to this account for everything else.
_FOUNDATION_MODEL_RESOURCE = "arn:aws:bedrock:*::foundation-model/*"
_BEDROCK_RESOURCES = [
    _FOUNDATION_MODEL_RESOURCE,
    f"arn:aws:bedrock:*:{acct}:inference-profile/*",
    f"arn:aws:bedrock:{REGION}:{acct}:knowledge-base/*",
]
_WILDCARD_ACTIONS = [
    "neptune-graph:ReadDataViaQuery", "neptune-graph:GetGraph", "neptune-graph:GetGraphSummary",
    "athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults",
    "glue:GetTable", "glue:GetTables", "glue:GetDatabase", "glue:GetPartitions", "glue:GetPartition", "glue:BatchGetPartition",
    "ssm:GetParameter", "ssm:GetParameters",
    "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
    "logs:DescribeLogGroups", "logs:DescribeLogStreams",
    "xray:PutTraceSegments", "xray:PutTelemetryRecords",
    "xray:GetSamplingRules", "xray:GetSamplingTargets", "cloudwatch:PutMetricData",
]
_BEDROCK_ACTIONS = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
if LAYER == "L2" or LAYER.startswith("L3"):
    _BEDROCK_ACTIONS.append("bedrock:Retrieve")
POLICY = json.dumps({"Version": "2012-10-17", "Statement": [
    {"Sid": "BedrockScoped", "Effect": "Allow", "Action": _BEDROCK_ACTIONS, "Resource": _BEDROCK_RESOURCES},
    {"Sid": "S3Scoped", "Effect": "Allow",
     "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:GetBucketLocation"],
     "Resource": _SCOPED_S3},
    {"Sid": "DataPlaneAndTelemetry", "Effect": "Allow", "Action": _WILDCARD_ACTIONS, "Resource": "*"},
]})

print(f"[1/5] IAM role {ROLE}")
try:
    role_arn = iam.create_role(RoleName=ROLE, AssumeRolePolicyDocument=TRUST)["Role"]["Arn"]
except iam.exceptions.EntityAlreadyExistsException:
    role_arn = iam.get_role(RoleName=ROLE)["Role"]["Arn"]
iam.put_role_policy(RoleName=ROLE, PolicyName=f"{NAME}_policy", PolicyDocument=POLICY)
print("  waiting 10s for IAM propagation"); time.sleep(10)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)

# The TCGA lake database is Lake Formation-governed; a fresh IAM role has NO LF grants, which would
# silently break every Athena query ("Insufficient Lake Formation permission(s)"). Grant DESCRIBE on
# the database + SELECT/DESCRIBE on its tables to the new role. Best-effort: warn if the deployer
# lacks lakeformation:GrantPermissions (grant it manually then).
ATHENA_DB = "oncology_semantic_hub"
RODA_DB = "oncology_semantic_hub_roda"  # v3 RODA extension tables (additive)
RAW_DB = "oncology_semantic_hub_raw"    # L2 flat PrimeKG (additive)
_LF_MAP = {"L1": (ATHENA_DB,), "L3": (ATHENA_DB, RODA_DB), "L2": (ATHENA_DB, RODA_DB, RAW_DB), "L3b": (ATHENA_DB, RODA_DB, RAW_DB), "L3c": (ATHENA_DB, RODA_DB, RAW_DB)}
_LF_DBS = _LF_MAP.get(LAYER, (ATHENA_DB, RODA_DB))  # L3 ablations (L3_no_*) get the same data grants as L3
try:
    lf = boto3.client("lakeformation", region_name=REGION)
    grants = []
    for db in _LF_DBS:
        grants += [
            ({"Database": {"Name": db}}, ["DESCRIBE"]),
            ({"Table": {"DatabaseName": db, "TableWildcard": {}}}, ["SELECT", "DESCRIBE"]),
        ]
    for resource, perms in grants:
        try:
            lf.grant_permissions(Principal={"DataLakePrincipalIdentifier": role_arn},
                                 Resource=resource, Permissions=perms)
        except Exception:  # noqa: BLE001 — already granted or table-level nuance; continue
            pass
    print(f"  granted Lake Formation DESCRIBE/SELECT on {', '.join(_LF_DBS)} to the role")
except Exception as e:  # noqa: BLE001
    print(f"  WARN: Lake Formation grant failed ({e}); Athena queries will fail until granted manually")

print("[2/5] build package (ARM64)")
if BUILD.exists():
    shutil.rmtree(BUILD)
pkg = BUILD / "pkg"; pkg.mkdir(parents=True)
# SECURITY (B603/semgrep dangerous-subprocess-use): fully static argument vector — every element
# is a hardcoded literal (package names, platform/version flags); no shell is used (list-form
# argv, shell=False); no external/tainted input anywhere in this call. Not command-injectable.
# Not fixable by shlex.quote() — that function is for building shell command STRINGS and would
# corrupt a list-form argv element; it does not apply to this call shape. ACCEPTED RESIDUAL
# FINDING: AWS's own official AgentCore Runtime reference sample uses the identical pattern —
# 02-host-your-agent/01-runtime/02-hosting-tools/01-mcp-server-basics/deploy.py's
# zip_and_upload_code() calls `subprocess.run(["uv", "pip", "install", "--python-platform",
# "aarch64-manylinux2014", ...], check=True)` to cross-install ARM64 wheels — there is no
# AWS-blessed packaging path that avoids a subprocess call to the package manager. The repo's
# shared utils/runtime_helpers.py avoids subprocess entirely, but only because it zips
# ALREADY-INSTALLED files — it has no install step, so adopting it would drop this script's
# ARM64 cross-compilation capability (a functional regression) rather than fix anything. Also
# confirmed (2026-10-08/09 scans): Slingshot re-flags this call shape regardless of
# # nosemgrep/# nosec annotations — suppression comments do not clear it. Audited; no code change.
subprocess.run([sys.executable, "-m", "pip", "install",  # nosec B603  # nosemgrep
                "strands-agents[otel]", "strands-agents-tools", "bedrock-agentcore",
                "aws-opentelemetry-distro", "mcp", "-t", str(pkg),
                "--platform", "manylinux2014_aarch64", "--only-binary=:all:",
                "--python-version", "3.13", "--quiet"], check=True)
shutil.copy(_DIR / "semantic_hub_agent.py", pkg / "semantic_hub_agent.py")
# Bundle the shared hub_core package (live get_hub_schema) beside the agent so `import hub_core` works
# from the deployment package root. Exclude caches/tests.
shutil.copytree(_DIR.parent / "hub_core", pkg / "hub_core",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
zip_path = BUILD / "deployment_package.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(pkg):
        for f in files:
            if f.endswith(".pyc") or "__pycache__" in root:
                continue
            full = Path(root) / f
            zf.write(full, full.relative_to(pkg))
print(f"  {zip_path} ({zip_path.stat().st_size/1024/1024:.1f} MB)")

print("[3/5] upload to S3")
try:
    s3.create_bucket(Bucket=BUCKET) if REGION == "us-east-1" else s3.create_bucket(
        Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
except Exception:
    pass
s3.upload_file(str(zip_path), BUCKET, KEY)
print(f"  s3://{BUCKET}/{KEY}")

print(f"[4/5] create runtime {NAME}")
# L0-web: inject the AWS-managed Web Search gateway config (us-east-1) so the runtime's web_search tool
# can fetch a Cognito token + call the gateway. Read from env (source utils/.env.web-search before deploy);
# no secret is stored in source. The gateway/Cognito live in us-east-1 regardless of the runtime region.
_WS_ENV = {}
if LAYER == "L0-web":
    _wd = os.environ["COGNITO_DOMAIN"]
    _WS_ENV = {
        "SEMHUB_WS_GATEWAY_URL": os.environ["AGENTCORE_GATEWAY_URL"],
        "SEMHUB_WS_TOKEN_URL": f"https://{_wd}.auth.us-east-1.amazoncognito.com/oauth2/token",
        "SEMHUB_WS_CLIENT_ID": os.environ["COGNITO_CLIENT_ID"],
        "SEMHUB_WS_CLIENT_SECRET": os.environ["COGNITO_CLIENT_SECRET"],
        "SEMHUB_WS_SCOPE": os.environ.get("COGNITO_SCOPE", ""),
    }
    print(f"  L0-web: wired web-search gateway {os.environ['AGENTCORE_GATEWAY_URL']}")

# Inject the hub's data-plane config into the runtime (the agent's defaults are placeholders).
# GRAPH_ID is required; ATHENA_OUTPUT/data bucket derives from the deploy account+region unless overridden.
_GRAPH_ID = os.environ.get("SEMHUB_GRAPH_ID", "")
if LAYER.startswith("L3") and not _GRAPH_ID:
    raise SystemExit("SEMHUB_GRAPH_ID is required to deploy L3/graph layers. "
                     "export SEMHUB_GRAPH_ID=<your-neptune-analytics-graph-id>")
_ATHENA_OUTPUT = os.environ.get("SEMHUB_ATHENA_OUTPUT",
                                f"s3://oncology-semantic-hub-data-{acct}-{REGION}/athena-results/")
_HUB_ENV = {
    "SEMHUB_REGION": REGION,
    "SEMHUB_ATHENA_OUTPUT": _ATHENA_OUTPUT,
    **({"SEMHUB_GRAPH_ID": _GRAPH_ID} if _GRAPH_ID else {}),
    **({"SEMHUB_ATHENA_DB": os.environ["SEMHUB_ATHENA_DB"]} if os.environ.get("SEMHUB_ATHENA_DB") else {}),
}
resp = ctrl.create_agent_runtime(
    agentRuntimeName=NAME,
    agentRuntimeArtifact={"codeConfiguration": {
        "code": {"s3": {"bucket": BUCKET, "prefix": KEY}},
        "runtime": "PYTHON_3_13",
        "entryPoint": ["opentelemetry-instrument", "semantic_hub_agent.py"]}},
    networkConfiguration={"networkMode": "PUBLIC"},
    environmentVariables={"SEMHUB_LAYER": LAYER, **_HUB_ENV, **_WS_ENV,
                          **({"SEMHUB_TEMP": os.environ["SEMHUB_TEMP"]} if os.environ.get("SEMHUB_TEMP") else {}),
                          **({"SEMHUB_SUBJECT_MODEL": os.environ["SEMHUB_SUBJECT_MODEL"]} if os.environ.get("SEMHUB_SUBJECT_MODEL") else {}),
                          **({"SEMHUB_STREAMING": os.environ["SEMHUB_STREAMING"]} if os.environ.get("SEMHUB_STREAMING") else {})},
    roleArn=role_arn)
agent_id = resp["agentRuntimeId"]
print(f"  runtime id: {agent_id}")

print("[5/5] wait for READY")
for el in range(0, 600, 15):
    st = ctrl.get_agent_runtime(agentRuntimeId=agent_id).get("status", "UNKNOWN")
    print(f"  [{el:>3}s] {st}")
    if st in ("READY", "ACTIVE"):
        break
    if "FAILED" in st:
        raise RuntimeError(f"deploy failed: {st}")
    time.sleep(15)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)

agent_arn = ctrl.get_agent_runtime(agentRuntimeId=agent_id)["agentRuntimeArn"]
cfg = {"agent_id": agent_id, "agent_arn": agent_arn,
       "cw_log_group": f"/aws/bedrock-agentcore/runtimes/{agent_id}-DEFAULT",
       "region": REGION, "role_arn": role_arn, "s3_bucket": BUCKET, "s3_key": KEY,
       "layer": LAYER,
       "subject_model": os.environ.get("SEMHUB_SUBJECT_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")}
_CONFIG.write_text(json.dumps(cfg, indent=2))
print(f"\nDeploy complete. {json.dumps(cfg, indent=2)}")
