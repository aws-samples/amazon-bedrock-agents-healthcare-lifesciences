#!/usr/bin/env python3
"""Add COSMIC Cancer Gene Census Tier 1 annotations to the knowledge graph.

1. Use a hardcoded representative subset of ~75 COSMIC CGC Tier 1 genes
2. Update Neptune gene_protein nodes with cosmic_tier=1 property (batched via UNWIND)
3. Print match count
4. Upload gene list CSV to S3
"""
import json, time, io, csv
import boto3

import _config as C
REGION = C.REGION
C.require("BUCKET", "GRAPH_ID")
BUCKET = C.BUCKET
GRAPH_ID = C.GRAPH_ID
MAX_SECONDS = 120

COSMIC_TIER1_GENES = [
    "TP53", "KRAS", "NRAS", "BRAF", "PIK3CA", "PTEN", "APC", "BRCA1", "BRCA2", "RB1",
    "EGFR", "MYC", "CDKN2A", "ATM", "NF1", "NF2", "VHL", "WT1", "RET", "KIT",
    "PDGFRA", "ALK", "MET", "FGFR1", "FGFR2", "FGFR3", "IDH1", "IDH2", "DNMT3A", "TET2",
    "JAK2", "MPL", "CALR", "NPM1", "FLT3", "RUNX1", "CEBPA", "KMT2A", "EZH2", "ASXL1",
    "SETBP1", "SF3B1", "SRSF2", "U2AF1", "ZRSR2", "STAG2", "RAD21", "SMC1A", "SMC3", "BCOR",
    "BCORL1", "PHF6", "EP300", "CREBBP", "ARID1A", "ARID2", "SMARCA4", "SMARCB1", "PBRM1", "BAP1",
    "CDH1", "CTNNB1", "AKT1", "ERBB2", "ERBB3", "MAP2K1", "MAP2K2", "HRAS", "FBXW7", "NOTCH1",
    "NOTCH2", "MED12", "SPOP", "FOXA1",
]

neptune = boto3.client("neptune-graph", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)


def update_neptune():
    print(f"\nStep 1: Updating Neptune with cosmic_tier=1 for {len(COSMIC_TIER1_GENES)} genes ...")
    batch_size = 10
    total_matched = 0
    matched_genes = []
    t0 = time.time()

    for i in range(0, len(COSMIC_TIER1_GENES), batch_size):
        if time.time() - t0 > MAX_SECONDS:
            print(f"  ⚠ Timeout after {MAX_SECONDS}s — stopping")
            break
        batch = COSMIC_TIER1_GENES[i : i + batch_size]
        items = ", ".join(f"'{g}'" for g in batch)
        cypher = (
            f"UNWIND [{items}] AS gene_name "
            "MATCH (g:gene_protein) WHERE g.name = gene_name "
            "SET g.cosmic_tier = 1 "
            "RETURN gene_name, g.name AS matched"
        )
        resp = neptune.execute_query(
            graphIdentifier=GRAPH_ID, queryString=cypher, language="OPEN_CYPHER"
        )
        result = json.loads(resp["payload"].read())["results"]
        n = len(result)
        matched_genes.extend(r["matched"] for r in result)
        total_matched += n
        elapsed = time.time() - t0
        print(f"  Batch {i // batch_size + 1}: {n}/{len(batch)} matched ({elapsed:.0f}s)")

    print(f"\n  Total genes matched in Neptune: {total_matched} / {len(COSMIC_TIER1_GENES)}")
    return total_matched, matched_genes


def upload_s3():
    print("\nStep 2: Uploading gene list to S3 ...")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["gene_symbol", "cosmic_tier"])
    for g in COSMIC_TIER1_GENES:
        writer.writerow([g, 1])
    s3.put_object(Bucket=BUCKET, Key="enrichment/cosmic_tier1_genes.csv", Body=buf.getvalue())
    print(f"  s3://{BUCKET}/enrichment/cosmic_tier1_genes.csv ({len(COSMIC_TIER1_GENES)} rows)")


if __name__ == "__main__":
    print("=" * 60)
    print("  14: Add COSMIC Cancer Gene Census Tier 1 to Knowledge Graph")
    print("=" * 60)

    total_matched, matched_genes = update_neptune()
    upload_s3()

    print(f"\n{'=' * 60}")
    print(f"  COSMIC Tier 1 genes in list:      {len(COSMIC_TIER1_GENES)}")
    print(f"  Genes matched in Neptune:          {total_matched}")
    if matched_genes:
        print(f"  Sample matched: {', '.join(matched_genes[:10])}")
    unmatched = set(COSMIC_TIER1_GENES) - set(matched_genes)
    if unmatched:
        print(f"  Unmatched ({len(unmatched)}): {', '.join(sorted(unmatched)[:15])}...")
    print(f"{'=' * 60}")
