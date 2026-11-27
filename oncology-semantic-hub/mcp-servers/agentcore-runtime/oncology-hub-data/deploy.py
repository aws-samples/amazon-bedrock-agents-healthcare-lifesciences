"""Deploy the Oncology Semantic Hub DATA MCP server to Amazon Bedrock AgentCore Runtime.

Boto3, no-Docker code-zip path (modeled on 02-host-your-agent/01-runtime/02-hosting-tools/
01-mcp-server-basics/deploy.py) + the hub's data-access IAM + Lake Formation grants (from
oncology_semantic_hub/agentcore/deploy.py). Reuses the SEPARATELY-deployed OLS Cognito infra for a
CUSTOM_JWT authorizer (reads its SSM params; creates NO new Cognito). Bundles hub_core beside the
server so `import hub_core` resolves in the package.

Prerequisite: deploy the OLS Runtime MCP server first (mcp-servers/agentcore-runtime/
ontology-lookup-service) — this script fails fast if its Cognito SSM params are absent.

Usage:  SEMHUB_GRAPH_ID=<graph-id> python deploy.py [--region us-west-2] [--ols-app ontology-lookup-service]
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
# Permanent layout: this server lives at oncology_semantic_hub/mcp-servers/agentcore-runtime/oncology-hub-data/,
# so hub_core/ is three levels up, inside the hub.
_HUB_CORE = _DIR.parent.parent.parent / "hub_core"
if not (_HUB_CORE / "queries.py").exists():
    raise SystemExit(
        f"hub_core/ not found at {_HUB_CORE} (expected oncology_semantic_hub/hub_core/). "
        "This script assumes it runs from oncology_semantic_hub/mcp-servers/agentcore-runtime/"
        "oncology-hub-data/ — if the server moved, update _HUB_CORE above.")

ap = argparse.ArgumentParser()
ap.add_argument("--region", default=None)
ap.add_argument("--ols-app", default="ontology-lookup-service", help="OLS SSM app name to reuse for Cognito")
args = ap.parse_args()
REGION = args.region or Session().region_name or "us-west-2"
OLS_PREFIX = f"/app/{args.ols_app}/agentcore"

acct = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
iam = boto3.client("iam", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)
ssm = boto3.client("ssm", region_name=REGION)
ctrl = boto3.client("bedrock-agentcore-control", region_name=REGION)

APP = "oncology-hub-data"
NAME = f"oncology_hub_data_{uuid.uuid4().hex[:8]}"
ROLE = f"{NAME}_role"
BUCKET = f"bedrock-agentcore-code-{acct}-{REGION}"
KEY = f"{NAME}/deployment_package.zip"
BUILD = Path(f"/tmp/{NAME}_build")  # nosec B108
ATHENA_DB, RODA_DB = "oncology_semantic_hub", "oncology_semantic_hub_roda"

GRAPH_ID = os.environ.get("SEMHUB_GRAPH_ID", "")
if not GRAPH_ID:
    raise SystemExit("SEMHUB_GRAPH_ID is required. export SEMHUB_GRAPH_ID=<your-neptune-analytics-graph-id>")

# ── [0/6] Preflight: OLS Cognito must already exist (we reuse it, never create) ──────────────
print(f"[0/6] preflight: OLS Cognito under {OLS_PREFIX}")
def _ssm(name):
    return ssm.get_parameter(Name=f"{OLS_PREFIX}/{name}")["Parameter"]["Value"]
try:
    DISCOVERY_URL = _ssm("cognito_discovery_url")
    CLIENT_ID = _ssm("machine_client_id")
except Exception as e:  # noqa: BLE001
    raise SystemExit(
        f"OLS Cognito SSM params not found under {OLS_PREFIX} ({e}). "
        "Deploy the OLS Runtime MCP server first (mcp-servers/agentcore-runtime/ontology-lookup-service).")
print(f"  reusing discovery_url={DISCOVERY_URL}\n  allowedClients=[{CLIENT_ID}]")

# ── [1/6] IAM role — READ-ONLY data access + logs (no write actions) ─────────────────────────
TRUST = json.dumps({"Version": "2012-10-17", "Statement": [{
    "Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"aws:SourceAccount": acct},
                  "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:*:{acct}:runtime/*"}}}]})
# Data/results bucket for scoped S3 (derived like SEMHUB_ATHENA_OUTPUT; override with SEMHUB_DATA_BUCKET).
DATA_BUCKET = os.environ.get("SEMHUB_DATA_BUCKET", f"oncology-semantic-hub-data-{acct}-{REGION}")
POLICY = json.dumps({"Version": "2012-10-17", "Statement": [
    {"Effect": "Allow", "Action": [
        "neptune-graph:ReadDataViaQuery", "neptune-graph:GetGraph", "neptune-graph:GetGraphSummary",
        "athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults",
        "glue:GetTable", "glue:GetTables", "glue:GetDatabase", "glue:GetDatabases",
        "glue:GetPartition", "glue:GetPartitions", "glue:BatchGetPartition",
        "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
        "logs:DescribeLogGroups", "logs:DescribeLogStreams",
    ], "Resource": "*"},
    # S3 scoped to the hub data bucket (least privilege) — read anywhere in it, write only to athena-results/.
    {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": f"arn:aws:s3:::{DATA_BUCKET}/*"},
    {"Effect": "Allow", "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
     "Resource": f"arn:aws:s3:::{DATA_BUCKET}"},
    {"Effect": "Allow", "Action": ["s3:PutObject"],
     "Resource": f"arn:aws:s3:::{DATA_BUCKET}/athena-results/*"},
]})
print(f"[1/6] IAM role {ROLE} (read-only)")
try:
    role_arn = iam.create_role(RoleName=ROLE, AssumeRolePolicyDocument=TRUST)["Role"]["Arn"]
except iam.exceptions.EntityAlreadyExistsException:
    role_arn = iam.get_role(RoleName=ROLE)["Role"]["Arn"]
iam.put_role_policy(RoleName=ROLE, PolicyName=f"{NAME}_policy", PolicyDocument=POLICY)
print("  waiting 10s for IAM propagation"); time.sleep(10)  # nosemgrep

# ── [2/6] Lake Formation grants (fresh role has none → Athena/Glue would fail silently) ──────
print(f"[2/6] Lake Formation DESCRIBE/SELECT on {ATHENA_DB}, {RODA_DB}")
try:
    lf = boto3.client("lakeformation", region_name=REGION)
    for db in (ATHENA_DB, RODA_DB):
        for resource, perms in [({"Database": {"Name": db}}, ["DESCRIBE"]),
                                ({"Table": {"DatabaseName": db, "TableWildcard": {}}}, ["SELECT", "DESCRIBE"])]:
            try:
                lf.grant_permissions(Principal={"DataLakePrincipalIdentifier": role_arn},
                                     Resource=resource, Permissions=perms)
            except Exception:  # noqa: BLE001
                pass
    print("  granted")
except Exception as e:  # noqa: BLE001
    print(f"  WARN: LF grant failed ({e}); grant manually or Athena will fail")

# ── [3/6] Build package (ARM64) — mcp_server.py + hub_core + deps ────────────────────────────
print("[3/6] build package (ARM64)")
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
# AWS-blessed packaging path that avoids a subprocess call to the package manager. Also confirmed
# (2026-10-08/09 scans on the sibling agentcore/deploy.py): Slingshot re-flags this call shape
# regardless of # nosemgrep/# nosec annotations — suppression comments do not clear it. Audited;
# no code change.
subprocess.run([sys.executable, "-m", "pip", "install",  # nosec B603  # nosemgrep
                "mcp>=1.23.0,<2.0.0", "boto3", "bedrock-agentcore", "-t", str(pkg),
                "--platform", "manylinux2014_aarch64", "--only-binary=:all:",
                "--python-version", "3.13", "--quiet"], check=True)
shutil.copy(_DIR / "mcp_server.py", pkg / "mcp_server.py")
shutil.copytree(_HUB_CORE, pkg / "hub_core", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
zip_path = BUILD / "deployment_package.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(pkg):
        for f in files:
            if f.endswith(".pyc") or "__pycache__" in root:
                continue
            full = Path(root) / f
            zf.write(full, full.relative_to(pkg))
print(f"  {zip_path} ({zip_path.stat().st_size/1024/1024:.1f} MB)")

# ── [4/6] Upload to S3 ───────────────────────────────────────────────────────────────────────
print("[4/6] upload to S3")
try:
    s3.create_bucket(Bucket=BUCKET) if REGION == "us-east-1" else s3.create_bucket(
        Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
except Exception:  # noqa: BLE001
    pass
s3.upload_file(str(zip_path), BUCKET, KEY)
print(f"  s3://{BUCKET}/{KEY}")

# ── [5/6] Create runtime (MCP protocol + CUSTOM_JWT reusing OLS Cognito) ─────────────────────
print(f"[5/6] create runtime {NAME} (serverProtocol=MCP, CUSTOM_JWT)")
ATHENA_OUTPUT = os.environ.get("SEMHUB_ATHENA_OUTPUT",
                               f"s3://oncology-semantic-hub-data-{acct}-{REGION}/athena-results/")
resp = ctrl.create_agent_runtime(
    agentRuntimeName=NAME,
    agentRuntimeArtifact={"codeConfiguration": {
        "code": {"s3": {"bucket": BUCKET, "prefix": KEY}},
        "runtime": "PYTHON_3_13",
        "entryPoint": ["mcp_server.py"]}},
    networkConfiguration={"networkMode": "PUBLIC"},
    protocolConfiguration={"serverProtocol": "MCP"},
    authorizerConfiguration={"customJWTAuthorizer": {
        "discoveryUrl": DISCOVERY_URL, "allowedClients": [CLIENT_ID]}},
    environmentVariables={"SEMHUB_REGION": REGION, "SEMHUB_GRAPH_ID": GRAPH_ID,
                          "SEMHUB_ATHENA_DB": ATHENA_DB, "SEMHUB_RODA_DB": RODA_DB,
                          "SEMHUB_ATHENA_OUTPUT": ATHENA_OUTPUT, "SEMHUB_ATHENA_WG": "primary"},
    roleArn=role_arn)
agent_id = resp["agentRuntimeId"]
agent_arn = resp["agentRuntimeArn"]
print(f"  runtime id: {agent_id}")
for el in range(0, 600, 15):
    st = ctrl.get_agent_runtime(agentRuntimeId=agent_id).get("status", "UNKNOWN")
    print(f"  [{el:>3}s] {st}")
    if st in ("READY", "ACTIVE"):
        break
    if "FAILED" in st:
        raise RuntimeError(f"deploy failed: {st}")
    time.sleep(15)  # nosemgrep

# ── [6/6] Build MCP URL + write SSM ──────────────────────────────────────────────────────────
encoded_arn = agent_arn.replace(":", "%3A").replace("/", "%2F")
mcp_url = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
for k, v in {"mcp_url": mcp_url, "agent_arn": agent_arn, "agent_id": agent_id}.items():
    ssm.put_parameter(Name=f"/app/{APP}/agentcore/{k}", Value=v, Type="String", Overwrite=True)
cfg = {"agent_id": agent_id, "agent_arn": agent_arn, "mcp_url": mcp_url, "region": REGION,
       "role_arn": role_arn, "ols_app": args.ols_app}
(_DIR / "runtime_config.json").write_text(json.dumps(cfg, indent=2))
print(f"[6/6] wrote SSM /app/{APP}/agentcore/{{mcp_url,agent_arn,agent_id}} + runtime_config.json")
print(f"\nDeploy complete.\n{json.dumps(cfg, indent=2)}")
