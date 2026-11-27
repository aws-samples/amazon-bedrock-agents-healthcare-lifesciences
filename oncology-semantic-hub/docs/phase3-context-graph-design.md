# Feature 3 Deep-Dive — Human-Feedback-Enriched Semantic Hub (context graph)

**Status: DESIGN / RESEARCH (2026-08-11).** Literature synthesis + a first architecture proposal for
enriching the Oncology Semantic Hub with human feedback. Intended for iteration before build (target v1.3.0).
Companion to `docs/phase3-plan.md`.

---

## 1. Problem

The curated hub (PrimeKG + TCGA + OLS) holds *systems-of-record facts*. It does **not** hold the
**institutional knowledge** an oncology researcher carries: how *they* process their cohort, local
terminology ("we call this assay X"), which associations *they* treat as actionable, corrections to
mismapped entities. Today that knowledge lives in the human's head and is lost between sessions.

**Goal:** capture that human knowledge, store it in the hub as a *distinct, governed knowledge tier*, and
use it to improve the agent's answers on *their* data — measurably, without fine-tuning.

---

## 2. Literature synthesis (the "deep research")

Five converging research threads, and what each contributes to our design.

### 2.1 The context-graph / decision-trace loop
- **Arize — "Using context graphs" (Apr 2026)** and **"Self-improving agent on a context graph of human
  disagreement" (May 2026)**; **Foundation Capital context-graphs thesis.** Unit of capture = the
  **decision trace** (trigger → agent proposal → human resolution + reason → outcome). Entities/relations
  *emerge* from traces. Loop = **capture → annotate → mine → improve** (feed patterns back as config/prompt,
  **not** fine-tuning). Demonstrated 53.8% → 83.1% agreement with the human reviewer over 4 cycles.
- **Takeaway for us:** the atomic capture is *(agent answer → human correction + reason)*. Improvement is a
  retrieval/config loop, not retraining. Ownership/portability matters (keep it in our lake/graph, open format).

### 2.2 Agent memory architectures
- **MemGPT** (Packer et al. 2024, OS-like context paging); **Generative Agents** (Park et al. 2023, memory
  stream + **reflection** + retrieval by recency/importance/relevance); **Reflexion** (Shinn et al. 2023,
  arXiv 2303.11366, verbal self-critique episodic buffer); **Voyager** (Wang et al. 2023, skills-as-code).
- **Temporal Knowledge Graph for Agent Memory** (arXiv 2501.13956, Zep/Graphiti): dynamic, **bi-temporal**
  knowledge integration — facts have validity intervals, beliefs update over time.
- **Takeaway:** use a **memory stream + periodic reflection/consolidation**; track **temporal validity**
  (user context goes stale); split ephemeral prefs (memory) from durable domain facts (graph).

### 2.3 Knowledge-graph enrichment / refinement with humans in the loop
- **KARMA** (arXiv 2502.06472): multi-agent LLM KG enrichment; 83.1% LLM-verified correctness; **conflict-edge
  reduction** via multi-layer assessment.
- **"Conversation-Driven Refinement of KGs: True Active Learning in the Chatbot Loop"** (Springer 2023):
  user feedback in the app loop refines **both** the KG **and** the extraction process; tolerates incompleteness.
- **Ontology curation HITL / task design** (ACM 3626960); **Explainable automatic KG construction HITL**;
  **Biological knowledgebase HITL literature curation** (PMC12904773 — directly oncology-adjacent).
- **Agentic Deep Graph Reasoning** (arXiv 2502.13025): feedback-driven loops yield *self-organizing*
  knowledge networks (hub formation, bridging nodes).
- **Takeaway:** human feedback should refine the graph **additively and reversibly**, with explicit
  **conflict detection** — never silent overwrite of curated facts.

### 2.4 Provenance-grounded / trustworthy memory  ← *most aligned with our existing model*
- **Eywa — "Provenance-Grounded Long-Term Memory"** (arXiv 2605.30771): **store immutable source evidence
  BEFORE deriving canonical facts**; validate derived memories against typed signals + source support;
  deterministic retrieval with **zero LLM calls inside retrieval**.
