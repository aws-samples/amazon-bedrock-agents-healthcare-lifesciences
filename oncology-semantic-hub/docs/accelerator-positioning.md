# Accelerator Positioning

**Status: STRATEGIC (2026-08-12).** The enduring positioning of the two accelerators — their current and future
place within the enterprise semantic-layer vision. *Current implementation detail:*
[whitepaper-section-4.1-draft.md](whitepaper-section-4.1-draft.md). *Tactical execution plan (owners, meetings, timeline):* [next-steps-onepager.md](next-steps-onepager.md).
*Feature backlog:* [backlog.md](backlog.md).

---

## The reframe: the accelerator is the *method*, not the sample data
Composed of existing building blocks (knowledge graph, public datasets, ontology service, agent runtime), a hub
pitched as "we loaded the data" is table stakes. The durable value is the **method** each accelerator embodies:

- **Accelerator 1 — Semantic Hub Starter + BYOD:** the **KG + L3 constructs** (graph traversal + ontology
  harmonization) and a **repeatable bring-your-own-data pipeline** (open datasets *and* a customer's own cohort).
  The oncology hub is the **reference implementation**, not the value.
- **Accelerator 2 — Semantic Hub Benchmark Framework:** an **objective measurement** of whether the semantic
  layer is worth the investment, and whether a given addition *helps or poisons* the agent's answers.

## Position within the enterprise semantic-layer vision
Clients today run **RAG over documents with no formal semantic layer.** The industry direction is a **governed
semantic layer as an enterprise construct** (federated architecture, governance, quality mechanisms, CI/CD,
observability, feedback loops). Our two accelerators are **modules of that vision**, not standalone products:
- **A1** = the concrete reference implementation + the method to build one — de-risking the leap from
  "RAG on docs" to a governed semantic layer.
- **A2** = the measurement discipline that quantifies the layer's value and quality.

## Current position (today)
- **A1:** a deployable hub — knowledge graph + patient-data lake + ontology resolution — with a **documented BYOD
  process** (two integration modes: extend the core graph or add to the lake; a 5–6 step discover→process→wire→
  validate flow), **governed per-user, auditable data access** by design, and an env-driven, tested deploy path.
  (Implementation: [whitepaper-section-4.1-draft.md](whitepaper-section-4.1-draft.md).)
- **A2:** a three-dimension benchmark — **correctness, reproducibility, grounding/faithfulness** — across a
  bare-LLM → flat-data → semantic-hub capability ladder, operating in an **"attempt-and-attribute"** mode (agents
  attempt every question and tag provenance). Includes a **grounding metric that is a superset of Bedrock
  Contextual Grounding** (tool-provenance across all sources, tier-aware, no KB/Gateway dependency) plus
  layer-aware **provenance-faithfulness** (fabricated-grounding detection).

## Future position (what they work toward)
- **A1:** substantiated **beyond the reference dataset** (persona-based research demos, additional data
  modalities such as imaging), aligned to the **enterprise semantic-layer patterns**, with a resolved
  **multi-tenant, governed access** architecture.
- **A2:** **governance/gating** layered on top of measurement — evolving toward a **CI-gate** that decides what
  belongs in the semantic layer — plus **context-poisoning detection**, expert-validated ground truth,
  statistical rigor, and cross-model comparison.

## Why this is differentiated (beyond the building blocks)
1. **Grounding as a superset** of existing consistency/grounding checks — measures real tool-provenance across
   graph, lake, ontology, and literature, on any capability tier, without a KB or gateway dependency.
2. **Harmonization + BYOD method** — a repeatable way to bring heterogeneous data into a governed semantic layer,
   demonstrated on oncology rather than sold as oncology data.
3. **Governed, auditable access by design** — per-user identity at the data layer, which drop-in connectors do not provide.

## Integration posture (combine, don't duplicate)
The accelerators are designed to **converge with adjacent capability streams** rather than compete with them:
runtime **observability & governance**, existing **benchmarking** efforts, a broader **evaluation framework**, and
**bioinformatics-workflow automation**. A2 is complementary to runtime grounding checks (dev-time benchmark +
runtime guardrail = full lifecycle); A1 is the reference implementation of the shared semantic-layer pattern.
The governing principle is **one cohesive framework, not parallel silos.**

## Path to field-ready (high level)
A field team can **deploy the pattern into a customer account, onboard the customer's data, and prove value** —
integrated with the broader framework. The enabling pillars: repeatable BYOD deploy · one compelling
persona-based demo · objective value proof (A2) · runtime observability · governance/quality story · enablement
materials. *(Sequenced execution, owners, and timeline: [next-steps-onepager.md](next-steps-onepager.md).)*
