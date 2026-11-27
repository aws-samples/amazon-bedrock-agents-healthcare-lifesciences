#!/usr/bin/env python3
"""Task 6: Transform PrimeKG + TCGA data into Neptune Analytics openCypher CSV format and upload to S3."""
import os, boto3, pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT_DIR = os.path.join(DATA_DIR, 'neptune')
import _config as C
C.require("BUCKET")
BUCKET = C.BUCKET
S3_PREFIX = 'neptune/'
REGION = C.REGION


def safe_type(t):
    return t.replace('/', '_')


def write_primekg_nodes():
    """Read all_nodes.csv, split by type, write one CSV per node type."""
    df = pd.read_csv(os.path.join(DATA_DIR, 'primekg', 'all_nodes.csv'))
    counts = {}
    for ntype, grp in df.groupby('type'):
        label = safe_type(ntype)
        out = pd.DataFrame({
            ':ID': 'primekg_' + grp['index'].astype(str),
            ':LABEL': label,
            'name:String': grp['name'].values,
            'source:String': grp['source'].values,
            'original_id:String': grp['id'].astype(str).values,
        })
        path = os.path.join(OUT_DIR, f'nodes_{label}.csv')
        out.to_csv(path, index=False)
        counts[label] = len(out)
        print(f"  nodes_{label}.csv: {len(out):,} nodes")
    return counts


def write_tcga_case_nodes():
    """Generate case node CSV from tcga_cases.csv."""
    df = pd.read_csv(os.path.join(DATA_DIR, 'gdc', 'tcga_cases.csv'))
    out = pd.DataFrame({
        ':ID': 'case_' + df['case_id'],
        ':LABEL': 'case',
        'tcga_barcode:String': df['tcga_barcode'],
        'project_id:String': df['project_id'],
        'gender:String': df['gender'],
        'race:String': df['race'],
        'ethnicity:String': df['ethnicity'],
        'vital_status:String': df['vital_status'],
        'days_to_death:String': df['days_to_death'].astype(str),
        'primary_diagnosis:String': df['primary_diagnosis'],
        'tumor_stage:String': df['tumor_stage'],
        'age_at_diagnosis:String': df['age_at_diagnosis'].astype(str),
    })
    path = os.path.join(OUT_DIR, 'nodes_case.csv')
    out.to_csv(path, index=False)
    print(f"  nodes_case.csv: {len(out):,} nodes")
    return {'case': len(out)}


def write_tcga_sample_nodes():
    """Generate sample node CSV from tcga_samples.csv."""
    df = pd.read_csv(os.path.join(DATA_DIR, 'gdc', 'tcga_samples.csv'))
    out = pd.DataFrame({
        ':ID': 'sample_' + df['sample_id'],
        ':LABEL': 'sample',
        'sample_barcode:String': df['sample_barcode'],
        'project_id:String': df['project_id'],
        'sample_type:String': df['sample_type'],
        'tissue_type:String': df['tissue_type'],
    })
    path = os.path.join(OUT_DIR, 'nodes_sample.csv')
    out.to_csv(path, index=False)
    print(f"  nodes_sample.csv: {len(out):,} nodes")
    return {'sample': len(out)}


def write_primekg_edges():
    """Read kg_giant.csv, deduplicate bidirectional edges, write one CSV per relation."""
    df = pd.read_csv(os.path.join(DATA_DIR, 'primekg', 'kg_giant.csv'))
    # Deduplicate: keep only edges where x_index < y_index
    df = df[df['x_index'] < df['y_index']].copy()
    counts = {}
    for rel, grp in df.groupby('relation'):
        out = pd.DataFrame({
            ':START_ID': 'primekg_' + grp['x_index'].astype(str),
            ':END_ID': 'primekg_' + grp['y_index'].astype(str),
            ':TYPE': rel,
            'display_relation:String': grp['display_relation'].values,
        })
        fname = f'edges_{rel}.csv'
        out.to_csv(os.path.join(OUT_DIR, fname), index=False)
        counts[rel] = len(out)
        print(f"  {fname}: {len(out):,} edges")
    return counts


def write_case_diagnosis_edges():
    """Generate case_has_diagnosis edges using tcga_to_mondo mapping."""
    cases = pd.read_csv(os.path.join(DATA_DIR, 'gdc', 'tcga_cases.csv'))
    mapping = pd.read_csv(os.path.join(DATA_DIR, 'mappings', 'tcga_to_mondo.csv'))
    merged = cases.merge(mapping[['project_id', 'primekg_index']], on='project_id', how='inner')
    out = pd.DataFrame({
        ':START_ID': 'case_' + merged['case_id'],
        ':END_ID': 'primekg_' + merged['primekg_index'].astype(str),
        ':TYPE': 'case_has_diagnosis',
    })
    path = os.path.join(OUT_DIR, 'edges_case_has_diagnosis.csv')
    out.to_csv(path, index=False)
    print(f"  edges_case_has_diagnosis.csv: {len(out):,} edges")
    return {'case_has_diagnosis': len(out)}


def write_sample_from_case_edges():
    """Generate sample_from_case edges."""
    df = pd.read_csv(os.path.join(DATA_DIR, 'gdc', 'tcga_samples.csv'))
    out = pd.DataFrame({
        ':START_ID': 'sample_' + df['sample_id'],
        ':END_ID': 'case_' + df['case_id'],
        ':TYPE': 'sample_from_case',
    })
    path = os.path.join(OUT_DIR, 'edges_sample_from_case.csv')
    out.to_csv(path, index=False)
    print(f"  edges_sample_from_case.csv: {len(out):,} edges")
    return {'sample_from_case': len(out)}


def upload_to_s3():
    """Upload all CSVs in OUT_DIR to S3."""
    s3 = boto3.client('s3', region_name=REGION)
    files = sorted(f for f in os.listdir(OUT_DIR) if f.endswith('.csv'))
    for f in files:
        key = S3_PREFIX + f
        s3.upload_file(os.path.join(OUT_DIR, f), BUCKET, key)
        print(f"  s3://{BUCKET}/{key}")
    return len(files)


if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    print("=== Task 6: Transform to Neptune openCypher CSV ===\n")

    print("--- PrimeKG Nodes ---")
    node_counts = write_primekg_nodes()

    print("\n--- TCGA Case Nodes ---")
    node_counts.update(write_tcga_case_nodes())

    print("\n--- TCGA Sample Nodes ---")
    node_counts.update(write_tcga_sample_nodes())

    print("\n--- PrimeKG Edges (deduplicated) ---")
    edge_counts = write_primekg_edges()

    print("\n--- Case → Diagnosis Edges ---")
    edge_counts.update(write_case_diagnosis_edges())

    print("\n--- Sample → Case Edges ---")
    edge_counts.update(write_sample_from_case_edges())

    print("\n--- Uploading to S3 ---")
    n_files = upload_to_s3()

    print(f"\n=== Summary ===")
    print(f"  Node types: {len(node_counts)}")
    for k, v in sorted(node_counts.items()):
        print(f"    {k}: {v:,}")
    print(f"  Total nodes: {sum(node_counts.values()):,}")
    print(f"  Edge types: {len(edge_counts)}")
    for k, v in sorted(edge_counts.items()):
        print(f"    {k}: {v:,}")
    print(f"  Total edges: {sum(edge_counts.values()):,}")
    print(f"  Files uploaded: {n_files}")
    print("\n=== Task 6 Complete ===")
