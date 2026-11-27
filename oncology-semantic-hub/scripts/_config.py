"""Shared configuration for the data-setup pipeline (`scripts/`) — Accelerator 1.

Single source of truth for the AWS identifiers every step needs, so the bucket / region /
graph id are defined ONCE instead of being copy-pasted into each script.

**No account-specific values are hardcoded.** Every value is read from an environment
variable. Set these before running the pipeline (see `.env.example` at the repo root):

    export SEMHUB_ACCOUNT_ID=123456789012                 # your AWS account id
    export SEMHUB_REGION=us-west-2                         # your region
    export SEMHUB_GRAPH_ID=g-xxxxxxxxxx                    # your Neptune Analytics graph id
    export SEMHUB_BUCKET=my-hub-data-bucket                # optional; derived from account+region if unset
    export SEMHUB_ATHENA_DB=oncology_semantic_hub          # optional; has a sensible default
    export SEMHUB_GLUE_ROLE_ARN=arn:aws:iam::123456789012:role/<glue-crawler-role>
    export SEMHUB_IMPORT_ROLE_ARN=arn:aws:iam::123456789012:role/<neptune-import-role>

Scripts call `_config.require("BUCKET", "GRAPH_ID", ...)` at startup, which fails loudly with
setup guidance if a needed value is unset — so the pipeline never silently targets the wrong
account.
"""
from __future__ import annotations

import os
from pathlib import Path

# ── AWS identifiers (all env-driven; no hardcoded account) ──────────────────
ACCOUNT_ID = os.environ.get("SEMHUB_ACCOUNT_ID", "")
REGION = os.environ.get("SEMHUB_REGION", "us-west-2")
# Data bucket: explicit override, else derived from account+region (empty if account unset).
_BUCKET_DEFAULT = f"oncology-semantic-hub-data-{ACCOUNT_ID}-{REGION}" if ACCOUNT_ID else ""
BUCKET = os.environ.get("SEMHUB_BUCKET", _BUCKET_DEFAULT)

GRAPH_ID = os.environ.get("SEMHUB_GRAPH_ID", "")
ATHENA_DB = os.environ.get("SEMHUB_ATHENA_DB", "oncology_semantic_hub")
RAW_DB = os.environ.get("SEMHUB_RAW_DB", "oncology_semantic_hub_raw")
RODA_DB = os.environ.get("SEMHUB_RODA_DB", "oncology_semantic_hub_roda")
CRAWLER_NAME = os.environ.get("SEMHUB_CRAWLER", "oncology-hub-crawler")

# Roles the AWS services assume. Empty by default — required only for the steps that use them
# (07 Glue crawler, 08 Neptune import); require() guards those.
GLUE_ROLE_ARN = os.environ.get("SEMHUB_GLUE_ROLE_ARN", "")
IMPORT_ROLE_ARN = os.environ.get("SEMHUB_IMPORT_ROLE_ARN", "")

# ── S3 locations (empty if BUCKET unset — require() catches it) ─────────────
LAKE_S3 = f"s3://{BUCKET}/lake/" if BUCKET else ""
NEPTUNE_S3 = f"s3://{BUCKET}/neptune/" if BUCKET else ""
ATHENA_OUTPUT = os.environ.get("SEMHUB_ATHENA_OUTPUT", f"s3://{BUCKET}/athena-results/" if BUCKET else "")

# ── Local paths ──────────────────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
DATA_DIR = ROOT / "data"


def require(*names: str) -> None:
    """Fail loudly if any required config value is unset. Call at the top of a script's main().

    Example:  _config.require("BUCKET", "GRAPH_ID")
    """
    missing = [n for n in names if not globals().get(n)]
    if missing:
        env_names = {"BUCKET": "SEMHUB_ACCOUNT_ID (or SEMHUB_BUCKET)", "GRAPH_ID": "SEMHUB_GRAPH_ID",
                     "ACCOUNT_ID": "SEMHUB_ACCOUNT_ID", "GLUE_ROLE_ARN": "SEMHUB_GLUE_ROLE_ARN",
                     "IMPORT_ROLE_ARN": "SEMHUB_IMPORT_ROLE_ARN", "ATHENA_OUTPUT": "SEMHUB_BUCKET"}
        lines = "\n".join(f"  export {env_names.get(n, 'SEMHUB_' + n)}=<value>" for n in missing)
        raise SystemExit(
            f"[config] Missing required configuration: {', '.join(missing)}\n"
            f"Set these environment variables before running (see .env.example):\n{lines}")


def summary() -> str:
    """One-line-per-value dump, printed by scripts at startup so a run is self-documenting."""
    return "\n".join(
        f"  {k:<16} {v or '(unset)'}"
        for k, v in [
            ("account", ACCOUNT_ID), ("region", REGION), ("bucket", BUCKET),
            ("graph_id", GRAPH_ID), ("athena_db", ATHENA_DB), ("crawler", CRAWLER_NAME),
            ("lake_s3", LAKE_S3), ("neptune_s3", NEPTUNE_S3),
            ("glue_role", GLUE_ROLE_ARN), ("import_role", IMPORT_ROLE_ARN),
        ]
    )