- **NeuSymMS — Hybrid Neuro-Symbolic Memory** (arXiv 2605.17596): continuity without context bloat, avoids
  cross-entity contamination, **auditable**.
- **Survey of Evidence Tracing & Execution Provenance in LLM Agents** (arXiv 2606.04990): execution provenance
  = a **typed graph** connecting evidence → claims → actions → answers.
- **Provenance-Aware Tiered Memory** (arXiv 2602.17913): memory must be evidence-faithful + auditable + economical.
- **EpisTwin — KG-grounded neuro-symbolic Personal AI** (arXiv 2603.06290): user-centric **Personal Knowledge
  Graph** built from semantic triples lifted from the user's data.
- **PAHF — Learning Personalized Agents from Human Feedback** (arXiv 2602.16173): 3-step loop —
  (1) pre-action **clarification**, (2) **ground** actions in retrieved preferences, (3) **post-action feedback**
  updates memory when preferences drift.
- **Takeaway:** this is our home turf. We already tag provenance and score faithfulness per layer. The design
  should **(a) keep raw human input immutable + provenance-stamped, (b) derive canonical user facts separately,
  (c) tag them a distinct tier, (d) keep retrieval deterministic/auditable.**

### 2.5 Self-improving / experiential agents (feedback without fine-tuning)
- **ExpeL** (arXiv 2308.10144): gather experiences → extract NL insights → recall at inference.
- **ERL** (arXiv 2603.24639): reflect on trajectories → transferable **heuristics** → retrieve + inject at test
  time (selective retrieval essential; +7.8% on Gaia2).
- **EXG — Self-Evolving Agents with Experience Graphs** (arXiv 2605.17721): an **experience graph** as external
  memory, online growth + offline consolidation.
