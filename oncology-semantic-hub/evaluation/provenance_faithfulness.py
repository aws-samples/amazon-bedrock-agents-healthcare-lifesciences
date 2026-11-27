"""Provenance Faithfulness — the ONE new faithfulness metric (+ descriptors).

METRIC (faithfulness):
  provenance_faithfulness [0,1] = 1 - (fabricated_grounding_tags / all_tags).
  "Fabricated grounding" = claiming a tool/source the layer did not actually use
  (e.g. L0 emitting [Lake], L2 emitting [Graph]). Higher = more honest attribution.
DESCRIPTORS (NOT faithfulness metrics — tier characterization only):
  grounding_rate = tool-tags / all-tags (how tool-backed vs [Model knowledge]).
  A low grounding_rate is NOT unfaithful (honest use of model memory is faithful).
Layer-aware provenance-attribution.
Complements Builtin.Faithfulness (which is vacuous when there is no retrieved context).
Scores whether an answer's provenance tags are HONEST: no claim of a tool source the layer
cannot have (fabricated grounding), and own-knowledge tagged [Model knowledge].
"""
import re
# provenance tag types a layer can legitimately produce (its actual tools)
VALID = {
 "L0": {"model", "recalled"},
 "L0-web": {"web", "model", "recalled"},
 "L1": {"lake", "model", "recalled"},
 "L2": {"lake", "roda", "primekg-flat", "kb", "model", "recalled"},
 "L3": {"kb", "graph", "lake", "roda", "ols", "model", "recalled"},
 # Quick (or any harness) connected to the deployed data MCP server (Neptune+Athena) + OLS MCP.
 # Same attributable sources as L3; used to score Quick answers (see remote-mcp-server-design.md §15).
 "quick": {"kb", "graph", "lake", "roda", "ols", "compute", "model", "recalled"},
 # 2x2 / component ablations: same inventory as L3 minus the ablated tool.
 # (query_variant_annotation -> "roda" is present in every L3-family layer, matching the deployed agent.)
 "L3a": {"kb", "graph", "lake", "roda", "model", "recalled"},              # graph, -OLS
 "L3b": {"kb", "lake", "roda", "primekg-flat", "ols", "model", "recalled"},  # flat, +OLS
 "L3_no_graph": {"kb", "lake", "roda", "ols", "model", "recalled"},
 "L3_no_ols": {"kb", "graph", "lake", "roda", "model", "recalled"},
 "L3_no_kb": {"graph", "lake", "roda", "ols", "model", "recalled"},
}
def _tagtype(t):
    t = t.lower()
    if "model knowledge" in t: return "model"
    if t.startswith("recalled"): return "recalled"
    if t.startswith("lake"): return "lake"
    if t.startswith("graph"): return "graph"
    if t.startswith("ols"): return "ols"
    if t.startswith("kb"): return "kb"
    if t.startswith("roda"): return "roda"
    if t.startswith("web"): return "web"
    if t.startswith("compute") or t.startswith("code"): return "compute"
    if "primekg" in t: return "primekg-flat"
    return "other"
def score_provenance(answer: str, layer: str):
    tags = re.findall(r"\[([^\]]+)\]", answer or "")
    types = [_tagtype(t) for t in tags if _tagtype(t) != "other" or "model" in t.lower()]
    types = [t for t in types if t in {"model","recalled","lake","graph","ols","kb","roda","primekg-flat","web","compute"}]
    valid = VALID.get(layer, {"model"})
    if not types:
        return {"provenance_faithfulness": None, "grounding_rate": None, "n_tags": 0,
                "fabricated": [], "note": "no provenance tags (unauditable)"}
    fabricated = [t for t in types if t not in valid]
    tool_tags = [t for t in types if t not in ("model", "recalled")]  # recalled = ungrounded, like model knowledge
    return {"provenance_faithfulness": round(1 - len(fabricated)/len(types), 3),
            "grounding_rate": round(len(tool_tags)/len(types), 3),
            "n_tags": len(types), "fabricated": sorted(set(fabricated))}
if __name__ == "__main__":
    tests = [
     ("L0","EGFR drives GBM [Model knowledge]; therapy is erlotinib [Model knowledge]."),
     ("L0","148 TCGA-GBM patients carry EGFR [Lake:tcga_mutations]."),  # FABRICATED: L0 has no lake
     ("L3","148 patients [Lake:tcga_mutations]; EGFR is druggable [Graph]; melanoma [OLS:MONDO:0005105]."),
     ("L2","EGFR-drug link [Graph]; 79 patients [Lake:tcga_mutations]."),  # FABRICATED: L2 has no graph
     ("L2","evidence [KB PMID:21639808]; 79 patients [Lake:tcga_mutations]; drug via [PrimeKG-flat:drug_protein]."),
     ("L3","BRAF V600E confers resistance."),  # untagged -> unauditable
    ]
    for lyr,a in tests:
        print(f"  {lyr}: {score_provenance(a,lyr)}  <- {a[:55]}")
