#!/usr/bin/env python3
"""Task 4: Extract GDC molecular data (mutations, CNV, expression) via analysis APIs → S3 Parquet."""
import os, json, requests, io, time
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import boto3

import _config as C
C.require("BUCKET")
BUCKET = C.BUCKET
REGION = C.REGION
BASE = "https://api.gdc.cancer.gov"
S3 = boto3.client('s3', region_name=REGION)

# Load TCGA project list from mapping file
MAP_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'mappings')
TCGA_PROJECTS = pd.read_csv(os.path.join(MAP_DIR, 'tcga_to_mondo.csv'))['project_id'].tolist()


def upload_parquet_to_s3(df, s3_key):
    """Write DataFrame as Parquet directly to S3."""
    buf = io.BytesIO()
    table = pa.Table.from_pandas(df)
    pq.write_table(table, buf, compression='snappy')
    buf.seek(0)
    S3.put_object(Bucket=BUCKET, Key=s3_key, Body=buf.getvalue())
    print(f"    → s3://{BUCKET}/{s3_key} ({len(df)} rows, {buf.tell()/1e6:.1f} MB)")


def extract_mutations_for_project(project_id):
    """Extract HIGH/MODERATE impact SSM occurrences for a project."""
    all_rows = []
    offset = 0
    filters = json.dumps({"op":"and","content":[
        {"op":"=","content":{"field":"case.project.project_id","value":project_id}},
        {"op":"in","content":{"field":"ssm.consequence.transcript.annotation.vep_impact",
                              "value":["HIGH","MODERATE"]}}
    ]})
    fields = ",".join([
        "ssm.ssm_id","ssm.chromosome","ssm.start_position","ssm.end_position",
        "ssm.reference_allele","ssm.tumor_allele","ssm.mutation_subtype",
        "ssm.consequence.transcript.gene.symbol",
        "ssm.consequence.transcript.gene.gene_id",
        "ssm.consequence.transcript.aa_change",
        "ssm.consequence.transcript.consequence_type",
        "ssm.consequence.transcript.annotation.vep_impact",
        "case.case_id","case.submitter_id"
    ])
    while True:
        resp = requests.get(f"{BASE}/ssm_occurrences", params={
            "filters": filters, "fields": fields,
            "size": 1000, "from": offset, "format": "json"
        })
        if resp.status_code != 200:
            print(f"    ⚠ HTTP {resp.status_code} at offset {offset}, retrying...")
            time.sleep(2)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
            continue
        data = resp.json()
        hits = data.get("data", {}).get("hits", [])
        if not hits:
            break
        for h in hits:
            ssm = h.get("ssm", {})
            case = h.get("case", {})
            # Get first consequence with gene info
            conseqs = ssm.get("consequence", [])
            gene_symbol, gene_id, aa_change, consequence_type, vep_impact = "", "", "", "", ""
            for c in (conseqs or []):
                t = c.get("transcript", {})
                g = t.get("gene", {})
                if g.get("symbol"):
                    gene_symbol = g["symbol"]
                    gene_id = g.get("gene_id", "")
                    aa_change = t.get("aa_change", "")
                    consequence_type = t.get("consequence_type", "")
                    vep_impact = t.get("annotation", {}).get("vep_impact", "")
                    break
            all_rows.append({
                "ssm_id": ssm.get("ssm_id", ""),
                "chromosome": ssm.get("chromosome", ""),
                "start_position": ssm.get("start_position"),
                "end_position": ssm.get("end_position"),
                "reference_allele": ssm.get("reference_allele", ""),
                "tumor_allele": ssm.get("tumor_allele", ""),
                "mutation_subtype": ssm.get("mutation_subtype", ""),
                "hugo_symbol": gene_symbol,
                "ensembl_gene_id": gene_id,
                "aa_change": aa_change,
                "consequence_type": consequence_type,
                "vep_impact": vep_impact,
                "case_id": case.get("case_id", ""),
                "submitter_id": case.get("submitter_id", ""),
                "project_id": project_id,
            })
        offset += 1000
        if offset % 5000 == 0:
            print(f"    {project_id}: {offset} ssm_occurrences fetched...")
        # Rate limiting
        if offset % 10000 == 0:
            time.sleep(1)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    return pd.DataFrame(all_rows)


def extract_cnv_for_project(project_id):
    """Extract gene-level CNV occurrences for a project."""
    all_rows = []
    offset = 0
    filters = json.dumps({"op":"and","content":[
        {"op":"=","content":{"field":"case.project.project_id","value":project_id}},
        {"op":"=","content":{"field":"cnv.gene_level_cn","value":"true"}}
    ]})
    fields = "cnv.cnv_id,cnv.chromosome,cnv.start_position,cnv.end_position,cnv.cnv_change,cnv.consequence.gene.symbol,case.case_id,case.submitter_id"
    while True:
        resp = requests.get(f"{BASE}/cnv_occurrences", params={
            "filters": filters, "fields": fields,
            "size": 1000, "from": offset, "format": "json"
        })
        if resp.status_code != 200:
            time.sleep(2)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
            continue
        hits = resp.json().get("data", {}).get("hits", [])
        if not hits:
            break
        for h in hits:
            cnv = h.get("cnv", {})
            case = h.get("case", {})
            gene_symbol = ""
            for c in (cnv.get("consequence") or []):
                g = c.get("gene", {})
                if g.get("symbol"):
                    gene_symbol = g["symbol"]
                    break
            all_rows.append({
                "cnv_id": cnv.get("cnv_id", ""),
                "chromosome": cnv.get("chromosome", ""),
                "start_position": cnv.get("start_position"),
                "end_position": cnv.get("end_position"),
                "cnv_change": cnv.get("cnv_change", ""),
                "hugo_symbol": gene_symbol,
                "case_id": case.get("case_id", ""),
                "submitter_id": case.get("submitter_id", ""),
                "project_id": project_id,
            })
        offset += 1000
        if offset % 5000 == 0:
            print(f"    {project_id}: {offset} cnv_occurrences fetched...")
        if offset % 10000 == 0:
            time.sleep(1)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    return pd.DataFrame(all_rows)


