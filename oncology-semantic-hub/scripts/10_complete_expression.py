#!/usr/bin/env python3
"""Complete expression data for remaining TCGA studies via cBioPortal API.

Discovers all *_tcga studies, skips the 10 already loaded, fetches expression
z-scores for 10 driver genes, and writes Parquet per study to S3.
"""
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
TIMEOUT = 30  # seconds per API call

ALREADY_DONE = {
    "brca_tcga", "luad_tcga", "gbm_tcga", "ov_tcga", "coadread_tcga",
    "ucec_tcga", "hnsc_tcga", "lihc_tcga", "stad_tcga", "skcm_tcga",
}

GENE_IDS = [7157, 672, 675, 5728, 3845, 673, 1956, 5290, 4893, 7428]


def discover_studies():
    r = requests.get(f"{BASE}/studies?keyword=tcga&projection=SUMMARY",
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return sorted(
        s["studyId"] for s in r.json()
        if s["studyId"].endswith("_tcga") and s["studyId"] not in ALREADY_DONE
    )


def fetch_expression(study):
    """Try rna_seq_v2 z-scores, fall back to rna_seq z-scores. Returns DataFrame or None."""
    body = {"sampleListId": f"{study}_all", "entrezGeneIds": GENE_IDS}
    for suffix in ("rna_seq_v2_mrna_median_Zscores", "rna_seq_mrna_median_Zscores"):
        profile = f"{study}_{suffix}"
        try:
            r = requests.post(
                f"{BASE}/molecular-profiles/{profile}/molecular-data/fetch?projection=SUMMARY",
                json=body, headers=HEADERS, timeout=TIMEOUT,
            )
            if r.status_code == 404:
                continue
            r.raise_for_status()
            data = r.json()
            if not data:
                continue
            print(f"    profile: {profile}")
            return pd.DataFrame([{
                "sample_id": rec["sampleId"],
                "hugo_symbol": rec.get("gene", {}).get("hugoGeneSymbol", ""),
                "entrez_gene_id": rec["entrezGeneId"],
                "value": rec["value"],
                "project_id": study,
            } for rec in data])
        except requests.exceptions.Timeout:
            print(f"    ⚠ timeout on {profile}")
            continue
        except requests.RequestException as e:
            print(f"    ⚠ {e}")
            continue
    return None


def upload_parquet(df, key):
    buf = io.BytesIO()
    pq.write_table(pa.Table.from_pandas(df), buf, compression="snappy")
    buf.seek(0)
    S3.put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    print(f"    → s3://{BUCKET}/{key} ({len(df)} rows)")


if __name__ == "__main__":
    print("=== Complete expression data for remaining TCGA studies ===\n")

    studies = discover_studies()
    print(f"Found {len(studies)} remaining TCGA studies:\n  {', '.join(studies)}\n")

    results = []  # (study, rows, status)
    total_rows = 0

    for i, study in enumerate(studies, 1):
        print(f"  [{i}/{len(studies)}] {study}")
        t0 = time.time()
        try:
            df = fetch_expression(study)
            elapsed = time.time() - t0
            if elapsed > 60:
                print(f"    ⚠ skipped (took {elapsed:.0f}s > 60s limit)")
                results.append((study, 0, "timeout"))
                continue
            if df is not None and len(df):
                upload_parquet(
                    df,
                    f"lake/tcga_expression/source=cbioportal/project_id={study}/expression.parquet",
                )
                total_rows += len(df)
                results.append((study, len(df), "OK"))
            else:
                print("    ⚠ no expression profile found")
                results.append((study, 0, "no_profile"))
        except Exception as e:
            print(f"    ✗ ERROR: {e}")
            results.append((study, 0, f"error"))
        time.sleep(1)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)

    # --- Summary ---
    print(f"\n{'='*55}")
    print(f"  {'Study':<25s} {'Rows':>8s}  Status")
    print(f"  {'-'*25} {'-'*8}  {'-'*15}")
    for study, rows, status in results:
        print(f"  {study:<25s} {rows:>8,d}  {status}")
    print(f"  {'-'*25} {'-'*8}")
    print(f"  {'TOTAL':<25s} {total_rows:>8,d}")
    ok = sum(1 for _, _, s in results if s == "OK")
    noprof = sum(1 for _, _, s in results if s == "no_profile")
    print(f"\n  {ok} OK / {noprof} no_profile / {len(results)-ok-noprof} other")
    print("=== Done ===")
