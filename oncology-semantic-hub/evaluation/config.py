"""Central configuration for the Semantic Hub Validation Framework.

Everything the harness needs is defined here so the rest of the framework does
NOT import from agent/main.py (v1 coupled the benchmark to the app, which mixed
production and evaluation concerns and pinned a malformed model id).

⚠️ Model IDs: use VALID, versioned Bedrock inference-profile IDs only.
   v1 used "us.anthropic.claude-opus-4-7" which has no version suffix and does
   not resolve. Verify any ID with:
       aws bedrock list-inference-profiles --region us-west-2
   before trusting a run.

⚠️ RESPONSIBLE AI / RESEARCH USE ONLY: this framework benchmarks an oncology research
   assistant over public, de-identified TCGA data. It is NOT a clinical decision-support
   system. AI-generated outputs scored here (drug names, evidence levels, treatment-
   implication language) must not be used as the sole basis for a clinical or treatment
   decision — qualified clinical/oncologist review is required before any such output
   informs patient care. This file configures the MODEL and METHODOLOGY only; it is the
   deploying organization's responsibility to enable Amazon Bedrock Guardrails and any
   additional content controls appropriate to their deployment, and to keep a human in
   the loop wherever this framework's outputs could influence a real clinical decision.
   See the top-level README's Known Limitations section and docs/bring-your-own-data.md's
   PHI/HIPAA guidance before using this framework on anything beyond the public TCGA
   reference data.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# ── AWS / resource configuration ────────────────────────────────────────────
REGION = os.environ.get("SEMHUB_REGION", "us-west-2")

# Neptune Analytics graph that ground truth is pinned to.
GRAPH_ID = os.environ.get("SEMHUB_GRAPH_ID", "")  # set to your Neptune Analytics graph id

# Athena / data lake
ATHENA_DATABASE = os.environ.get("SEMHUB_ATHENA_DB", "oncology_semantic_hub")
ATHENA_WORKGROUP = os.environ.get("SEMHUB_ATHENA_WG", "primary")
ATHENA_OUTPUT = os.environ.get("SEMHUB_ATHENA_OUTPUT", "")  # set to s3://<your-bucket>/athena-results/

# Ground-truth snapshot identifier — stamped onto every generated question so a
# later graph mutation invalidates stale answers explicitly.
DATA_SNAPSHOT = os.environ.get("SEMHUB_SNAPSHOT", "hub_snapshot")


# ── Model configuration ──────────────────────────────────────────────────────
# Subject model = the model under test on every layer (held constant so the ONLY
# variable is the semantic hub). Judge model must differ from subjects to avoid
# self-evaluation bias.
#
# The known-good id below is the one the deployed agent already runs on. Model
# independence (Objective 3) adds more ids in MODEL_INDEPENDENCE_CANDIDATES after
# they are verified against `aws bedrock list-inference-profiles`.
SUBJECT_MODEL_ID = os.environ.get(
    "SEMHUB_SUBJECT_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
JUDGE_MODEL_ID = os.environ.get(
    "SEMHUB_JUDGE_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)
GROUND_TRUTH_MODEL_ID = os.environ.get(
    "SEMHUB_GT_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)

# TODO(model-independence): verify these before use.
#   e.g. "us.amazon.nova-pro-v1:0", "us.anthropic.claude-3-5-haiku-20241022-v1:0"
MODEL_INDEPENDENCE_CANDIDATES: list[str] = []


# ── Run / methodology defaults ───────────────────────────────────────────────
# Correctness runs are deterministic; reproducibility runs use a non-zero temp so
# run-to-run variance is actually observable (the hub's job is to suppress it).
CORRECTNESS_TEMPERATURE = 0.0
REPRODUCIBILITY_TEMPERATURE = 0.7
N_RUNS = 3
MAX_TOKENS = 1500

# A question counts as "correct" when its score meets this threshold.
CORRECTNESS_THRESHOLD = 0.8


# ── Paths ────────────────────────────────────────────────────────────────────
EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
GOLDEN_DATASET = ROOT / "ground_truth" / "golden_v2.json"
GOLDEN_DATASET_TIER1 = ROOT / "ground_truth" / "golden_dataset_v1.json"
RESULTS_DIR = ROOT / "output"
REPORTS_DIR = ROOT / "output"
SYSTEM_PROMPTS_DIR = EVAL_DIR / "system_prompts"

for _d in (RESULTS_DIR, REPORTS_DIR, SYSTEM_PROMPTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ── Layer definitions ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class LayerConfig:
    """One agent configuration under test. `tools` are logical tool names resolved
    by the runner; `graph_mask` selects tool-level ablation (never mutates the graph)."""

    name: str
    description: str
    tools: tuple[str, ...] = ()
    system_prompt_file: str = "base_researcher.txt"
    graph_mask: str | None = None  # None | "no_clinvar" | "no_ontology" | "no_patients"


# Pilot headline comparison: L1 (raw data lake, NO semantic map) vs L3 (hub WITH map).
LAYERS: dict[str, LayerConfig] = {
    "L1": LayerConfig(
        name="L1",
        description="Raw data lake, no semantic map (Athena SQL only)",
        tools=("query_patient_data",),
        system_prompt_file="with_athena.txt",
    ),
    "L3": LayerConfig(
        name="L3",
        description="Semantic hub with retrieval map (Neptune + Athena + OLS ontology)",
        tools=("query_knowledge_graph", "query_patient_data", "get_hub_schema", "ontology_lookup"),
        system_prompt_file="full_hub.txt",
    ),
}

# Reference / ablation layers, wired in later iterations.
LAYERS_FUTURE: dict[str, LayerConfig] = {
    "L0": LayerConfig("L0", "Bare LLM (no tools, parametric knowledge only)",
                      (), "base_researcher.txt"),
    "L2": LayerConfig("L2", "LLM + knowledge graph only (Neptune)",
                      ("query_knowledge_graph", "get_hub_schema"), "with_neptune.txt"),
    "L3_no_clinvar": LayerConfig("L3_no_clinvar", "Full hub minus ClinVar enrichment",
                                 ("query_knowledge_graph", "query_patient_data", "get_hub_schema"),
                                 "full_hub.txt", graph_mask="no_clinvar"),
    "L3_no_ontology": LayerConfig("L3_no_ontology", "Full hub minus MONDO/ICD ontology",
                                  ("query_knowledge_graph", "query_patient_data", "get_hub_schema"),
                                  "full_hub.txt", graph_mask="no_ontology"),
    "L3_no_patients": LayerConfig("L3_no_patients", "Full hub minus TCGA patient nodes",
                                  ("query_knowledge_graph", "query_patient_data", "get_hub_schema"),
                                  "full_hub.txt", graph_mask="no_patients"),
}