def extract_expression_for_project(project_id, case_ids, gene_ids):
    """Extract gene expression values for a project via /gene_expression/values."""
    # API accepts batches of case_ids + gene_ids
    batch_size = 50  # cases per batch
    all_rows = []
    for i in range(0, len(case_ids), batch_size):
        batch = case_ids[i:i+batch_size]
        try:
            resp = requests.post(f"{BASE}/gene_expression/values", json={
                "case_ids": batch,
                "gene_ids": gene_ids[:50],  # limit genes per request
                "tsv_units": "median_centered_log2_uqfpkm",
                "format": "tsv"
            }, timeout=60)
            if resp.status_code == 200 and resp.text.strip():
                lines = resp.text.strip().split('\n')
                if len(lines) > 1:
                    header = lines[0].split('\t')
                    for line in lines[1:]:
                        parts = line.split('\t')
                        gene = parts[0]
                        for j, val in enumerate(parts[1:], 1):
                            if j < len(header) and val and val != 'NaN':
                                try:
                                    all_rows.append({
                                        "case_id": header[j],
                                        "ensembl_gene_id": gene,
                                        "expression_value": float(val),
                                        "project_id": project_id,
                                    })
                                except (ValueError, IndexError):
                                    pass
        except Exception as e:
            print(f"    ⚠ Expression batch error: {e}")
        time.sleep(0.5)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    return pd.DataFrame(all_rows)


if __name__ == '__main__':
    print("=== Task 4: Extract GDC Molecular Data → S3 ===")
    print(f"  Bucket: s3://{BUCKET}")
    print(f"  Projects: {len(TCGA_PROJECTS)}")

    # --- Mutations ---
    print("\n=== 4a: Somatic Mutations (HIGH/MODERATE impact) ===")
    total_muts = 0
    for pid in TCGA_PROJECTS:
        print(f"  {pid}...")
        df = extract_mutations_for_project(pid)
        if len(df) > 0:
            upload_parquet_to_s3(df, f"lake/tcga_mutations/project_id={pid}/mutations.parquet")
            total_muts += len(df)
        else:
            print(f"    (no mutations)")
    print(f"  Total mutations: {total_muts}")

    # --- CNV (sample 3 projects for Sprint 1 — full extraction is very large) ---
    print("\n=== 4b: Copy Number Variations (gene-level, 3 projects) ===")
    total_cnv = 0
    for pid in TCGA_PROJECTS[:3]:  # BRCA, LUAD, GBM — start small
        print(f"  {pid}...")
        df = extract_cnv_for_project(pid)
        if len(df) > 0:
            upload_parquet_to_s3(df, f"lake/tcga_cna/project_id={pid}/cna.parquet")
            total_cnv += len(df)
    print(f"  Total CNV events: {total_cnv}")

    # --- Expression (sample: top 10 cancer genes, 3 projects) ---
    print("\n=== 4c: Gene Expression (sample: 3 projects, 10 genes) ===")
    TOP_GENES = [
        "ENSG00000141510",  # TP53
        "ENSG00000012048",  # BRCA1
        "ENSG00000139618",  # BRCA2
        "ENSG00000171862",  # PTEN
        "ENSG00000133703",  # KRAS
        "ENSG00000157764",  # BRAF
        "ENSG00000146648",  # EGFR
        "ENSG00000121879",  # PIK3CA
        "ENSG00000181143",  # MYC
        "ENSG00000136997",  # MYC (alt)
    ]
    cases_df = pd.read_csv(os.path.join(os.path.dirname(__file__), '..', 'data', 'gdc', 'tcga_cases.csv'))
    total_expr = 0
    for pid in TCGA_PROJECTS[:3]:
        print(f"  {pid}...")
        proj_cases = cases_df[cases_df['project_id'] == pid]['case_id'].tolist()[:200]
        df = extract_expression_for_project(pid, proj_cases, TOP_GENES)
        if len(df) > 0:
            upload_parquet_to_s3(df, f"lake/tcga_expression/project_id={pid}/expression.parquet")
            total_expr += len(df)
    print(f"  Total expression values: {total_expr}")

    print("\n=== Task 4 Complete ===")
    print(f"  Mutations: {total_muts} rows across {len(TCGA_PROJECTS)} projects")
    print(f"  CNV: {total_cnv} rows across 3 projects")
    print(f"  Expression: {total_expr} rows across 3 projects")
