# Oncology Semantic Hub — Sales Enablement Brief

> **For:** AWS field teams, HCLS account teams, partner SAs
> **Date:** August 2026

---

## Two accelerators (independently valuable, composable)

### Accelerator 1: Oncology Semantic Hub (starter hub + BYOD)
A **working, deployable oncology research hub** that customers extend with their own data — not
just a demo to look at. **The accelerator is the *method*, not the sample data:** the KG + L3 semantic-layer
constructs (knowledge-graph traversal + ontology harmonization) + a repeatable **bring-your-own-data** pipeline
to onboard RODA open datasets *and* a customer's own cohorts. Oncology (TCGA/PrimeKG/CIViC/ClinVar) is the
**reference implementation** that proves the pattern — TCGA alone is table stakes; the value is the constructs + BYOD.

**AWS services:** Amazon Neptune Analytics, Amazon Athena, Amazon S3, Amazon Bedrock (AgentCore Runtime + Knowledge Bases), AWS SSM (OLS config).

**What's included:**
- Neptune knowledge graph (PrimeKG backbone — 174K nodes: genes, diseases, drugs, pathways)
- TCGA patient data lake (1.8M somatic mutations, expression, CNA — Athena/Parquet)
- RODA expansion pipeline (28 curated open datasets, repeatable onboarding at scale)
- OLS MCP server (200+ ontologies, live canonical resolution)
- Agent code (single-file, env-gated L0–L3, deploys to AgentCore)
- Bring-your-own-data guide (swap/augment your cohort, add RODA datasets)
- Numbered data pipeline scripts (fully reproducible)

**Customer value:** *"Start with a validated oncology foundation, add your cohort + your datasets
(via RODA pipeline), and have a working research agent on day 1."*

### Accelerator 2: Semantic Hub Benchmark Framework
A **measurement tool** for any semantic hub (oncology or other domain) — prove whether your
semantic layer is worth the investment. **Domain-agnostic:** swap the questions and tag vocabulary
to benchmark any KG + lake + ontology combination.

**What's included:**
- Tier-controlled ladder design (L0 bare LLM → L1 lake → L2 flat data → L3 semantic hub)
- 3-dimension scoring (correctness, faithfulness, reproducibility)
- Novel provenance-faithfulness scorer (layer-aware fabrication detection)
- 5× reproducibility framework (solve-count + self-agreement)
- 2×2 ablation design (graph × ontology isolation)
- Golden dataset template + authoring guidance (schema for any domain)
- Benchmark report template (exec summary → methodology → results → root-cause → roadmap)

**Customer value:** *"Prove whether YOUR semantic layer is worth it — measure correctness,
reproducibility, and grounding with the same rigor we validated ours."*

### How they compose
Use Accelerator 1 to **BUILD** your hub → use Accelerator 2 to **MEASURE** it. But each is
independently valuable — a customer can benchmark a hub they built without our code, or deploy
our oncology hub without running the full benchmark.

---

## What we can demo today

A **live, 4-question EGFR-GBM comparison** (~10 min):
- Q1–Q2 (L2 vs L3): correctness + reproducibility — same data, different organization
- Q3–Q4 (L0 vs L3): groundedness + multi-hop — memory vs real cohort data

**Validated results (84-question benchmark, Claude Sonnet 4.5):**
- Correctness: flat data 0.67 → semantic hub **0.80** (+13%)
- Reproducibility: flat data 0.63 → semantic hub **0.73** (+10%)
- Grounding rate: bare LLM 0.26 → semantic hub **1.0** (fully tool-backed)

**Key message:** *"Same data, same model — organizing it as a semantic hub makes the agent 13% more
correct and 10% more reproducible on hard multi-hop oncology questions."*

---

## How customers get started

### Path 1: "Show me the value on MY data" (2–4 week engagement)
1. Customer provides their patient cohort (VCF/MAF, clinical tables) + their KG (or we use PrimeKG)
2. We adapt the data pipeline (swap TCGA → their data, add RODA datasets) and deploy the hub
3. Run the benchmark framework on their domain questions → quantified value
4. Deliver: working agent + benchmark results + architecture diagram

### Path 2: "I want this pattern for a different domain" (4–8 week engagement)
1. Identify the customer's data sources (warehouse, KG, ontologies)
2. Apply the Neptune + Athena + OLS pattern to their domain
3. Build domain-specific benchmark questions (adapt the 12-category framework)
4. Deploy + validate + hand off

### Path 3: "I just want the tools" (self-service, days)
1. Connect to the HCLS MCP servers (Neptune, OLS, Athena) from their existing agent
2. Install the oncology-semantic-hub-analysis skill in their IDE (Claude Code, Kiro, Amazon Quick)
3. Query the public hub directly — no deployment needed

---

## Qualifying questions for customers

- "Do your researchers ask questions that cross multiple data systems?" → multi-hop value
- "Do you get different answers from the same query depending on who runs it?" → reproducibility value
- "Are your data lake queries limited to what's in the warehouse?" → graph/ontology value
- "Do you have a knowledge graph but no way for researchers to query it naturally?" → agent value
- "How do you know if adding a KG actually improved your agent's answers?" → benchmark value

---

## Supporting materials

| Material | Location |
|---|---|
| Technical report (methodology + results) | `docs/benchmark-report.md` |
| Demo recording script | `docs/demo-golden-thread-v4.md` |
| RODA data catalog (28 datasets) | `docs/roda_oncology_hub_complete_reference.md` |
| Whitepaper section 4.1 (detailed) | `docs/whitepaper-section-4.1-draft.md` |
| Live app | http://localhost:8501 (Streamlit, run locally) |
| Agent code | `agentcore/semantic_hub_agent.py` |
| Benchmark dataset | `evaluation/golden_v2.json` (84 Q) |
