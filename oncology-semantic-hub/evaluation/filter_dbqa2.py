"""Filter LABBench2 DbQA2 to our hub/Biomni coverage and format into the
AgentCore-compatible golden dataset schema (Tier 1: public database access).

⛔ STATUS: NOT YET WIRED INTO EITHER EVALUATION PATH (Phase 3 — Biomni). This is a
standalone prep script: run manually, it writes `golden_dataset_tier1.json`, but no
runner reads that file yet (`run_evaluation.py` / `run_agentcore_eval.py` /
`run_l1_l3_compare.py` all use `golden_dataset.json`). Tier 1 is scored only once the
Biomni Gateway tools exist; until then the source filter below is a heuristic.

DbQA2 (EdisonScientific/labbench2, gated — requires `hf auth login`) is a
breadth benchmark: 86 questions across 43 public bio-databases, 2 per source,
all is_opensource=False with a contamination canary. Each item is a pure
single-database lookup with a structured `ideal` answer and optional
`answer_regex`/`validator_params` for deterministic validation.

We keep the subset whose source is plausibly covered by the semantic hub or the
Biomni tool set. NOTE: this is a SOURCE-NAME heuristic. Once the actual Biomni
Gateway tool inventory is known, re-run with --biomni-tools to filter precisely.

Usage:
    python -m evaluation.filter_dbqa2               # writes golden_dataset_tier1.json
    python -m evaluation.filter_dbqa2 --all         # keep all 86 (no source filter)
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

from datasets import load_dataset

from . import config

# Sources covered by the semantic hub today (Neptune/Athena/ontology) or by
# common Biomni public-DB tools. Matched case-insensitively as substrings.
HUB_BIOMNI_SOURCES = [
    "TCGA", "ClinVar", "Open Targets", "UniProt", "Reactome", "STRING",
    "PDB", "Ensembl", "dbSNP", "GnomAD", "gnomAD", "KEGG", "ChEMBL", "GTEx",
    "GWAS Catalog", "1000 Genomes", "NCBI Genomes", "RefSeq", "GtoPdb",
    "Gene Ontology", "OMIM", "Monarch", "GenBank", "ENA",
]


def _source_is_relevant(sources: list[str]) -> list[str]:
    hits = []
    for s in sources:
        for r in HUB_BIOMNI_SOURCES:
            if r.lower() in s.lower():
                hits.append(s)
                break
    return hits


def _infer_answer_type(ideal: str, answer_regex: str) -> str:
    """Coarse answer-type tag used to route deterministic scoring."""
    ideal = (ideal or "").strip()
    try:
        parsed = json.loads(ideal)
    except (json.JSONDecodeError, TypeError):
        return "text"
    if isinstance(parsed, dict):
        if len(parsed) == 1:
            (val,) = parsed.values()
            if isinstance(val, (int, float)):
                return "exact_number"
            if isinstance(val, list):
                return "entity_list"
            if isinstance(val, str) and val.replace(".", "", 1).isdigit():
                return "exact_number"
        return "structured"
    if isinstance(parsed, list):
        return "entity_list"
    if isinstance(parsed, (int, float)):
        return "exact_number"
    return "text"


def format_item(row: dict) -> dict:
    """Map a DbQA2 row to the AgentCore-compatible golden schema."""
    ideal = row.get("ideal", "") or ""
    answer_regex = row.get("answer_regex", "") or ""
    answer_type = _infer_answer_type(ideal, answer_regex)
    sources = row.get("sources", []) or []

    return {
        "id": f"dbqa2_{row['id'][:8]}",
        "input": row["question"],
        "evaluationReferenceInputs": {
            "expectedResponse": ideal,
            # Tool trajectory is unknown until Biomni tools are mapped to sources.
            "expectedTrajectory": [],
            "assertions": [],
        },
        "metadata": {
            "category": "tier1_public_db",
            "answer_type": answer_type,
            "sources": sources,
            "verification_method": "expert_verified_labbench2",
            "is_opensource": bool(row.get("is_opensource", False)),
            "canary": row.get("canary", ""),
            "answer_regex": answer_regex,
            "validator_params": row.get("validator_params", ""),
            "labbench2_id": row["id"],
            "labbench2_tag": row.get("tag", "dbqa2"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="keep all 86 (skip source filter)")
    args = ap.parse_args()

    ds = load_dataset("EdisonScientific/labbench2", "dbqa2")["train"]

    kept, skipped_sources = [], Counter()
    for row in ds:
        rel = _source_is_relevant(row.get("sources", []) or [])
        if args.all or rel:
            kept.append(format_item(row))
        else:
            for s in row.get("sources", []) or []:
                skipped_sources[s] += 1

    by_type = Counter(item["metadata"]["answer_type"] for item in kept)
    by_source = Counter(s for item in kept for s in item["metadata"]["sources"])

    with open(config.GOLDEN_DATASET_TIER1, "w") as f:
        json.dump(kept, f, indent=2)

    print(f"DbQA2 total: {len(ds)}  |  kept: {len(kept)}  ->  {config.GOLDEN_DATASET_TIER1}")
    print("answer_type:", dict(by_type))
    print("kept sources:", dict(by_source.most_common()))
    if not args.all:
        print("skipped sources (not hub/Biomni-relevant):", dict(skipped_sources.most_common()))
    print("\n⚠️ Source-name heuristic. Re-filter against the real Biomni tool inventory before reporting.")


if __name__ == "__main__":
    main()
