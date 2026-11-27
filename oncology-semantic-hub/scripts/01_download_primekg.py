#!/usr/bin/env python3
"""Task 1: Download PrimeKG from Harvard Dataverse and explore schema."""
import os, sys, requests, pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'primekg')
KG_FILE = os.path.join(DATA_DIR, 'kg_giant.csv')
# Harvard Dataverse file IDs for PrimeKG
FILES = {
    'kg_giant.csv': '6180620',
    'drug_features.csv': '6180618',
    'disease_features.csv': '6180619',
}

def download():
    os.makedirs(DATA_DIR, exist_ok=True)
    for fname, fid in FILES.items():
        path = os.path.join(DATA_DIR, fname)
        if os.path.exists(path):
            print(f"  ✓ {fname} already exists ({os.path.getsize(path)/1e6:.1f} MB)")
            continue
        url = f"https://dataverse.harvard.edu/api/access/datafile/{fid}"
        print(f"  Downloading {fname}...")
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  ✓ {fname} ({os.path.getsize(path)/1e6:.1f} MB)")

def explore():
    print("\n=== Loading PrimeKG ===")
    kg = pd.read_csv(KG_FILE, low_memory=False)
    print(f"Shape: {kg.shape}")
    print(f"Columns: {list(kg.columns)}")

    # Extract unique nodes
    nx = kg[['x_index','x_id','x_type','x_name','x_source']].drop_duplicates(subset='x_index')
    ny = kg[['y_index','y_id','y_type','y_name','y_source']].drop_duplicates(subset='y_index')
    nx.columns = ny.columns = ['index','id','type','name','source']
    nodes = pd.concat([nx, ny]).drop_duplicates(subset='index')

    print(f"\n=== Nodes: {len(nodes)} unique ===")
    print(nodes['type'].value_counts().to_string())

    print(f"\n=== Edges: {len(kg)} total ===")
    print(kg['relation'].value_counts().to_string())

    print(f"\n=== Sample edges ===")
    print(kg[['x_type','relation','y_type','x_name','y_name']].head(5).to_string())

    # Save node summary for later tasks
    nodes.to_csv(os.path.join(DATA_DIR, 'all_nodes.csv'), index=False)
    print(f"\n✓ Saved all_nodes.csv ({len(nodes)} nodes)")
    return nodes, kg

if __name__ == '__main__':
    print("=== Task 1: Download PrimeKG ===")
    download()
    nodes, kg = explore()
    print("\n=== Task 1 Complete ===")
