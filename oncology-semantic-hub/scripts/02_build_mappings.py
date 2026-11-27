#!/usr/bin/env python3
"""Task 2: Build ID mappings — TCGA project→MONDO disease, Hugo Symbol→Entrez Gene ID."""
import os, requests, json, pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
MAP_DIR = os.path.join(BASE_DIR, 'data', 'mappings')
PRIMEKG_NODES = os.path.join(BASE_DIR, 'data', 'primekg', 'all_nodes.csv')

def build_tcga_to_mondo():
    """Fetch TCGA projects from GDC, then map to MONDO IDs in PrimeKG."""
    print("\n=== Step 1: Fetch TCGA projects from GDC ===")
    url = "https://api.gdc.cancer.gov/projects"
    params = {
        "filters": json.dumps({"op":"=","content":{"field":"program.name","value":"TCGA"}}),
        "fields": "project_id,name,disease_type,primary_site",
        "size": 100, "format": "json"
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    projects = resp.json()["data"]["hits"]
    print(f"  Found {len(projects)} TCGA projects")

    print("\n=== Step 2: Match to PrimeKG disease nodes ===")
    nodes = pd.read_csv(PRIMEKG_NODES)
    diseases = nodes[nodes['type'] == 'disease'][['index','id','name']].copy()
    diseases['name_lower'] = diseases['name'].str.lower().str.strip()

    # Manual mapping — TCGA disease types to MONDO names in PrimeKG
    # Built by matching GDC disease_type to PrimeKG disease names
    MANUAL_MAP = {
        "TCGA-ACC": "adrenal cortex carcinoma",
        "TCGA-BLCA": "urinary bladder cancer",
        "TCGA-BRCA": "breast carcinoma",
        "TCGA-CESC": "cervical cancer",
        "TCGA-CHOL": "cholangiocarcinoma",
        "TCGA-COAD": "colon adenocarcinoma",
        "TCGA-DLBC": "diffuse large B-cell lymphoma",
        "TCGA-ESCA": "esophageal carcinoma",
        "TCGA-GBM": "glioblastoma",
        "TCGA-HNSC": "head and neck squamous cell carcinoma",
        "TCGA-KICH": "chromophobe renal cell carcinoma",
        "TCGA-KIRC": "clear cell renal carcinoma",
        "TCGA-KIRP": "papillary renal cell carcinoma",
        "TCGA-LAML": "acute myeloid leukemia",
        "TCGA-LGG": "lower grade glioma",
        "TCGA-LIHC": "hepatocellular carcinoma",
        "TCGA-LUAD": "lung adenocarcinoma",
        "TCGA-LUSC": "lung squamous cell carcinoma",
        "TCGA-MESO": "mesothelioma",
        "TCGA-OV": "ovarian carcinoma",
        "TCGA-PAAD": "pancreatic adenocarcinoma",
        "TCGA-PCPG": "pheochromocytoma",
        "TCGA-PRAD": "prostate adenocarcinoma",
        "TCGA-READ": "rectal adenocarcinoma",
        "TCGA-SARC": "sarcoma",
        "TCGA-SKCM": "melanoma",
        "TCGA-STAD": "stomach carcinoma",
        "TCGA-TGCT": "testicular germ cell cancer",
        "TCGA-THCA": "thyroid carcinoma",
        "TCGA-THYM": "thymoma",
        "TCGA-UCEC": "endometrial carcinoma",
        "TCGA-UCS": "uterine carcinosarcoma",
        "TCGA-UVM": "uveal melanoma",
    }

    rows = []
    matched = 0
    for proj in sorted(projects, key=lambda x: x['project_id']):
        pid = proj['project_id']
        search_name = MANUAL_MAP.get(pid)
        if not search_name:
            dt = proj.get('disease_type', '')
            search_name = (dt[0] if isinstance(dt, list) and dt else str(dt)).lower()
        match = diseases[diseases['name_lower'].str.contains(search_name.lower(), na=False)]
        dt_str = proj.get('disease_type','')
        dt_str = dt_str[0] if isinstance(dt_str, list) and dt_str else str(dt_str)
        if len(match) > 0:
            best = match.iloc[0]
            rows.append({'project_id': pid, 'disease_type': dt_str,
                         'mondo_id': best['id'], 'mondo_name': best['name'],
                         'primekg_index': int(best['index'])})
            matched += 1
        else:
            # Try fuzzy: first word match
            words = search_name.split()
            for w in words:
                if len(w) > 4:
                    match2 = diseases[diseases['name_lower'].str.contains(w, na=False)]
                    if len(match2) > 0:
                        best = match2.iloc[0]
                        rows.append({'project_id': pid, 'disease_type': dt_str,
                                     'mondo_id': best['id'], 'mondo_name': best['name'],
                                     'primekg_index': int(best['index'])})
                        matched += 1
                        break
            else:
                rows.append({'project_id': pid, 'disease_type': dt_str,
                             'mondo_id': '', 'mondo_name': '', 'primekg_index': -1})
                print(f"  ⚠ No match for {pid}: {search_name}")

    df = pd.DataFrame(rows)
    path = os.path.join(MAP_DIR, 'tcga_to_mondo.csv')
    df.to_csv(path, index=False)
    print(f"\n  ✓ Mapped {matched}/{len(projects)} projects → MONDO")
    print(f"  Saved to {path}")
    return df

def build_hugo_to_entrez():
    """Download HGNC gene name mapping."""
    print("\n=== Step 3: Download HGNC Hugo→Entrez mapping ===")
    url = "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt"
    print(f"  Downloading from {url}...")
    hgnc = pd.read_csv(url, sep='\t', usecols=['symbol','entrez_id','name','locus_group'],
                        low_memory=False)
    hgnc = hgnc[hgnc['entrez_id'].notna()].copy()
    hgnc['entrez_id'] = hgnc['entrez_id'].astype(int)
    path = os.path.join(MAP_DIR, 'hugo_to_entrez.csv')
    hgnc.to_csv(path, index=False)
    print(f"  ✓ {len(hgnc)} genes mapped (Hugo Symbol → Entrez ID)")
    print(f"  Saved to {path}")

    # Verify overlap with PrimeKG gene nodes
    nodes = pd.read_csv(PRIMEKG_NODES)
    primekg_genes = nodes[nodes['type'] == 'gene/protein']
    primekg_entrez = set(primekg_genes['id'].astype(str))
    hgnc_entrez = set(hgnc['entrez_id'].astype(str))
    overlap = primekg_entrez & hgnc_entrez
    print(f"  PrimeKG genes: {len(primekg_genes)}, HGNC genes: {len(hgnc)}, overlap: {len(overlap)}")
    return hgnc

if __name__ == '__main__':
    os.makedirs(MAP_DIR, exist_ok=True)
    print("=== Task 2: Build ID Mappings ===")
    tcga_mondo = build_tcga_to_mondo()
    print(tcga_mondo[['project_id','mondo_name','mondo_id']].to_string())
    hgnc = build_hugo_to_entrez()
    print("\n=== Task 2 Complete ===")
