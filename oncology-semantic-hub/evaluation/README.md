# Semantic Hub Benchmark Framework (Accelerator 2)

Measure whether your semantic layer (knowledge graph + ontology) is worth the investment —
with the same rigor used to validate the oncology hub.

## What you get

- **Tier-controlled comparison:** L0 (bare LLM) → L1 (lake) → L2 (flat data) → L3 (semantic hub)
- **3-dimension scoring:** correctness, faithfulness, reproducibility
- **Novel metrics:** provenance-faithfulness (layer-aware), grounding_rate (tier-discriminating)
- **5× reproducibility:** solve-count + self-agreement (Jaccard)
- **Methodology:** attempt-and-attribute (no forced abstention, no combined scores)

## Quick start (using the oncology reference)

```bash
# 1. Deploy L3 and L2 agents (requires running data pipeline first)
python agentcore/deploy.py --layer L3
python agentcore/deploy.py --layer L2

# 2. Run native AgentCore evaluation (Builtin.Correctness + Faithfulness)
python agentcore/run_agentcore_eval.py

# 3. Run custom benchmark (F1 scoring + 5× reproducibility)
python agentcore/run_v2_benchmark.py

# Results written to output/
```

## Adapting for your own domain

### Step 1: Write your golden dataset
Create a JSON file following the `ground_truth/golden_v2.json` schema:

```json
[
  {
    "id": "my_q_001",
    "question": "How many patients have mutations in BRCA1?",
    "category": "lake",
    "ideal": {"n_patients": 142},
    "verify": "SELECT COUNT(DISTINCT patient_id) FROM mutations WHERE gene='BRCA1'"
  }
]
```

**Categories** (the reference `golden_v2.json` uses 12; adapt to your domain):
- `lake` — answerable from your data warehouse alone
- `graph_1hop` — single relationship traversal
- `graph_multihop` — multi-hop graph reasoning
- `reconciliation` / `cross_system` — cross-system entity resolution
- `ontology` — identifier/terminology resolution
- `multi_source` — requires joining multiple systems
- `quantitative_precision` — exact numeric answers (within tolerance)
- `drug_gene_relationships` — drug ↔ target traversal
- `evidence` / `actionability` — clinical evidence + actionability (CIViC)
- `negative` — questions about absent data (should say "can't determine")

### Step 2: Configure provenance tags
Edit `provenance_faithfulness.py` → `VALID` (the per-layer valid-tag inventory) to match your tools:

```python
VALID = {
    "L0": {"model", "recalled"},
    "L1": {"snowflake", "model", "recalled"},          # your lake
    "L2": {"snowflake", "neo4j-flat", "kb", "model", "recalled"},  # your flat KG
    "L3": {"snowflake", "neo4j", "umls", "kb", "model", "recalled"},  # your hub
}
```

### Step 3: Run and report
Same scripts, same methodology — just point at your agent configs and golden dataset.

## File reference

| File | Purpose |
|---|---|
| `../ground_truth/golden_v2.json` | The 84-question oncology benchmark (reference instance) |
| `../ground_truth/golden_v2_FROZEN_phaseA.json` | Frozen snapshot for traceability |
| `../ground_truth/golden_v2_agentcore.json` | AgentCore ReferenceInputs format |
| `provenance_faithfulness.py` | Layer-aware provenance scorer |
| `scoring.py` | Deterministic scorers (numeric, gene-list F1, CURIE match) |
| `test_scoring.py` | Scorer unit tests — run with `python -m evaluation.test_scoring` |
| `judge.py` | LLM-as-judge for open-ended/negative questions |
| `generate_questions.py` | Template-driven question generation from live data |
| `config.py` | Evaluation configuration |

> The golden datasets live under `ground_truth/`, not `evaluation/`. `config.py` resolves them via
> `GOLDEN_DATASET = ROOT/"ground_truth"/"golden_v2.json"`.

## Running the tests

This repo uses the Python standard-library **`unittest`** (no `pytest`). Run:

```bash
python -m unittest discover -s tests        # benchmark-framework + provenance tests
python -m unittest discover -s hub_core      # read-only query guards + schema
python -m evaluation.test_scoring            # deterministic scorer assertions
```

## Metrics glossary

| Metric | What it measures | Novel? |
|---|---|---|
| Correctness (Builtin) | Answer vs verified GT (LLM-judge, pass/fail) | Borrowed (AgentCore) |
| Correctness (custom F1) | Partial credit for gene-list/set-valued answers | Ours |
| Builtin.Faithfulness | Non-contradiction with tool outputs | Borrowed (AgentCore) |
| Provenance-faithfulness | Layer-aware attribution honesty (fabricated grounding detection) | **Novel** |
| grounding_rate | Fraction of answer backed by tool retrievals | **Novel** |
| Reproducibly-correct | Fraction of 5 runs correct (≥0.8 vs GT) | Borrowed concept (BioMysteryBench) |
| Self-agreement | Mean pairwise Jaccard across 5 runs | Ours (Jaccard operationalization) |

Full methodology: `docs/benchmark-report.md`
