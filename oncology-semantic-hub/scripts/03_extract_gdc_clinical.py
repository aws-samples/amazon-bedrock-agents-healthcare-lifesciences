#!/usr/bin/env python3
"""Task 3: Extract GDC clinical + biospecimen data for all TCGA cases."""
import os, json, requests, pandas as pd

BASE = "https://api.gdc.cancer.gov"
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'gdc')
FIELDS = ",".join([
    "case_id", "submitter_id", "project.project_id",
    "demographic.gender", "demographic.race", "demographic.ethnicity",
    "demographic.vital_status", "demographic.days_to_death",
    "diagnoses.primary_diagnosis", "diagnoses.tumor_stage",
    "diagnoses.age_at_diagnosis", "diagnoses.morphology",
    "diagnoses.site_of_resection_or_biopsy",
    "samples.sample_id", "samples.submitter_id",
    "samples.sample_type", "samples.tumor_descriptor", "samples.tissue_type"
])

def extract_cases():
    print("=== Fetching TCGA cases from GDC API ===")
    all_cases = []
    offset = 0
    filters = json.dumps({"op":"=","content":{"field":"project.program.name","value":"TCGA"}})
    while True:
        resp = requests.get(f"{BASE}/cases", params={
            "filters": filters, "fields": FIELDS,
            "size": 500, "from": offset, "format": "json"
        })
        resp.raise_for_status()
        hits = resp.json()["data"]["hits"]
        if not hits:
            break
        all_cases.extend(hits)
        offset += 500
        if offset % 2000 == 0:
            print(f"  Fetched {len(all_cases)} cases...")
    print(f"  Total: {len(all_cases)} TCGA cases")
    return all_cases

def flatten(all_cases):
    cases_rows, samples_rows = [], []
    for c in all_cases:
        pid = c.get("project", {}).get("project_id", "")
        demo = c.get("demographic", {}) or {}
        diags = c.get("diagnoses") or []
        diag = diags[0] if diags else {}

        cases_rows.append({
            "case_id": c["case_id"],
            "tcga_barcode": c.get("submitter_id", ""),
            "project_id": pid,
            "gender": demo.get("gender", ""),
            "race": demo.get("race", ""),
            "ethnicity": demo.get("ethnicity", ""),
            "vital_status": demo.get("vital_status", ""),
            "days_to_death": demo.get("days_to_death"),
            "primary_diagnosis": diag.get("primary_diagnosis", ""),
            "tumor_stage": diag.get("tumor_stage", ""),
            "age_at_diagnosis": diag.get("age_at_diagnosis"),
        })
        for s in (c.get("samples") or []):
            samples_rows.append({
                "sample_id": s["sample_id"],
                "sample_barcode": s.get("submitter_id", ""),
                "case_id": c["case_id"],
                "project_id": pid,
                "sample_type": s.get("sample_type", ""),
                "tissue_type": s.get("tissue_type", ""),
            })

    cases_df = pd.DataFrame(cases_rows)
    samples_df = pd.DataFrame(samples_rows)
    return cases_df, samples_df

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=== Task 3: Extract GDC Clinical Data ===")
    all_cases = extract_cases()

    # Save raw JSON
    with open(os.path.join(DATA_DIR, 'tcga_cases_raw.json'), 'w') as f:
        json.dump(all_cases, f)

    cases_df, samples_df = flatten(all_cases)
    cases_df.to_csv(os.path.join(DATA_DIR, 'tcga_cases.csv'), index=False)
    samples_df.to_csv(os.path.join(DATA_DIR, 'tcga_samples.csv'), index=False)

    print(f"\n=== Results ===")
    print(f"  Cases: {len(cases_df)}")
    print(f"  Samples: {len(samples_df)}")
    print(f"  Projects: {cases_df['project_id'].nunique()}")
    print(f"\n  Cases per project (top 10):")
    print(cases_df['project_id'].value_counts().head(10).to_string())
    print(f"\n  Sample types:")
    print(samples_df['sample_type'].value_counts().to_string())
    print("\n=== Task 3 Complete ===")
