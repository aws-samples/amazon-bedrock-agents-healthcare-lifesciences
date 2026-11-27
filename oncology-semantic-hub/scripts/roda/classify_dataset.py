"""Reusable classifier: RODA dataset metadata + S3 preview -> onboarding lane decision.

Answers, per dataset: is it **BUILD-ETL** (copy+transform into the customer account) or **RUNTIME-DIRECT**
(Athena external table over RODA's bucket, zero copy)? RODA MCP (Lane A, discovery) is always available.

Inputs come from RODA metadata (`get_dataset_details`: Region + S3 bucket) plus a live, read-only S3 preview
(no-sign-request) to detect format / partitioning / nesting / size. See docs/roda-master-plan-scale.md §2.

SAFE: read-only, public buckets only (UNSIGNED). Usage:
    python scripts/roda/classify_dataset.py --slug genoxus-annotation --bucket genoxus-annotation-release --region us-west-2
"""
import argparse
import io
import os

import boto3
from botocore import UNSIGNED
from botocore.config import Config

HUB_REGION = os.environ.get("HUB_REGION", "us-west-2")
_COLUMNAR = {".parquet", ".orc"}


def _client(region):
    return boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name=region)


def preview(bucket, region, max_keys=400):
    s3 = _client(region)
    keys, total = [], 0
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, MaxKeys=max_keys, PaginationConfig={"MaxItems": max_keys}):
        for o in page.get("Contents", []):
            keys.append((o["Key"], o["Size"])); total += o["Size"]
    exts = {os.path.splitext(k)[1].lower() for k, _ in keys if os.path.splitext(k)[1]}
    partitioned = any("=" in k for k, _ in keys)
    return {"n_sampled": len(keys), "exts": exts, "partitioned": partitioned,
            "sample_bytes": total, "keys": keys}


def detect_nested(bucket, region, keys):
    """Read one parquet schema; return True if any field is struct/list/map (nested)."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    pk = next((k for k, _ in keys if k.endswith(".parquet")), None)
    if not pk:
        return None
    body = _client(region).get_object(Bucket=bucket, Key=pk)["Body"].read()
    schema = pq.read_schema(io.BytesIO(body))
    for t in schema.types:
        if pa.types.is_struct(t) or pa.types.is_list(t) or pa.types.is_large_list(t) or pa.types.is_map(t):
            return True
    return False


def classify(slug, bucket, region, hub_region=HUB_REGION):
    sig = preview(bucket, region)
    nested = detect_nested(bucket, region, sig["keys"]) if (_COLUMNAR & sig["exts"]) else None
    fmt = "columnar" if (sig["exts"] and sig["exts"] <= _COLUMNAR) else "raw/mixed"
    if region != hub_region:
        lane, why = "C BUILD-ETL", f"cross-region ({region} != hub {hub_region}) → Athena cannot query in place; copy"
    elif not (sig["exts"] and sig["exts"] <= _COLUMNAR):
        lane, why = "C BUILD-ETL", f"raw/mixed format {sorted(sig['exts'])} → convert to Parquet"
    elif nested:
        lane, why = "C BUILD-ETL", "nested Parquet (struct/list) → flatten for join-friendly querying"
    elif sig["partitioned"]:
        lane, why = "B RUNTIME-DIRECT", "same-region, flat columnar, partitioned → external table (verify no join/subset need)"
    else:
        lane, why = "C BUILD-ETL", "same-region columnar but unpartitioned → ingest (scan cost) [default safe]"
    return {"slug": slug, "bucket": bucket, "region": region, "lane": lane, "rationale": why,
            "format": fmt, "partitioned": sig["partitioned"], "nested": nested,
            "extensions": sorted(sig["exts"]), "objects_sampled": sig["n_sampled"],
            "note": "Lane A (RODA MCP discovery/preview) always available regardless."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="RODA slug (for the record)")
    ap.add_argument("--bucket", required=True, help="S3 bucket from RODA Resources[].ARN")
    ap.add_argument("--region", required=True, help="RODA Resources[].Region")
    ap.add_argument("--hub-region", default=HUB_REGION)
    a = ap.parse_args()
    r = classify(a.slug, a.bucket, a.region, a.hub_region)
    print(f"\n=== {r['slug']} → {r['lane']} ===")
    print(f"rationale : {r['rationale']}")
    print(f"format    : {r['format']} | partitioned={r['partitioned']} | nested={r['nested']} | exts={r['extensions']}")
    print(f"note      : {r['note']}")


if __name__ == "__main__":
    main()
