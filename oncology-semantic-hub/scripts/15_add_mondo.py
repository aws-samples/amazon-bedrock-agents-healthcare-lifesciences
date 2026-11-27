#!/usr/bin/env python3
"""Step 15: Enrich disease nodes with MONDO ontology cross-references.

Re-authored loader for the enrichment the runbook flagged as "not checked in"
(docs/data-pipeline-rebuild.md §4.3): adds `icd10`, `ncit`, and `mondo_definition`
properties onto `:disease` nodes from the MONDO OBO release. Mirrors the batched-write
pattern of 11_add_clinvar.py / 14_add_cosmic.py.

1. Download the MONDO OBO (mondo.obo) if not cached
2. Parse [Term] stanzas → MONDO id, definition, xref ICD10:*, xref NCIT:*
3. Match to :disease nodes by their stored id (see --id-format)
4. Batched UNWIND SET into Neptune

Usage:
    python 15_add_mondo.py --dry-run                 # download+parse+report, no graph writes
    python 15_add_mondo.py                            # enrich (default: top --limit diseases)
    python 15_add_mondo.py --id-format number --limit 1000

--id-format controls how a MONDO term id is matched to `disease.original_id`, which depends on
how step 06 stored it: 'curie' = "MONDO:0007254", 'number' = "0007254", 'int' = "7254".
"""
import argparse
import os
import re
import subprocess
import time

import boto3

import _config as C

OBO_URL = "http://purl.obolibrary.org/obo/mondo.obo"
OBO_PATH = "/tmp/mondo.obo"
MAX_SECONDS = 300


def download_obo():
    if os.path.exists(OBO_PATH):
        print(f"  MONDO OBO already at {OBO_PATH} ({os.path.getsize(OBO_PATH)/1e6:.1f} MB)")
        return
    print(f"  downloading {OBO_URL} ...")
    subprocess.run(["wget", "-q", OBO_URL, "-O", OBO_PATH], check=True)
    print(f"  downloaded {os.path.getsize(OBO_PATH)/1e6:.1f} MB")


def parse_obo():
    """Yield dicts: {mondo_num, icd10, ncit, definition} for each MONDO [Term]."""
    terms = []
    cur = None
    with open(OBO_PATH) as f:
        for line in f:
            line = line.rstrip("\n")
            if line == "[Term]":
                if cur and cur.get("mondo_num"):
                    terms.append(cur)
                cur = {"mondo_num": None, "icd10": None, "ncit": None, "definition": None}
                continue
            if cur is None:
                continue
            if line.startswith("id: MONDO:"):
                cur["mondo_num"] = line.split("MONDO:")[1].strip()
            elif line.startswith("def: "):
                m = re.search(r'def:\s*"(.*?)"', line)
                if m:
                    cur["definition"] = m.group(1)
            elif line.startswith("xref: ICD10:") and not cur["icd10"]:
                cur["icd10"] = line.split("ICD10:")[1].split()[0].strip()
            elif line.startswith("xref: NCIT:") and not cur["ncit"]:
                cur["ncit"] = line.split("NCIT:")[1].split()[0].strip()
    if cur and cur.get("mondo_num"):
        terms.append(cur)
    return terms


def to_key(mondo_num: str, fmt: str) -> str:
    if fmt == "curie":
        return f"MONDO:{mondo_num}"
    if fmt == "number":
        return mondo_num
    if fmt == "int":
        return str(int(mondo_num))
    raise ValueError(fmt)


def esc(s):
    return str(s).replace("\\", "\\\\").replace("'", "\\'") if s is not None else ""


def update_neptune(rows, id_format, limit):
    ng = boto3.client("neptune-graph", region_name=C.REGION)
    rows = [r for r in rows if any((r["icd10"], r["ncit"], r["definition"]))][:limit]
    batch, total, t0 = 100, 0, time.time()
    for i in range(0, len(rows), batch):
        if time.time() - t0 > MAX_SECONDS:
            print(f"  ⚠ timeout after {MAX_SECONDS}s — stopping")
            break
        items = []
        for r in rows[i:i + batch]:
            items.append(
                f"{{mondo: '{esc(to_key(r['mondo_num'], id_format))}', "
                f"icd10: '{esc(r['icd10'])}', ncit: '{esc(r['ncit'])}', def: '{esc(r['definition'])[:1500]}'}}")
        cypher = (
            f"UNWIND [{', '.join(items)}] AS row "
            "MATCH (d:disease) WHERE d.original_id = row.mondo "
            "SET d.icd10 = row.icd10, d.ncit = row.ncit, d.mondo_definition = row.def "
            "RETURN count(d) AS updated")
        resp = ng.execute_query(graphIdentifier=C.GRAPH_ID, queryString=cypher, language="OPEN_CYPHER")
        import json as _json
        n = (_json.loads(resp["payload"].read())["results"] or [{"updated": 0}])[0]["updated"]
        total += n
        print(f"  batch {i//batch + 1}: {n} updated (cumulative {total}, {time.time()-t0:.0f}s)")
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id-format", choices=["curie", "number", "int"], default="curie")
    ap.add_argument("--limit", type=int, default=500, help="max disease terms to enrich")
    ap.add_argument("--dry-run", action="store_true", help="download+parse+report, no graph writes")
    args = ap.parse_args()

    print("=== Step 15: MONDO ontology enrichment ===")
    print(C.summary())

    if args.dry_run and not os.path.exists(OBO_PATH):
        print(f"\n[dry-run] would download {OBO_URL}, parse [Term] stanzas for ICD10/NCIT/def, "
              f"and enrich up to {args.limit} :disease nodes matched by original_id "
              f"(format={args.id_format}). No download or graph writes performed.")
        return

    download_obo()
    terms = parse_obo()
    enrichable = [t for t in terms if any((t["icd10"], t["ncit"], t["definition"]))]
    print(f"\nParsed {len(terms):,} MONDO terms; {len(enrichable):,} have icd10/ncit/definition.")
    ex = enrichable[0] if enrichable else None
    if ex:
        print(f"  example: MONDO:{ex['mondo_num']}  icd10={ex['icd10']} ncit={ex['ncit']} "
              f"key(--id-format={args.id_format})={to_key(ex['mondo_num'], args.id_format)}")

    if args.dry_run:
        print(f"\n[dry-run] would enrich up to {args.limit} :disease nodes matched by "
              f"original_id (format={args.id_format}). No graph writes.")
        return

    total = update_neptune(enrichable, args.id_format, args.limit)
    print(f"\nDisease nodes enriched: {total:,}")
    if total == 0:
        print("  0 matched — check --id-format matches how step 06 stored disease.original_id.")
    print("=== Step 15 complete ===")


if __name__ == "__main__":
    main()
