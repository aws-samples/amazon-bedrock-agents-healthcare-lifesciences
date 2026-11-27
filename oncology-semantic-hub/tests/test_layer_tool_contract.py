"""Contract test: the L0-L3 layer -> tool mapping must stay consistent across its definitions.

The layer ladder (the accelerator's core mechanism) is described in two places that can silently
drift apart:
  1. agentcore/semantic_hub_agent.py  — the DEPLOYED agent's env-gated tool list per SEMHUB_LAYER.
  2. evaluation/provenance_faithfulness.py `VALID` — the provenance-tag inventory each layer may emit.

If a layer gains/loses a tool in (1) but (2) isn't updated, the provenance scorer will either flag
honest tags as fabricated or miss real fabrication — quietly corrupting the benchmark's headline
grounding/faithfulness numbers. This test pins the mapping so that drift fails CI.

Pure logic + env-gated import only; makes no AWS calls.
"""
import importlib
import os
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "agentcore"))

from evaluation.provenance_faithfulness import VALID  # noqa: E402

# The capability each logical tool grounds — i.e. the provenance tag it lets the agent legitimately emit.
TOOL_TO_TAG = {
    "query_knowledge_graph": "graph",
    "query_patient_data": "lake",
    "query_variant_annotation": "roda",
    "query_primekg": "primekg-flat",
    "knowledge_search": "kb",
    "ontology_lookup": "ols",
    "get_hub_schema": None,   # structural, not a fact source — grounds no tag
    "web_search": "web",
}

# Expected deployed tool set per layer (mirrors semantic_hub_agent.py's env-gating).
EXPECTED_TOOLS = {
    "L0": set(),
    "L0-web": {"web_search"},
    "L1": {"query_patient_data"},
    "L2": {"knowledge_search", "query_patient_data", "query_variant_annotation", "query_primekg"},
    "L3": {"knowledge_search", "get_hub_schema", "query_knowledge_graph",
           "query_patient_data", "query_variant_annotation", "ontology_lookup"},
    "L3a": {"knowledge_search", "get_hub_schema", "query_knowledge_graph",
            "query_patient_data", "query_variant_annotation"},  # graph, -OLS
    "L3_no_graph": {"knowledge_search", "get_hub_schema", "query_patient_data",
                    "query_variant_annotation", "ontology_lookup"},
    "L3_no_ols": {"knowledge_search", "get_hub_schema", "query_knowledge_graph",
                  "query_patient_data", "query_variant_annotation"},
    "L3_no_kb": {"get_hub_schema", "query_knowledge_graph", "query_patient_data",
                 "query_variant_annotation", "ontology_lookup"},
}


def _agent_import_available():
    """True only if the deployed agent's deps are importable (the repo .venv, not a bare interpreter)."""
    try:
        import strands  # noqa: F401
        import bedrock_agentcore  # noqa: F401
        return True
    except Exception:
        return False


def _load_agent_tools(layer):
    """Import semantic_hub_agent under SEMHUB_LAYER=<layer> and return its tool-name set.
    Only call when _agent_import_available() is True."""
    os.environ["SEMHUB_LAYER"] = layer
    sys.modules.pop("semantic_hub_agent", None)
    mod = importlib.import_module("semantic_hub_agent")
    names = set()
    for t in mod._TOOLS:
        names.add(getattr(t, "tool_name", getattr(t, "__name__", None)))
    return names, mod


class TestLayerToolContract(unittest.TestCase):

    def test_tools_consistent_with_provenance_inventory(self):
        """Every tag a layer's tools can ground must be allowed in VALID, and every tool-grounded
        tag in VALID must correspond to a tool the layer actually has — no silent drift.

        This is pure data-vs-data (EXPECTED_TOOLS vs VALID), so it runs in any interpreter with no
        heavy deps and no AWS — the cheapest guard against the benchmark-corrupting drift."""
        for layer, tools in EXPECTED_TOOLS.items():
            if layer not in VALID:
                continue  # layers not scored (e.g. L0-web) need no inventory
            with self.subTest(layer=layer):
                tool_tags = {TOOL_TO_TAG[t] for t in tools if TOOL_TO_TAG.get(t)}
                allowed = VALID[layer]
                missing = tool_tags - allowed
                self.assertFalse(
                    missing,
                    f"{layer}: tools can emit {sorted(missing)} but VALID forbids them "
                    f"-> scorer would flag honest tags as fabricated.")
                # Non-tool tags are always allowed: model, recalled, web, compute.
                tool_grounded = {v for v in allowed if v not in {"model", "recalled", "web", "compute"}}
                orphan = tool_grounded - tool_tags
                self.assertFalse(
                    orphan,
                    f"{layer}: VALID allows tool-tags {sorted(orphan)} with no backing tool "
                    f"-> scorer would miss real fabrication.")

    @unittest.skipUnless(_agent_import_available(),
                         "deployed-agent deps (strands/bedrock_agentcore) not installed — "
                         "run in the repo .venv to exercise the live env-gating check")
    def test_deployed_tools_match_expected(self):
        """The agent's env-gated tool list equals the documented set for each layer (live import)."""
        for layer, expected in EXPECTED_TOOLS.items():
            with self.subTest(layer=layer):
                got, _ = _load_agent_tools(layer)
                self.assertEqual(
                    got, expected,
                    f"{layer}: deployed tools {sorted(got)} != expected {sorted(expected)} "
                    f"— update EXPECTED_TOOLS or semantic_hub_agent.py (they drifted).")

    @unittest.skipUnless(_agent_import_available(),
                         "deployed-agent deps not installed — run in the repo .venv")
    def test_env_gating_isolates_layers(self):
        """L0 has no tools; L3 has the full set — a sanity check that gating actually switches."""
        l0, _ = _load_agent_tools("L0")
        l3, _ = _load_agent_tools("L3")
        self.assertEqual(l0, set())
        self.assertIn("query_knowledge_graph", l3)
        self.assertGreater(len(l3), len(l0))

    def tearDown(self):
        os.environ.pop("SEMHUB_LAYER", None)
        sys.modules.pop("semantic_hub_agent", None)


if __name__ == "__main__":
    unittest.main()
