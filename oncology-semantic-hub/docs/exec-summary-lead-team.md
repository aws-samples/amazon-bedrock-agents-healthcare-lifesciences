# Exec Summary — Oncology Semantic Hub Accelerators: Positioning & Collaboration Plan

**For:** Lisa McFerrin, Indradeep Dasgupta · **From:** Hasan Poonawala · **Date:** 2026-08-12

## TL;DR
The oncology work yields **two accelerators that are modules of the emerging enterprise semantic-layer
framework — not standalone products.** Addressing the "beyond TCGA" concern: **the accelerator is the
*method*, not the sample data.** Next step is a **7-working-day alignment sprint** with the parallel streams
(Stan, Chaitanya, Ariella/Michael, Nadeem) to converge on one cohesive framework before further build.

## The two accelerators (what they are + what to work toward)

**Accelerator 1 — Semantic Hub Starter + BYOD.** A1 is the reusable *method* for building a governed semantic
layer over life-sciences data — knowledge-graph traversal plus ontology harmonization (the "L3" constructs) —
with a repeatable bring-your-own-data pipeline that onboards RODA open datasets *and* a customer's own cohort
(two modes: extend the core graph or add to the lake; a documented 5–6 step discover→process→wire→validate flow).
Oncology (TCGA/PrimeKG/CIViC) is the reference implementation, not the value — TCGA alone is table stakes. It also
supports governed, auditable per-user DB access by design (assume-role per identity → CloudTrail/Neptune audit),
which the drop-in Neptune MCP servers can't. *To work toward:* one substantial RODA-BYOD research persona demo
(to prove "beyond TCGA"), alignment to the enterprise semantic-layer patterns (federated/governance/CI-CD), and a
resolved per-user/multi-tenant access architecture.

**Accelerator 2 — Semantic Hub Benchmark Framework.** A2 objectively measures whether the semantic layer is worth
the investment — scoring correctness, reproducibility, and grounding/faithfulness across a bare-LLM → flat-data →
semantic-hub ladder — and can flag when an addition *poisons* context rather than helps. Its grounding is a
superset of Bedrock Contextual Grounding: tool-provenance across lake/graph/OLS/KB/RODA, tier-aware (works even
with no tools), with no KB or AgentCore-Gateway dependency, plus provenance-faithfulness (fabricated-grounding
detection). Today it operates in "attempt-and-attribute" mode (agents attempt every question and tag provenance;
no gating). *To work toward:* adding governance/gating on top — evolving it toward a CI-gate for the semantic
layer — plus context-poisoning detection, expert-validated ground truth, and statistical rigor (significance/CIs).

**Collaborators ahead (7-day alignment sprint).** Fold both accelerators into the team's shared semantic-layer
framework rather than maintain separate solutions: **Indradeep** — anchor A1 to the enterprise semantic-layer
architecture and patterns; **Stan** — integrate observability + governance, align our (superset) grounding with
his runtime guardrail across the dev+prod lifecycle, and scope the gating roadmap; **Chaitanya** — merge or
complement the existing benchmarking harness (one tool, not two); **Ariella & Michael** — position A2 as the
measurement module within their full framework; **Nadeem** — build the RODA → HealthOmics bioinformatics-workflow
skill with graduated human-in-the-loop. A **group meeting (Day 6)** consolidates into one framework, assigns
module owners, and opens a shared channel; publish decision by Day 7. *(Detailed table + timeline below and in
`next-steps-onepager.md`.)*

## Why this is differentiated (the "more than building blocks" answer)

## Why this is differentiated (the "more than building blocks" answer)
- **A2's grounding is a superset of Bedrock Contextual Grounding.** Contextual Grounding is KB-literature-only,
  requires a Bedrock KB, and depends on AgentCore Gateway. Ours measures **tool-provenance across all sources**
  (lake/graph/OLS/KB/RODA), is **tier-aware** (works even with no tools), needs **no KB/Gateway dependency**, and
  adds **provenance-faithfulness** (fabricated-grounding detection). It generalizes the metric to real research agents.
- **A1's value is the harmonization + BYOD method**, demonstrated on oncology — de-risking the leap clients face
  today (RAG-on-documents, no semantic layer) toward a **governed semantic layer**.
- **Governed, auditable access by design:** our custom-tool architecture supports **per-user DB credentials**
  (assume-role per identity → CloudTrail/Neptune per-user audit) — the drop-in Neptune MCP servers can't
  (single-identity only). A concrete governance advantage for multi-tenant, enterprise use.

## Collaboration plan (7-day alignment sprint, then build)
Fold our work into the shared framework rather than maintaining separate solutions:

| Stream | Collaborator | Our role / integration |
|---|---|---|
| Semantic-layer architecture & patterns | **Indradeep** | Anchor A1 as the reference implementation of the enterprise construct |
| Observability & governance | **Stan** | Our grounding (superset) + his runtime guardrail = full dev+prod lifecycle |
| Existing benchmarking app | **Chaitanya** | Merge/complement harnesses — one benchmarking tool |
| Full evaluation framework | **Ariella & Michael** | A2 as the semantic-hub-value measurement module within it |
| Bioinformatics workflows + graduated automation | **Nadeem** | RODA→HealthOmics ETL skill with step-by-step HITL (hands-on dev) |

**Sprint:** individual syncs (days 1–5) → group meeting to consolidate + assign owners + shared channel (day 6)
→ publish decision (day 7). Detail in the one-pager.

## Ask / decisions needed from the lead team
1. **Endorse the positioning:** A1 = method+BYOD (not TCGA); A2 = the measurement module today (attempt-and-attribute), with governance/gating as the roadmap toward a CI-gate.
2. **Bless the 7-day alignment sprint** and the collaborator syncs above.
3. **Guidance on demo scope** — we propose *one* substantial persona-based research demo (EGFR-GBM + RODA BYOD +
   graduated HITL) over many lightweight features, consistent with "let customer engagements inform implementation."

## What we are explicitly *not* doing yet
Over-building concrete features before customer input and before framework alignment — to avoid duplication and
premature solutions. Post-alignment, highest-leverage build = A2⇄Stan integration + the one persona demo.
