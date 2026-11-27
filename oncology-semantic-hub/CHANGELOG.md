# Changelog

All notable changes to the Oncology Semantic Hub accelerators. Versions follow [SemVer](https://semver.org/).

## [Unreleased] — Phase 3 (planned)
See `docs/phase3-plan.md` for design tracks.
- **[1.1.0]** Feature 1 — radar chart metrics visualization (Accelerator 2)
- **[1.2.0]** Feature 2 — HealthOmics workflow execution on discovered VCFs (1000 Genomes VEP; Accelerator 1)
             + Accelerator 2 external-dataset validation (LAB-Bench DbQA2)
- **[1.3.0]** Feature 3 — human-in-the-loop context graph / self-improving hub (Accelerator 1)

## [1.0.0] — 2026-08-11 — Check-in baseline
First clean, check-in-ready release of the two accelerators.

### Accelerator 1 — Oncology Starter Hub + BYOD
- Env-gated agent (L0/L1/L2/L3 + ablations) deployable to AgentCore Runtime.
- Numbered data pipeline (`scripts/01–16`) + RODA expansion (`scripts/roda/`).
- Neptune knowledge graph (PrimeKG) + TCGA lake (Athena) + OLS ontology + CIViC/ClinVar (RODA).
- Bring-your-own-data pathway documented.

### Accelerator 2 — Semantic Hub Benchmark Framework
- 84-question golden dataset (12 categories) + scorers (correctness F1, provenance-faithfulness, reproducibility).
- Tier-controlled ladder (L0→L3) + 2×2 ablation (graph × ontology).
- Native AgentCore eval + custom 5× reproducibility runner.
- Headline results: L2→L3 +0.13 correctness, +0.10 reproducibility, near-full grounding.

### Repository hygiene
- **De-accounted:** zero hardcoded AWS account IDs / graph IDs across all committable files;
  all config env-driven via `scripts/_config.py` + `.env.example`, fails loudly if unset.
- `deploy.py` injects runtime config (`SEMHUB_GRAPH_ID` / `SEMHUB_ATHENA_OUTPUT`).
- Clean separation: `agentcore/` (agent) · `evaluation/` (framework) · `ground_truth/` (datasets) ·
  `scripts/` (pipeline) · `tests/` (23 unit tests) · `docs/` (+ `archive/`) · `output/` (gitignored).
- Secrets/outputs gitignored (`agent_config*.json`, `.env`, `output/`, `data/`).
- 23 unit tests passing; live L3 deploy + smoke test validated post-refactor.
