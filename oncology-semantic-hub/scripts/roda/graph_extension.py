"""Reusable graph extension: CIViC -> Oncology TA Extension (`ta_oncology`) in Neptune, per Research Technical
Specs §2.1/§3. Adds **CancerBiomarker** nodes + **predicts_response_to** edges that BRIDGE to the PrimeKG core
(`gene_protein {name}`, `drug {name}`) by shared IDs — **the core is never mutated**. Everything is tagged
`partition='ta_oncology'` so the whole extension is **droppable** (rollback).

Two-tier: this is the *relationships* layer; full evidence detail stays in the `civic_evidence` Athena table.

SAFE BY DEFAULT: --dry-run (reads civic_evidence + core, prints what WOULD be written, NO graph writes).
    python scripts/roda/graph_extension.py --gene EGFR              # dry-run (demo scope)
    python scripts/roda/graph_extension.py --gene EGFR --apply      # write extension
    python scripts/roda/graph_extension.py --drop                   # rollback: delete the ta_oncology extension
"""
import argparse

import boto3
import pyarrow.parquet as pq
import pyarrow.fs as pafs

import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import _config as C
C.require("GRAPH_ID", "BUCKET")
GRAPH_ID = C.GRAPH_ID
REGION = C.REGION
CIVIC_PARQUET = f"{C.BUCKET}/roda/civic_evidence/civic_evidence.parquet"
PARTITION = "ta_oncology"
_g = boto3.client("neptune-graph", region_name=REGION)


def _q(qs, params=None):
    import json
    r = _g.execute_query(graphIdentifier=GRAPH_ID, queryString=qs, language="OPEN_CYPHER",
                         parameters=params or {})
    return json.loads(r["payload"].read())


def _direction(sig: str) -> str:
    s = (sig or "").lower()
    return "sensitive" if ("sensitiv" in s or "response" in s) else ("resistant" if "resist" in s else "unknown")


def _ther(v):
    """parquet list columns come back as numpy arrays; normalize to a python list."""
    if v is None:
        return []
    try:
        return [t for t in v]
    except TypeError:
        return []


def load_civic():
    fs = pafs.S3FileSystem(region=REGION)
    return pq.read_table(CIVIC_PARQUET, filesystem=fs).to_pandas()


def core_names(label):
    rows = _q(f"MATCH (n:{label}) RETURN n.name AS name")["results"]
    return {r["name"] for r in rows if r.get("name")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gene", default="EGFR", help="gene filter for the extension ('ALL' for everything)")
    ap.add_argument("--apply", action="store_true", help="write the extension to Neptune (default: dry-run)")
    ap.add_argument("--drop", action="store_true", help="ROLLBACK: delete the whole ta_oncology extension")
    a = ap.parse_args()

    if a.drop:
        if not a.apply:
            print("[DRY-RUN] would delete all nodes with partition='%s' (CancerBiomarker). Add --apply to execute." % PARTITION)
            return
        r = _q("MATCH (n:CancerBiomarker {partition:$p}) DETACH DELETE n RETURN count(n) AS n", {"p": PARTITION})
        print("[APPLY] dropped ta_oncology extension:", r["results"])
        return

    df = load_civic()
    if a.gene.upper() != "ALL":
        wanted = {g.strip().upper() for g in a.gene.split(",")}
        df = df[df.gene.str.upper().isin(wanted)]
    genes = core_names("gene_protein")
    drugs = core_names("drug")
    # bridge only where the core gene exists; count therapy edges that hit core drugs
    df = df[df.gene.isin(genes)]
    n_edges = sum(1 for _, r in df.iterrows() for t in _ther(r["therapies"]) if t in drugs)
    print(f"CIViC rows (gene in core): {len(df)} | biomarker nodes: {df['evidence_id'].nunique() if 'evidence_id' in df else len(df)}")
    print(f"predicts_response_to edges to CORE drugs: {n_edges} | core untouched (MATCH only)")
    print(f"sample:")
    for _, r in df.head(5).iterrows():
        drg = [t for t in _ther(r["therapies"]) if t in drugs]
        print(f"  {r['gene']} {r['variant']} [{r['evidence_level']}/{_direction(r['significance'])}] -> {drg or '(no core drug)'}  PMID:{r['citation_id']}")

    if not a.apply:
        print("\n[DRY-RUN] no graph writes. Re-run with --apply to create the ta_oncology extension.")
        return

    made_n = made_e = 0
    for _, r in df.iterrows():
        bid = f"civic:{r.get('evidence_id') or (r['gene'] + ':' + str(r['variant']))}"
        _q("""MERGE (b:CancerBiomarker {biomarker_id:$bid})
              SET b.partition=$p, b.source='CIViC', b.source_snapshot=$snap, b.gene=$gene, b.variant=$variant
              WITH b MATCH (g:gene_protein {name:$gene}) MERGE (b)-[e:BIOMARKER_OF_GENE]->(g) SET e.partition=$p""",
           {"bid": bid, "p": PARTITION, "snap": str(r.get("source_snapshot", "")), "gene": r["gene"],
            "variant": str(r["variant"])})
        made_n += 1
        for t in _ther(r["therapies"]):
            if t in drugs:
                _q("""MATCH (b:CancerBiomarker {biomarker_id:$bid}), (d:drug {name:$t})
                      MERGE (b)-[r2:PREDICTS_RESPONSE_TO]->(d)
                      SET r2.partition=$p, r2.direction=$dir, r2.evidence_level=$lvl, r2.pmid=$pmid, r2.disease=$disease""",
                   {"bid": bid, "t": t, "p": PARTITION, "dir": _direction(r["significance"]),
                    "lvl": r["evidence_level"], "pmid": str(r["citation_id"]), "disease": r["disease"]})
                made_e += 1
    print(f"[APPLY] upserted {made_n} CancerBiomarker nodes + {made_e} predicts_response_to edges (partition={PARTITION}); core untouched.")


if __name__ == "__main__":
    main()
