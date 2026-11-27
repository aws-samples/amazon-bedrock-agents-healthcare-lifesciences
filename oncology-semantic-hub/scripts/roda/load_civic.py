"""Reusable loader: CIViC Clinical Evidence (RODA) -> tidy `civic_evidence` table (somatic actionability).

CIViC = expert-curated **somatic** clinical interpretation (drug response, evidence level A-E). This is the
canonical *actionability* source (tech spec: "Cancer Biomarker predicts_response_to Drug"). Grounded in the
verified 25-column schema (docs/roda-v3-spec.md §1). Snapshot default = latest verified (01-Oct-2025).

SAFE BY DEFAULT: --dry-run (reads PUBLIC bucket, prints cleaned schema/sample, NO writes). --apply writes
Parquet to our S3 + registers the Glue table. Graph writes are ON HOLD (decision 2026-07-31) — tables only.

Usage:
    python scripts/roda/load_civic.py                       # dry-run, latest snapshot
    python scripts/roda/load_civic.py --snapshot 01-Oct-2025 --apply
"""
import argparse
import io

import boto3
import pandas as pd
from botocore import UNSIGNED
from botocore.config import Config

SRC_BUCKET = "civic-aws-opendata"
SRC_KEY_TMPL = "ClinicalEvidenceSummaries/date={snapshot}/ClinicalEvidenceSummaries.tsv"
DB = "oncology_semantic_hub_roda"
TABLE = "civic_evidence"
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import _config as C
REGION = C.REGION
KEEP = ["gene", "variant", "molecular_profile", "disease", "doid", "therapies",
        "therapy_interaction_type", "evidence_type", "evidence_direction", "evidence_level",
        "significance", "citation_id", "evidence_civic_url", "evidence_status", "variant_origin",
        "evidence_id"]
# Config (C.require) + the S3 client are resolved lazily inside fetch_clean()/main() so importing this
# module for unit tests of clean() needs no AWS config or network.


def clean(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Pure transform (no I/O; unit-testable): raw CIViC ClinicalEvidenceSummaries -> tidy KEEP columns.

    molecular_profile e.g. "EGFR L858R" -> gene=first token, variant=remainder (multi-gene profiles kept whole
    in variant); therapies split on commas -> list; accepted evidence only.
    """
    df = df_raw.fillna("")
    mp = df["molecular_profile"].str.strip()
    df["gene"] = mp.str.split().str[0]
    df["variant"] = mp.str.split(n=1).str[1].fillna("")
    df["therapies"] = df["therapies"].str.split(r"\s*,\s*")
    df = df[df["evidence_status"].str.lower() == "accepted"]  # accepted evidence only
    return df[KEEP].reset_index(drop=True)


def fetch_clean(snapshot: str) -> pd.DataFrame:
    s3_pub = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name=REGION)
    key = SRC_KEY_TMPL.format(snapshot=snapshot)
    body = s3_pub.get_object(Bucket=SRC_BUCKET, Key=key)["Body"].read()
    return clean(pd.read_csv(io.BytesIO(body), sep="\t", dtype=str))


def apply_write(df, out_s3, snapshot, db=DB, table=TABLE):
    import pyarrow as pa
    from pyarrow import fs as pafs
    import pyarrow.parquet as pq
    df = df.copy()
    df["source_snapshot"] = snapshot
    df["therapies"] = df["therapies"].apply(lambda x: x if isinstance(x, list) else [])
    bucket = out_s3.replace("s3://", "").split("/", 1)[0]
    prefix = out_s3.replace(f"s3://{bucket}/", "").rstrip("/")
    s3fs = pafs.S3FileSystem(region=REGION)
    with s3fs.open_output_stream(f"{bucket}/{prefix}/civic_evidence.parquet") as f:
        pq.write_table(pa.Table.from_pandas(df, preserve_index=False), f)
    glue = boto3.client("glue", region_name=REGION)
    try:
        glue.create_database(DatabaseInput={"Name": db, "Description": "RODA-sourced open data (v3)"})
    except glue.exceptions.AlreadyExistsException:
        pass
    def _t(c):
        return "array<string>" if c == "therapies" else "string"
    cols = [{"Name": c, "Type": _t(c)} for c in list(df.columns)]
    try:
        glue.delete_table(DatabaseName=db, Name=table)
    except glue.exceptions.EntityNotFoundException:
        pass
    glue.create_table(DatabaseName=db, TableInput={
        "Name": table, "TableType": "EXTERNAL_TABLE",
        "StorageDescriptor": {"Columns": cols, "Location": out_s3,
            "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
            "SerdeInfo": {"SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"}}})
    print(f"[APPLY] wrote {len(df)} rows to {out_s3} + registered {db}.{table}")


def main():
    C.require("BUCKET")
    default_out = f"s3://{C.BUCKET}/roda/civic_evidence/"
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default="01-Oct-2025", help="CIViC monthly dump date=<snapshot>")
    ap.add_argument("--out-s3", default=None)
    ap.add_argument("--target-db", default=DB)
    ap.add_argument("--target-table", default=TABLE)
    ap.add_argument("--staging", action="store_true",
                    help="write to a STAGING namespace (never clobbers prod civic_evidence)")
    ap.add_argument("--apply", action="store_true", help="write to S3 + Glue (default: dry-run)")
    a = ap.parse_args()
    db, table = a.target_db, a.target_table
    out_s3 = a.out_s3 or default_out
    if a.staging:
        # Additive staging: a NEW table in the SAME roda DB that L3 already queries → L3 reads it via its
        # existing generic Athena tool with NO code change / NO redeploy. Prod `civic_evidence` is untouched.
        table = f"{TABLE}_staging"
        out_s3 = a.out_s3 or f"s3://{C.BUCKET}/roda_staging/civic_evidence/"
    df = fetch_clean(a.snapshot)
    print(f"accepted evidence rows: {len(df)}  columns: {list(df.columns)}")
    print("\nevidence_level distribution:")
    print(df["evidence_level"].value_counts().to_string())
    egfr = df[df.gene == "EGFR"].head(6)
    print(f"\nEGFR actionability sample ({(df.gene=='EGFR').sum()} EGFR rows):")
    print(egfr[["gene", "variant", "disease", "therapies", "evidence_level", "significance", "citation_id"]].to_string())
    print(f"\ntarget: {db}.{table}  ->  {out_s3}" + ("  [STAGING]" if a.staging else ""))
    if not a.apply:
        print("\n[DRY-RUN] no writes. Re-run with --apply to persist (graph writes remain ON HOLD).")
        return
    apply_write(df, out_s3, a.snapshot, db=db, table=table)


if __name__ == "__main__":
    main()
