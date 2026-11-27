# /// script
# requires-python = ">=3.9"
# ///
"""Score an agent answer's grounding + provenance-faithfulness from its inline [tags].

Stdlib-only (no dependencies) — runs with `python3` or `uv run`. Two deterministic, single-response
metrics, no ground truth, no extra model call:

  grounding_rate           fraction of tags that are TOOL-retrieved ([Graph]/[Lake]/[OLS]/[KB]/[RODA]/
                           [Web]) vs [Model knowledge]/[Recalled]. Low is not "bad".
  provenance_faithfulness  1 - fabricated/total, where fabricated = a tag the connected-tool INVENTORY
                           cannot produce (e.g. claiming [Graph] with no graph tool). 1.0 = honest.

PORTABLE COPY of oncology_semantic_hub/evaluation/provenance_faithfulness.py — kept identical
(drift-guarded by skills/grounding-faithfulness-eval/tests/test_parity.py). Definitions match the
Oncology Semantic Hub benchmark report §12/§12b.
"""
import argparse
import json
import re
import sys

# Provenance-tag types each tool INVENTORY (layer) can legitimately produce.
VALID = {
    "L0": {"model", "recalled"},
    "L0-web": {"web", "model", "recalled"},
    "L1": {"lake", "model", "recalled"},
    "L2": {"lake", "roda", "primekg-flat", "kb", "model", "recalled"},
    "L3": {"kb", "graph", "lake", "ols", "model", "recalled"},
    # Quick (or any harness) on the Neptune+Athena data MCP server + OLS MCP.
    "quick": {"kb", "graph", "lake", "roda", "ols", "compute", "model", "recalled"},
}


def _tagtype(t):
    t = t.lower()
    if "model knowledge" in t:
        return "model"
    if t.startswith("recalled"):
        return "recalled"
    if t.startswith("lake"):
        return "lake"
    if t.startswith("graph"):
        return "graph"
    if t.startswith("ols"):
        return "ols"
    if t.startswith("kb"):
        return "kb"
    if t.startswith("roda"):
        return "roda"
    if t.startswith("web"):
        return "web"
    if t.startswith("compute") or t.startswith("code"):
        return "compute"
    if "primekg" in t:
        return "primekg-flat"
    return "other"


def score_provenance(answer, layer):
    tags = re.findall(r"\[([^\]]+)\]", answer or "")
    types = [_tagtype(t) for t in tags if _tagtype(t) != "other" or "model" in t.lower()]
    types = [t for t in types if t in {"model", "recalled", "lake", "graph", "ols", "kb", "roda", "primekg-flat", "web", "compute"}]
    valid = VALID.get(layer, {"model"})
    if not types:
        return {"provenance_faithfulness": None, "grounding_rate": None, "n_tags": 0,
                "fabricated": [], "note": "no provenance tags (unauditable)"}
    fabricated = [t for t in types if t not in valid]
    tool_tags = [t for t in types if t not in ("model", "recalled")]
    return {"provenance_faithfulness": round(1 - len(fabricated) / len(types), 3),
            "grounding_rate": round(len(tool_tags) / len(types), 3),
            "n_tags": len(types), "fabricated": sorted(set(fabricated))}


def main():
    ap = argparse.ArgumentParser(
        description="Score grounding_rate + provenance-faithfulness from an answer's inline [tags].",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  printf '%s' \"144 genes [Graph]; ~500 [Model knowledge]\" | python3 scripts/score_provenance.py --inventory quick\n"
               "  python3 scripts/score_provenance.py --inventory L3 --answer-file answer.txt\n"
               "Exit codes: 0 ok · 2 no input.")
    ap.add_argument("--inventory", default="quick",
                    help="connected-tool inventory: quick (default), L3, L2, L1, L0, L0-web")
    ap.add_argument("--answer-file", help="path to the answer text (default: read from stdin)")
    a = ap.parse_args()
    text = open(a.answer_file).read() if a.answer_file else sys.stdin.read()
    if not text.strip():
        print("Error: no answer text provided (pass --answer-file or pipe via stdin).", file=sys.stderr)
        sys.exit(2)
    if a.inventory not in VALID:
        print(f"Warning: unknown inventory '{a.inventory}'; tool tags will count as fabricated. "
              f"Known: {', '.join(VALID)}", file=sys.stderr)
    print(json.dumps(score_provenance(text, a.inventory), indent=2))


if __name__ == "__main__":
    main()
