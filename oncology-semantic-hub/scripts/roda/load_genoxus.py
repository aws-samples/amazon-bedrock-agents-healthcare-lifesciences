"""Reusable loader: flatten Genoxus nested ClinVar (RODA) -> tidy `genoxus_clinvar` table.

Grounded in the verified schema (docs/roda-v3-spec.md §3). Genoxus Parquet is deeply nested ClinVar; this
flattens it to a join-friendly table keyed by (chrom, pos, ref, alt) for the positional join to
`oncology_semantic_hub.tcga_mutations` (both GRCh38; note tcga uses `chr7`, Genoxus uses `7`).

SAFE BY DEFAULT: --dry-run (reads the PUBLIC bucket, prints schema/sample, NO writes). Pass --apply to write
Parquet to our S3 + register the Glue table (requires decisions Q3/Q5 approval + write creds).

Usage:
    python scripts/roda/load_genoxus.py --chroms 7            # dry-run, EGFR chromosome
    python scripts/roda/load_genoxus.py --chroms 7,10,3 --apply
"""
import argparse
import io

import boto3
import pandas as pd
import pyarrow.parquet as pq
from botocore import UNSIGNED
from botocore.config import Config

SRC_BUCKET = "genoxus-annotation-release"
SRC_PREFIX = "Genoxus-Annotation"
DB = "oncology_semantic_hub_roda"
TABLE = "genoxus_clinvar"
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import _config as C          # lazy: importing does not require AWS config
REGION = C.REGION

_s3_pub = boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name=REGION)


def _default_out() -> str:
    """Resolve the default output S3 URI lazily (requires BUCKET only when actually writing)."""
    C.require("BUCKET")
    return f"s3://{C.BUCKET}/roda/genoxus_clinvar/"


def list_window_keys(build: str, chrom: str) -> list:
    keys = []
    pfx = f"{SRC_PREFIX}/GRCh={build}/chr={chrom}/"
    for page in _s3_pub.get_paginator("list_objects_v2").paginate(Bucket=SRC_BUCKET, Prefix=pfx):
        keys += [o["Key"] for o in page.get("Contents", []) if o["Key"].endswith("clinvar.parquet")]
    return keys


def _sig_from_classifications(cls):
    """ClinVar germline significance lives in Classifications[]; prefer GermlineClassification.
    Significance text is in Description (falls back to Name); Review_Status may be null."""
    if not cls:
        return None, None
    g = next((c for c in cls if (c.get("Name") or "").lower().startswith("germline")), cls[0])
    return (g.get("Description") or g.get("Name")), g.get("Review_Status")


def flatten_table(tbl) -> pd.DataFrame:
    out = []
    for r in tbl.to_pylist():
        gl = r.get("Genomic_Location") or {}
        hg = r.get("Host_Genes") or []
        sig, review = _sig_from_classifications(r.get("Classifications"))
        conds = [cc.get("Name") for c in (r.get("Classifications") or [])
                 for cc in (c.get("Conditions") or []) if cc.get("Name")]
        out.append({
            "chrom": gl.get("Chromosome"), "pos": gl.get("Start"),
            "ref": r.get("Reference_Allele"), "alt": r.get("Alternate_Allele"),
            "variant_type": r.get("Variant_Type"),
            "gene_symbol": (hg[0].get("Symbol") if hg else None),
            "clinical_significance": sig, "review_status": review,
            "conditions": sorted(set(conds))[:10],
        })
    return pd.DataFrame(out)


def load_chroms(build, chroms):
    frames = []
    for chrom in chroms:
        keys = list_window_keys(build, chrom)
        print(f"chr{chrom}: {len(keys)} bp-window parquet files")
        for k in keys:
            body = _s3_pub.get_object(Bucket=SRC_BUCKET, Key=k)["Body"].read()
            frames.append(flatten_table(pq.read_table(io.BytesIO(body))))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def apply_write(df, out_s3):
    """GATED: write Parquet + register Glue table. Requires write creds + Q3/Q5 approval."""
    import pyarrow as pa
    from pyarrow import fs as pafs
    import pyarrow.parquet as pq
    bucket = out_s3.replace("s3://", "").split("/", 1)[0]
    prefix = out_s3.replace(f"s3://{bucket}/", "").rstrip("/")
    s3fs = pafs.S3FileSystem(region=REGION)
    with s3fs.open_output_stream(f"{bucket}/{prefix}/genoxus_clinvar.parquet") as f:
        pq.write_table(pa.Table.from_pandas(df, preserve_index=False), f)
    glue = boto3.client("glue", region_name=REGION)
    try:
        glue.create_database(DatabaseInput={"Name": DB, "Description": "RODA-sourced open data (v3)"})
    except glue.exceptions.AlreadyExistsException:
        pass
    def _t(c):
        return "bigint" if c == "pos" else ("array<string>" if c == "conditions" else "string")
    cols = [{"Name": c, "Type": _t(c)} for c in df.columns]
    try:
        glue.delete_table(DatabaseName=DB, Name=TABLE)
    except glue.exceptions.EntityNotFoundException:
        pass
    glue.create_table(DatabaseName=DB, TableInput={
        "Name": TABLE, "TableType": "EXTERNAL_TABLE",
        "StorageDescriptor": {"Columns": cols, "Location": out_s3,
            "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
            "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
            "SerdeInfo": {"SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"}}})
    print(f"[APPLY] wrote {len(df)} rows to {out_s3} + registered {DB}.{TABLE}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="38")
    ap.add_argument("--chroms", default="7", help="comma list, no 'chr' prefix")
    ap.add_argument("--out-s3", default=None, help="default: s3://<BUCKET>/roda/genoxus_clinvar/ (resolved lazily)")
    ap.add_argument("--snapshot", default="2026-06", help="Genoxus release tag for provenance")
    ap.add_argument("--apply", action="store_true", help="write to S3 + Glue (default: dry-run)")
    a = ap.parse_args()
    df = load_chroms(a.build, [c.strip() for c in a.chroms.split(",") if c.strip()])
    if len(df):
        df["build"] = a.build
        df["source_snapshot"] = a.snapshot
    print(f"\nflattened rows: {len(df)}  columns: {list(df.columns)}")
    if len(df):
        print("\nclinical_significance distribution (top 12):")
        print(df["clinical_significance"].value_counts(dropna=False).head(12).to_string())
        egfr = df[(df.chrom == "7") & (df.pos.between(55019017, 55211628))].head(6)
        print("\nEGFR-region sample:")
        print(egfr[["chrom", "pos", "ref", "alt", "gene_symbol", "clinical_significance", "review_status"]].to_string())
    if not a.apply:
        print("\n[DRY-RUN] no writes. Re-run with --apply (after Q3/Q5 approval) to persist.")
        return
    apply_write(df, a.out_s3 or _default_out())


if __name__ == "__main__":
    main()