- **Takeaway:** consolidate raw corrections into **retrievable heuristics/canonical facts**; **selective
  retrieval** of only-relevant user context is critical (don't dump everything into context).

---

## 3. Where our hub is uniquely positioned

Most personalization/memory work fuses user data into a **flat** store. Our differentiator: user context
enters a **provenance-governed, ontology-anchored semantic hub**, where it is:
1. a **distinct authority tier** (`[UserContext]`), never fused with PrimeKG's authority;
2. **linked to canonical MONDO-anchored entities** (genes/diseases/drugs) — so "our assay for *EGFR*" attaches
   to the exact EGFR node, not a name;
3. **measurable** — the same benchmark (Accelerator 2) quantifies the correctness lift from adding user context.

The **faithfulness framework becomes the governance mechanism**: a `[UserContext]` claim is *faithful* (honest
attribution) even when it disagrees with the curated graph — the system never presents user opinion as curated fact.

---

## 4. Proposed architecture (v1 for iteration)

A six-stage loop, mapping the literature onto our stack (Neptune + Athena + OLS + AgentCore Memory + benchmark):

```
 (1) CAPTURE            (2) DERIVE/CONSOLIDATE      (3) STORE (governed)
 human correction  ──▶  lift verbatim event into ──▶  Neptune :UserContext nodes (durable, entity-linked)
 or "remember…"         canonical user facts          + AgentCore Memory (ephemeral prefs)
 (immutable event)      (reflection, ExpeL-style)     both tagged [UserContext] + provenance + validity-time
        │                                                        │
        ▼                                                        ▼
 (6) MEASURE  ◀── (5) GOVERN/CONFLICT ◀────────────── (4) RETRIEVE @ inference
 benchmark lift       detect contradiction w/ curated     selective retrieval of relevant user context;
 (Accelerator 2)      graph; surface both, don't          agent injects it, tagged [UserContext]
                      overwrite; user-tier authority
```

**Stage 1 — Capture (immutable, provenance-first; per Eywa).** Two entry points: (a) conversational
("remember that we treat X as…"), (b) explicit correction on a specific agent answer (the decision-trace unit,
per Arize). Write a `:UserContextEvent` — verbatim text + who/when/session + the agent answer it corrects.
**Never mutate curated nodes at capture time.**

**Stage 2 — Derive/consolidate (reflection; per Generative Agents / ExpeL / ERL).** A separate step lifts events
into typed, canonical facts: `:UserPreference`, `:TerminologyMapping` (their term → canonical CURIE via OLS),
`:Correction` (proposed fix to a mapping), `:Heuristic` ("for our cohort, prefer…"). Each carries confidence +
validity interval + link to source event. Consolidation can be on-write (small) or periodic (mining, Arize-style).

**Stage 3 — Store (hybrid; per NeuSymMS / EpisTwin).** Durable, entity-linked domain knowledge → **Neptune**
nodes attached to the canonical gene/disease/drug (ontology-anchored). Ephemeral conversational prefs →
**AgentCore Memory** (semantic strategy). Both provenance-stamped and scoped (per-user/org).

**Stage 4 — Retrieve @ inference (selective; per ERL).** A new `query_user_context` tool (or graph traversal)
pulls **only relevant** user context for the current question and injects it; the agent tags any use `[UserContext]`.

**Stage 5 — Govern / conflict (per KARMA conflict-edges + our faithfulness model).** If user context contradicts
the curated graph, the agent **surfaces both with distinct tags** and notes the conflict — no silent override.
User-tier authority is explicitly lower than curated; a policy decides "user-context-wins-for-this-user" vs
"flag-for-review". Auditable lineage back to the source event.

**Stage 6 — Measure (the compounding loop; ties to Accelerator 2).** Re-run the benchmark on the user's question
set **with vs without** their context → report correctness lift (our analog of Arize's 53.8%→83.1%). This closes
Accelerator 1 ↔ 2 and makes "self-improving" a *measured* claim, not an assertion.

---

## 5. Design principles (distilled from the literature)
1. **Immutable capture, derived facts** (Eywa) — raw human input is never overwritten; canonical facts are derived + revisable.
2. **User context is a distinct provenance tier** (`[UserContext]`) — extends our layer-aware faithfulness scorer; not fabrication when legitimately user-contributed.
3. **Additive + reversible** (KG-HITL) — never silently mutate curated PrimeKG; corrections are proposals with lineage.
4. **Selective retrieval** (ERL) — inject only relevant user context; avoid context bloat / contamination (NeuSymMS).
5. **Temporal validity** (Graphiti/Zep) — user context can go stale; track validity; support belief updates + drift (PAHF).
6. **Conflict surfaced, not resolved silently** (KARMA) — show curated vs user with tags; explicit authority policy.
7. **Feedback without fine-tuning** (ExpeL/ERL/Arize) — improvement is retrieval + config, auditable and reversible.
8. **Measured improvement** (Arize) — quantify lift with the benchmark; don't assert self-improvement.

---

## 6. Open questions to iterate
- **Capture UX:** conversational vs structured form vs document upload (or all three)?
- **Consolidation:** on-write vs periodic mining? Who approves promoting a correction to a canonical user fact (auto vs human-gated)?
- **Storage split:** exact boundary between Neptune `:UserContext` (durable/structured) and AgentCore Memory (ephemeral/conversational)?
- **Conflict policy:** default authority when user context contradicts curated data (user-wins-scoped vs flag-for-review)?
- **Scoping/security:** per-user vs per-org isolation; PHI/governance implications of storing user-contributed clinical context.
- **Verbatim vs mined:** store raw assertions (simple, transparent) vs mine clusters (Arize-style, needs volume)? Start verbatim.
- **Measurement protocol:** how is the "user's question set" constructed to measure lift honestly (avoid teaching-to-the-test)?

---

## 7. Suggested phased build (v1.3.x)
- **v1.3.0-a (spike):** capture + store `:UserContext` (terminology mapping + preference), a `query_user_context`
  tool, `[UserContext]` provenance tag added to the faithfulness scorer. Manual/verbatim, single-user.
- **v1.3.0-b:** conflict surfacing vs curated graph; selective retrieval; temporal validity.
- **v1.3.0-c:** measurement — benchmark lift with/without user context on a small user question set (the compounding-loop proof).
- **v1.3.0-d (optional):** mining/consolidation of repeated corrections into heuristics (Arize-style), if volume warrants.

---

## 8. How the top papers answer the five open questions

Deep reads of Eywa (provenance memory), PAHF (personalized agents from human feedback; Meta/Princeton, with regret proofs), and EpisTwin (personal KG) resolve most of §6. Each row: what the papers do → our decision.

| Question | Eywa | PAHF | EpisTwin | **Our decision** |
|---|---|---|---|---|
| **1. Capture UX** | Implicit: route turns to an evidence pipeline; typed-signal detection (corrections, decisions, dates) | **Two explicit channels**: pre-action *clarification* (resolve ambiguity before acting) + post-action *correction* (fix a wrong answer); a salience detector drops non-informational feedback | Lift cross-app data into triples | **Dual-channel, post-action-first.** Primary = correction-on-an-answer (the decision-trace unit; PAHF proves it's *essential*). Secondary = conversational "remember that…" (pre-action/volunteered). Salience filter to avoid storing "thanks". |
| **2. Storage split** | 3 objects: **Evidence** (immutable) → **Signals** (typed) → **Beliefs** (revisable, LLM-derived). Extraction is an *index over* evidence | Per-user note store (SQLite/FAISS), NL note + embedding, strictly user-isolated | **User-centric Personal KG** of semantic triples (beats flat vector RAG) | **Immutable `:UserContextEvent` (verbatim) → derived `:UserContext` nodes in Neptune (revisable, entity-linked) + AgentCore Memory for ephemeral prefs.** Neptune (not flat) for durable domain knowledge, per EpisTwin. |
| **3. Conflict authority** | *Evidence precedes belief*; write-time **supersession** (≤1 active fact per slot); include superseded on contradiction; provenance = source support, **not truth** | Post-action feedback **overwrites** the user's own stale belief (drift); pre-action alone is brittle once the agent is "confidently wrong" | KG grounding + re-grounding | **Two policies:** (a) user-vs-user-prior → supersede (newest wins, keep old). (b) **user-vs-curated-graph → never overwrite curated; surface both with distinct tiers `[UserContext]` vs `[Graph]`**; user-tier authoritative *within the user's scope*, flagged as differing from canonical. Governance via our faithfulness model. |
| **4. Verbatim vs mined** | **"Extraction is an index, not the memory"** — verbatim evidence is authoritative; facts are a revisable index | detect → summarize → integrate (merge near-duplicates via similarity τ) | triples | **Verbatim-first + derived index.** Light consolidation (merge near-dupes, PAHF-style). Full mining/clustering (Arize) only at volume. |
| **5. Measurement** | Diagnostic **failure taxonomy** (coverage/retrieval/revision/scope/synthesis gaps); per-question traces; refusal-aware | **4-phase protocol** (learn → test → drift → adapted-test) + **ACPE** metric + regret bound O(K+γ); separates initial learning from drift adaptation | PersonalQA synthetic benchmark, multi-judge | **PAHF 4-phase + Accelerator-2 harness.** Measure correctness lift on the user's question set *with vs without* context; add a **drift phase** (change a convention → does it adapt?); use Eywa's taxonomy to localize failures. Hold out a test split (≠ correction set) to avoid teaching-to-the-test. |

**Load-bearing insights:** (i) PAHF's proof that *post-action correction is necessary* (pre-action alone can't fix "confidently wrong" drift) → our capture must center corrections. (ii) Eywa's *evidence-before-belief* + *index-not-memory* → never overwrite raw user input; derived facts are revisable. (iii) EpisTwin → a **graph** personal store captures topology/temporal structure a flat vector store misses — aligns with putting user context in Neptune, linked to canonical entities.

---

## 9. What user context brings to *our* scientific question set

Conceptualizing against the 84-Q EGFR-GBM benchmark categories. User context is not trivia — in oncology it changes *which answer is correct for this researcher*. Six context types and the questions they move:

| User-context type | Example (oncology) | Question categories it changes | Effect |
|---|---|---|---|
| **Terminology mapping** | "our lab's 'EGFR-amp panel' = EGFR amplification"; "'GBM' for us = primary GBM only" | ontology, reconciliation, lake | Resolves the user's term to the canonical entity before querying |
| **Cohort convention** | "we count a gene as recurrent at **≥5** patients, not ≥10"; "exclude secondary GBM" | multi_source, quantitative_precision, reconciliation | **Changes counts** — e.g., the recon_027 gene set, the multi_source driver list |
| **Actionability preference** | "our tumor board treats EGFRvIII as actionable via trial NCT-xxxx even without an on-label drug" | actionability, drug_gene_relationships, evidence | Adds the institution's actionability call the curated graph lacks |
| **Mapping correction** | "in our re-analysis TCGA-LGG maps to MONDO:0021637" | reconciliation | **Fixes/annotates** the exact LGG-misalignment case in our demo |
| **Method/threshold preference** | "pathogenic only at ClinVar ≥2-star"; "we annotate with VEP flags X" | evidence, actionability, quantitative_precision | Changes interpretation/filtering of variants |
| **Ranking preference** | "when listing druggable genes, prioritize those with active trials at our center" | multi_source, drug_gene (top-k) | Re-orders ranked-list answers to the user's priorities |

### The demonstrable beat (ties to Accelerator 2)
Take a question where L3 gives the **canonical** answer, add user context, and show the answer shifts to the **user-appropriate** one with `[UserContext]` + `[Graph]` provenance — and reverts when context is removed. Two concrete demos:
- **recon_027** ("genes associated with glioblastoma"): canonical **144** `[Graph]`. Add convention *"we define GBM-associated as COSMIC Tier-1 **and** druggable"* → agent returns the user-scoped subset, tagged `[UserContext]`+`[Graph]`, and explains the scoping. Removing the context reverts to 144.
- **Actionability** ("is EGFRvIII actionable in GBM?"): canonical = limited on-label. Add *"our board treats it actionable via NCT-xxxx"* → agent surfaces **both** the canonical evidence `[Graph/KB]` **and** the institutional call `[UserContext]`, clearly separated.

### Why this is the right proof for a *scientific* hub
A researcher's value question is rarely "what's the canonical fact?" — it's "what's the answer **given how we work**?" The curated hub answers the former; user context lets it answer the latter **without corrupting the canonical layer**. And because we already score provenance per layer, we can *prove* the answer used the user's context honestly (tagged `[UserContext]`), never passing institutional opinion off as curated fact.

---

## 10. Concrete measurement protocol (PAHF 4-phase, adapted to the hub)
1. **Phase 1 — Learn.** User issues corrections/conventions on a set of questions (e.g., the 6 context types above). Captured as `:UserContextEvent` → derived `:UserContext`.
2. **Phase 2 — Test (initial).** Ask a *held-out* set of questions that depend on those conventions (same conventions, different questions). Score correctness vs the **user's** ground truth, with vs without context. Expected: lift (our analog of Arize 53.8%→83.1%).
3. **Phase 3 — Drift.** User changes a convention (e.g., threshold ≥5 → ≥3). Does the agent adapt after a correction (post-action), or stay "confidently wrong" (PAHF's key failure of pre-action-only)?
4. **Phase 4 — Test (adapted).** Re-test on the drifted convention. Metric: ACPE (avg cumulative personalization error) + per-question provenance trace (Eywa taxonomy) to localize any residual failure.

**Guardrail:** the correction set (Phase 1/3) and the test set (Phase 2/4) are disjoint → measures generalization of the learned context, not memorization.

---

## References (credited)
Arize context-graph essays (Apr/May 2026); Foundation Capital context-graphs thesis. MemGPT (Packer 2024);
Generative Agents (Park 2023); Reflexion (Shinn 2023, arXiv 2303.11366); Voyager (Wang 2023); ExpeL
(2308.10144); ERL (2603.24639); EXG (2605.17721). KARMA (2502.06472); Conversation-Driven KG Refinement
(Springer 2023); Ontology curation HITL (ACM 3626960); Biological knowledgebase HITL curation (PMC12904773);
Agentic Deep Graph Reasoning (2502.13025); Temporal KG for Agent Memory / Graphiti-Zep (2501.13956).
Eywa Provenance-Grounded Memory (2605.30771); NeuSymMS (2605.17596); Evidence-Tracing/Execution-Provenance
survey (2606.04990); Provenance-Aware Tiered Memory (2602.17913); EpisTwin Personal KG (2603.06290);
PAHF Personalized Agents from Human Feedback (2602.16173).
