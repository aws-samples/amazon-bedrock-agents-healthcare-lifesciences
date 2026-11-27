"""Tear down Oncology Semantic Hub agent resources created by deploy.py.

deploy.py creates, per deployed layer: an AgentCore Runtime, an IAM execution role + inline
policy, Lake Formation grants to that role, and an S3 code-package object (in the shared
bedrock-agentcore-code-<acct>-<region> bucket). It records all of this in agent_config[_<layer>].json.
This script reverses exactly that, reading each config file so it only deletes what was deployed.

It does NOT delete the data plane (Neptune graph, Athena/Glue databases, data-lake S3, the Bedrock
Knowledge Base). Those are shared across layers and expensive to rebuild — tear them down explicitly
with the documented commands in docs/TEARDOWN.md (and agentcore/kb/create_kb.py --delete for the KB).

Usage:
    python agentcore/cleanup.py                         # show what would be deleted, touch nothing
    python agentcore/cleanup.py --layer L3             # tear down one layer's runtime + role
    python agentcore/cleanup.py --all                  # tear down every layer found in agent_config*.json
    python agentcore/cleanup.py --all --delete-code-bucket   # also empty+delete the shared code bucket

Safe by default: without --all or --layer it only lists. Each deletion is best-effort and continues
on error so a partially-deleted layer can still be cleaned up.
"""
import argparse
import glob
import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

_DIR = Path(__file__).parent


def _load_configs(layer):
    """Return [(path, config_dict)] for the requested layer, or all agent_config*.json if layer is None."""
    if layer:
        name = "agent_config.json" if layer == "L3" else f"agent_config_{layer.lower()}.json"
        paths = [_DIR / name]
    else:
        paths = [Path(p) for p in sorted(glob.glob(str(_DIR / "agent_config*.json")))]
        # agent_config.example.json is a template, not a real deployment.
        paths = [p for p in paths if p.name != "agent_config.example.json"]
    out = []
    for p in paths:
        if not p.exists():
            print(f"  (skip) {p.name} — not found")
            continue
        try:
            out.append((p, json.loads(p.read_text())))
        except (ValueError, OSError) as e:
            print(f"  (skip) {p.name} — unreadable ({e})")
    return out


def _delete_runtime(ctrl, cfg):
    agent_id = cfg.get("agent_id")
    if not agent_id:
        print("    no agent_id in config; skipping runtime")
        return
    try:
        ctrl.delete_agent_runtime(agentRuntimeId=agent_id)
        print(f"    deleted runtime {agent_id}")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("ResourceNotFoundException", "ValidationException"):
            print(f"    runtime {agent_id} already gone")
        else:
            print(f"    WARN: delete runtime {agent_id} failed: {e}")


def _delete_role(iam, role_arn):
    """Delete the execution role: drop inline policies first (required before DeleteRole)."""
    if not role_arn:
        print("    no role_arn in config; skipping role")
        return
    role_name = role_arn.split("/")[-1]
    try:
        for pol in iam.list_role_policies(RoleName=role_name).get("PolicyNames", []):
            iam.delete_role_policy(RoleName=role_name, PolicyName=pol)
            print(f"    deleted inline policy {pol}")
        # Detach any managed policies too (deploy.py uses inline only, but be defensive).
        for att in iam.list_attached_role_policies(RoleName=role_name).get("AttachedPolicies", []):
            iam.detach_role_policy(RoleName=role_name, PolicyArn=att["PolicyArn"])
        iam.delete_role(RoleName=role_name)
        print(f"    deleted role {role_name}")
    except iam.exceptions.NoSuchEntityException:
        print(f"    role {role_name} already gone")
    except ClientError as e:
        print(f"    WARN: delete role {role_name} failed: {e}")


def _delete_code_object(s3, cfg):
    bucket, key = cfg.get("s3_bucket"), cfg.get("s3_key")
    if not (bucket and key):
        return
    try:
        s3.delete_object(Bucket=bucket, Key=key)
        print(f"    deleted code object s3://{bucket}/{key}")
    except ClientError as e:
        print(f"    WARN: delete code object failed: {e}")


def _empty_and_delete_bucket(s3, bucket):
    """Empty then delete the shared code bucket. Only called with --delete-code-bucket."""
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objs:
                s3.delete_objects(Bucket=bucket, Delete={"Objects": objs})
        s3.delete_bucket(Bucket=bucket)
        print(f"  deleted code bucket {bucket}")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchBucket", "404"):
            print(f"  code bucket {bucket} already gone")
        else:
            print(f"  WARN: delete code bucket {bucket} failed: {e}")


def main():
    ap = argparse.ArgumentParser(description="Tear down AgentCore agent resources from deploy.py.")
    ap.add_argument("--region", default=None, help="override; else taken from each config's 'region'")
    ap.add_argument("--layer", default=None,
                    help="tear down a single layer (L0/L1/L2/L3/L3a/...). Omit with --all for every layer.")
    ap.add_argument("--all", action="store_true", help="tear down every layer found in agent_config*.json")
    ap.add_argument("--delete-code-bucket", action="store_true",
                    help="also empty + delete the shared bedrock-agentcore-code bucket (after all layers)")
    args = ap.parse_args()

    configs = _load_configs(args.layer)
    if not configs:
        print("No agent_config*.json found. Nothing to do.")
        return

    list_only = not (args.all or args.layer)
    if list_only:
        print("=== cleanup plan (list only — pass --layer <L> or --all to execute) ===")
    code_buckets = set()
    for path, cfg in configs:
        print(f"\n{path.name}: layer={cfg.get('layer', '?')} region={cfg.get('region', '?')}")
        print(f"  runtime : {cfg.get('agent_id', '(none)')}")
        print(f"  role    : {cfg.get('role_arn', '(none)')}")
        print(f"  code obj: s3://{cfg.get('s3_bucket', '?')}/{cfg.get('s3_key', '?')}")
        if cfg.get("s3_bucket"):
            code_buckets.add((cfg.get("region"), cfg["s3_bucket"]))
        if list_only:
            continue
        region = args.region or cfg.get("region") or "us-west-2"
        ctrl = boto3.client("bedrock-agentcore-control", region_name=region)
        iam = boto3.client("iam", region_name=region)
        s3 = boto3.client("s3", region_name=region)
        _delete_runtime(ctrl, cfg)
        _delete_role(iam, cfg.get("role_arn"))
        _delete_code_object(s3, cfg)
        # Leave the config file in place as a record; the user can delete it manually.

    if list_only:
        if args.delete_code_bucket:
            print("\n  (would also delete the shared code bucket with --all)")
        print("\nNothing deleted (list only).")
        return

    if args.delete_code_bucket:
        print("\n=== shared code bucket ===")
        for region, bucket in code_buckets:
            s3 = boto3.client("s3", region_name=args.region or region or "us-west-2")
            _empty_and_delete_bucket(s3, bucket)

    print("\nAgent teardown complete. Data plane (Neptune/Athena/Glue/S3 lake/KB) is NOT touched — "
          "see docs/TEARDOWN.md.")


if __name__ == "__main__":
    main()
