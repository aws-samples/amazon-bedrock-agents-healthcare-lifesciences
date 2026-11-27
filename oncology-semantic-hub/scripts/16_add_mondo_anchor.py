#!/usr/bin/env python3
"""Step 16: Anchor disease nodes with their canonical MONDO CURIE (reproducible loader).

WHY: the L3 multi-hop fix resolves a disease term (via ontology_lookup / OLS) to its MONDO id and
anchors the traversal on the SINGLE canonical graph node `(d:disease {mondo:'<CURIE>'})` — this kills
the disease-name fan-out (e.g. "glioblastoma" matches ~10 nodes) that made multi-hop counts wrong and
non-reproducible. That anchor requires a `mondo` property on the canonical disease nodes.

This script makes that graph enrichment REPRODUCIBLE from repo artifacts (previously applied ad-hoc):
it reads the committed mapping `evaluation/disease_mondo_map.csv` and SETs `d.mondo` on each named
canonical node. Idempotent (re-runnable). Dry-run by default.

Usage:
    python 16_add_mondo_anchor.py                    # dry-run: show what would be set
    python 16_add_mondo_anchor.py --apply            # write mondo onto the graph
    python 16_add_mondo_anchor.py --graph-id g-xxxx  # target a different Neptune graph
"""
import argparse
import _config as C
import csv
import json
from pathlib import Path

import boto3

_CSV = Path(__file__).resolve().parent.parent / "evaluation" / "disease_mondo_map.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph-id", default=C.GRAPH_ID or None, help="Neptune Analytics graph id")
    ap.add_argument("--region", default="us-west-2")
    ap.add_argument("--apply", action="store_true", help="write to the graph (default: dry-run)")
    a = ap.parse_args()

    rows = [r for r in csv.DictReader(_CSV.open()) if r.get("graph_node_name") and r.get("mondo_curie")]
    print(f"{len(rows)} canonical disease anchors from {_CSV.name} (apply={a.apply}):")

    neptune = boto3.client("neptune-graph", region_name=a.region)

    def run(q):
        return json.loads(neptune.execute_query(
            graphIdentifier=a.graph_id, queryString=q, language="OPEN_CYPHER")["payload"].read())["results"]

    applied = 0
    for r in rows:
        node, curie = r["graph_node_name"].replace("'", "\\'"), r["mondo_curie"]
        if a.apply:
            run(f"MATCH (d:disease {{name:'{node}'}}) SET d.mondo='{curie}' RETURN d.name")
            applied += 1
        print(f"  {'SET ' if a.apply else 'would set '}{r['graph_node_name']:40s} mondo={curie}")

    if a.apply:
        n = run("MATCH (d:disease) WHERE d.mondo IS NOT NULL RETURN count(d) AS n")[0]["n"]
        print(f"\napplied {applied}; disease nodes now carrying mondo: {n}")
    else:
        print("\n(dry-run — re-run with --apply to write)")


if __name__ == "__main__":
    main()
