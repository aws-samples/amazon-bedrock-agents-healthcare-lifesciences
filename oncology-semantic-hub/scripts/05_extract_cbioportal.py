#!/usr/bin/env python3
"""Task 5: Extract cBioPortal CNA + expression data for TCGA studies → S3 Parquet."""
import io, time, requests
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import boto3

import _config as C
C.require("BUCKET")
BUCKET = C.BUCKET
REGION = C.REGION
BASE = "https://www.cbioportal.org/api"
S3 = boto3.client("s3", region_name=REGION)
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

# Studies: coad_tcga doesn't exist on cBioPortal; the correct ID is coadread_tcga
STUDIES = ["brca_tcga", "luad_tcga", "gbm_tcga", "ov_tcga", "coadread_tcga"]

# 10 cancer driver genes (entrez IDs from task spec)
DRIVER_GENES = [7157, 672, 675, 5728, 3845, 673, 1956, 5290, 4893, 7428]

# Map entrez → hugo for expression output (avoids extra API call)
ENTREZ_TO_HUGO = {
    7157: "TP53", 672: "BRCA1", 675: "BRCA2", 5728: "PTEN", 3845: "KRAS",
    673: "BRAF", 1956: "EGFR", 5290: "PIK3CA", 4893: "NRAS", 7428: "VHL",
}


def api_post(url, body, retries=3):
    """POST with retries."""
    for attempt in range(retries):
        try:
            r = requests.post(url, json=body, headers=HEADERS, timeout=120)
            if r.status_code == 200:
                return r.json()
            print(f"    ⚠ HTTP {r.status_code} (attempt {attempt+1})")
        except requests.RequestException as e:
            print(f"    ⚠ {e} (attempt {attempt+1})")
        time.sleep(2 ** attempt)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    return []


def upload_parquet(df, key):
    """Write DataFrame as Parquet to S3."""
    buf = io.BytesIO()
    pq.write_table(pa.Table.from_pandas(df), buf, compression="snappy")
    buf.seek(0)
    S3.put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    print(f"    → s3://{BUCKET}/{key} ({len(df)} rows, {buf.tell()/1e6:.1f} MB)")


def find_profiles(study_id):
    """Return (cna_profile_id, expression_profile_id) for a study."""
    r = requests.get(f"{BASE}/studies/{study_id}/molecular-profiles", headers=HEADERS, timeout=30)
    profiles = r.json() if r.status_code == 200 else []
    cna_id = expr_id = None
    for p in profiles:
        pid = p["molecularProfileId"]
        if p["molecularAlterationType"] == "COPY_NUMBER_ALTERATION" and p["datatype"] == "DISCRETE":
            cna_id = pid
        # Prefer RNA-seq v2 z-scores relative to diploid
        if p["molecularAlterationType"] == "MRNA_EXPRESSION" and p["datatype"] == "Z-SCORE":
            if "rna_seq_v2" in pid and "median_Zscores" in pid and "all_sample" not in pid:
                expr_id = pid
            elif expr_id is None and "median_Zscores" in pid and "all_sample" not in pid:
                expr_id = pid
    return cna_id, expr_id


def fetch_cna(study_id, profile_id):
    """Fetch discrete CNA for all genes (non-zero alterations only)."""
    data = api_post(
        f"{BASE}/molecular-profiles/{profile_id}/discrete-copy-number/fetch?projection=DETAILED",
        {"sampleListId": f"{study_id}_all"},
    )
    if not data:
        return pd.DataFrame()
    rows = [
        {
            "sample_id": rec["sampleId"],
            "hugo_symbol": rec.get("gene", {}).get("hugoGeneSymbol", ""),
            "entrez_gene_id": rec["entrezGeneId"],
            "value": rec["alteration"],
            "project_id": study_id,
        }
        for rec in data
    ]
    return pd.DataFrame(rows)


def fetch_expression(study_id, profile_id):
    """Fetch expression z-scores for driver genes."""
    data = api_post(
        f"{BASE}/molecular-profiles/{profile_id}/molecular-data/fetch?projection=SUMMARY",
        {"sampleListId": f"{study_id}_all", "entrezGeneIds": DRIVER_GENES},
    )
    if not data:
        return pd.DataFrame()
    rows = [
        {
            "sample_id": rec["sampleId"],
            "hugo_symbol": ENTREZ_TO_HUGO.get(rec["entrezGeneId"], ""),
            "entrez_gene_id": rec["entrezGeneId"],
            "value": rec["value"],
            "project_id": study_id,
        }
        for rec in data
    ]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("=== Task 5: cBioPortal CNA + Expression → S3 ===")
    summary = []

    for study in STUDIES:
        print(f"\n  [{study}]")
        cna_pid, expr_pid = find_profiles(study)
        print(f"    CNA profile:  {cna_pid}")
        print(f"    Expr profile: {expr_pid}")

        # --- CNA ---
        cna_rows = 0
        if cna_pid:
            df_cna = fetch_cna(study, cna_pid)
            if len(df_cna):
                upload_parquet(df_cna, f"lake/tcga_cna/source=cbioportal/project_id={study}/cna.parquet")
                cna_rows = len(df_cna)
            else:
                print("    (no CNA data)")
        time.sleep(1)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)

        # --- Expression ---
        expr_rows = 0
        if expr_pid:
            df_expr = fetch_expression(study, expr_pid)
            if len(df_expr):
                upload_parquet(df_expr, f"lake/tcga_expression/source=cbioportal/project_id={study}/expression.parquet")
                expr_rows = len(df_expr)
            else:
                print("    (no expression data)")
        time.sleep(1)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)

        summary.append({"study": study, "cna_rows": cna_rows, "expr_rows": expr_rows})

    print("\n=== Summary ===")
    print(f"  {'Study':<20s} {'CNA rows':>10s} {'Expr rows':>10s}")
    print(f"  {'-'*20} {'-'*10} {'-'*10}")
    total_cna = total_expr = 0
    for s in summary:
        print(f"  {s['study']:<20s} {s['cna_rows']:>10,d} {s['expr_rows']:>10,d}")
        total_cna += s["cna_rows"]
        total_expr += s["expr_rows"]
    print(f"  {'TOTAL':<20s} {total_cna:>10,d} {total_expr:>10,d}")
    print("\n=== Task 5 Complete ===")
