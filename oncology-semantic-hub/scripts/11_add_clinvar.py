#!/usr/bin/env python3
"""Sprint 2 Task S2-2: Add ClinVar variant annotations to the knowledge graph.

1. Download ClinVar variant_summary.txt.gz
2. Filter to GRCh38 + Pathogenic/Likely pathogenic
3. Group by GeneID → count pathogenic variants, keep top ClinicalSignificance
4. Match to PrimeKG gene/protein nodes
5. Update Neptune node properties in batches (max 500 genes, 5-min timeout)
6. Upload summary CSV to S3
"""
import json, os, subprocess, time
import boto3, pandas as pd

import _config as C
REGION = C.REGION
C.require("BUCKET", "GRAPH_ID")
BUCKET = C.BUCKET
GRAPH_ID = C.GRAPH_ID
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CLINVAR_GZ = "/tmp/variant_summary.txt.gz"
MAX_GENES = 500
MAX_SECONDS = 300  # 5-minute timeout

neptune = boto3.client("neptune-graph", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)


def download_clinvar():
    print("Step 1: Downloading ClinVar variant_summary.txt.gz ...")
    if os.path.exists(CLINVAR_GZ):
        print(f"  Already exists at {CLINVAR_GZ}, skipping")
    else:
        subprocess.run(
            ["wget", "-q", "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz",
             "-O", CLINVAR_GZ],
            check=True,
        )
        print(f"  Downloaded {os.path.getsize(CLINVAR_GZ) / 1e6:.1f} MB")


def parse_and_filter():
    print("\nStep 2-3: Parsing, filtering, and grouping ClinVar ...")
    df = pd.read_csv(CLINVAR_GZ, sep="\t", compression="gzip", low_memory=False)
    print(f"  Raw rows: {len(df):,}")

    # Filter: GRCh38 assembly
    df = df[df["Assembly"] == "GRCh38"]
    print(f"  After GRCh38 filter: {len(df):,}")

    # Filter: Pathogenic or Likely pathogenic
    mask = df["ClinicalSignificance"].str.contains("Pathogenic|Likely pathogenic", case=False, na=False)
    df = df[mask].copy()
    print(f"  After pathogenic filter: {len(df):,}")
    total_pathogenic = len(df)

    # Drop rows without valid GeneID
    df = df[df["GeneID"] != -1].dropna(subset=["GeneID"])
    df["GeneID"] = df["GeneID"].astype(int)

    # Group by GeneID: count + top significance
    summary = (
        df.groupby("GeneID")
        .agg(
            pathogenic_count=("ClinicalSignificance", "size"),
            top_significance=("ClinicalSignificance", "first"),
            gene_symbol=("GeneSymbol", "first"),
        )
        .reset_index()
        .sort_values("pathogenic_count", ascending=False)
    )
    print(f"  Genes with pathogenic variants: {len(summary):,}")
    return summary, total_pathogenic


def match_primekg(summary):
    print("\nStep 4: Matching to PrimeKG gene/protein nodes ...")
    nodes = pd.read_csv(os.path.join(DATA_DIR, "primekg", "all_nodes.csv"))
    genes = nodes[nodes["type"] == "gene/protein"][["id"]].copy()
    genes["id"] = genes["id"].astype(int)

    matched = summary.merge(genes, left_on="GeneID", right_on="id", how="inner").drop(columns=["id"])
    print(f"  Matched {len(matched):,} / {len(summary):,} genes to PrimeKG")
    return matched


def update_neptune(matched):
    print(f"\nStep 5: Updating Neptune (max {MAX_GENES} genes, {MAX_SECONDS}s timeout) ...")
    rows = matched.head(MAX_GENES).to_dict("records")
    batch_size = 100
    total_updated = 0
    t0 = time.time()

    for i in range(0, len(rows), batch_size):
        if time.time() - t0 > MAX_SECONDS:
            print(f"  ⚠ Timeout after {MAX_SECONDS}s — stopping")
            break
        batch = rows[i : i + batch_size]
        items = []
        for r in batch:
            eid = str(int(r["GeneID"]))
            sig = str(r["top_significance"]).replace("'", "\\'")
            cnt = int(r["pathogenic_count"])
            items.append(f"{{eid: '{eid}', cnt: {cnt}, sig: '{sig}'}}")
        cypher = (
            f"UNWIND [{', '.join(items)}] AS row "
            "MATCH (g:gene_protein) WHERE g.original_id = row.eid "
            "SET g.clinvar_pathogenic_count = row.cnt, g.clinvar_top_significance = row.sig "
            "RETURN count(g) AS updated"
        )
        resp = neptune.execute_query(
            graphIdentifier=GRAPH_ID, queryString=cypher, language="OPEN_CYPHER"
        )
        result = json.loads(resp["payload"].read())["results"]
        n = result[0]["updated"] if result else 0
        total_updated += n
        elapsed = time.time() - t0
        print(f"  Batch {i // batch_size + 1}: {n} updated (cumulative {total_updated}, {elapsed:.0f}s)")

    print(f"  Total Neptune nodes updated: {total_updated}")
    return total_updated


def upload_s3(summary):
    print("\nStep 6: Uploading summary to S3 ...")
    path = "/tmp/clinvar_gene_summary.csv"
    summary.to_csv(path, index=False)
    s3.upload_file(path, BUCKET, "enrichment/clinvar_gene_summary.csv")
    print(f"  s3://{BUCKET}/enrichment/clinvar_gene_summary.csv ({len(summary):,} rows)")


if __name__ == "__main__":
    print("=" * 60)
    print("  S2-2: Add ClinVar Annotations to Knowledge Graph")
    print("=" * 60)

    download_clinvar()
    summary, total_pathogenic = parse_and_filter()
    matched = match_primekg(summary)
    upload_s3(summary)
    total_updated = update_neptune(matched)

    print(f"\n{'=' * 60}")
    print(f"  Total pathogenic variants found:  {total_pathogenic:,}")
    print(f"  Genes matched to PrimeKG:         {len(matched):,}")
    print(f"  Genes updated in Neptune:         {total_updated:,}")
    print(f"{'=' * 60}")
