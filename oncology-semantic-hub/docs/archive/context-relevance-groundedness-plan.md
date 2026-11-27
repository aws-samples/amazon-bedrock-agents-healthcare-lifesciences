# Metrics expansion plan — Context Relevance + Groundedness (expose the L1 < L3 *context* gap)

**Status:** Plan / design (not started). Complements `validation-framework-status.md` (v2 re-baseline) and the
live-groundedness UI design (`live-groundedness-ui-design.md`, P0.4).

## Why (the gap in today's metrics)
Our v2 re-baseline uses AgentCore **Faithfulness** (non-contradiction with tool outputs, 5-level ordinal) +
**Correctness** + Reproducibility. But **Faithfulness cannot separate L1 from L3** — both score ~1.0 (L1 0.992,
L3 1.000) because a lake-only agent that answers from thin context or **defers** does not *contradict* its tool
outputs, so it is "faithful." Correctness separates them (0.38 vs 0.97) at the **answer** level, but we have **no
metric on the *context itself*** — i.e. *was the retrieved/assembled context relevant and sufficient?*

**The motivating case — the Fisher's test (co-occurrence beat).** Both L1 and L3 correctly *defer* the
statistical test (both Faithfulness 1.0). The difference is the **data each would hand downstream**:
- **L3** assembles a real, multi-source, provenanced contingency (tcga_mutations 82/371 **+** cBioPortal 253/570,
  with denominators/snapshot) → **relevant, sufficient** input for a valid Fisher test.
- **L1** assembles a thin/textbook co-occurrence narrative, **no cBioPortal, no cohort contingency** → **not
  relevant / insufficient** — a downstream test on it is **garbage-in**.

Faithfulness scores both 1.0; **Correctness** catches L1's wrong answer — but neither *directly measures the
quality of the context sent downstream.* That is the metric we're missing.

## Metric 1 — Context Relevance (AgentCore built-in)
**AgentCore definition** (trace-level): *"whether the passage provides information necessary to contribute to
correctly and completely answering the question."* Scale: **Not Relevant · Partially Relevant · Perfectly
Relevant**; placeholder `{retrieved_passages}`.
- **Use:** score each question's retrieved/assembled context (the tool outputs) for relevance+sufficiency.
- **Expected:** on graph/KB/multi-source questions (drug, ontology, co-occurrence) **L3 = Perfectly Relevant**
  (it pulled the right rows/passages) vs **L1 = Not/Partially Relevant** (thin lake-only context) — the first
  metric that shows L1's *context* is worse, independent of the answer.
- **Open question (verify first):** AgentCore's Context Relevance is RAG-oriented (`{retrieved_passages}`). We
  must confirm how it populates that placeholder for a **tool-using** agent (does it map tool outputs → passages
  automatically, or only KB-retrieval spans?). If it doesn't map tool outputs, implement a **custom
  context-relevance judge** over the captured tool outputs (same rubric).

## Metric 2 — Groundedness (support-based; stronger than AgentCore Faithfulness)
AgentCore Faithfulness = **non-contradiction**. We want **support/entailment**: *is each claim actually backed by
the retrieved context?* — which a deferring/thin answer fails. Options:
- **(a) Bedrock Guardrails — contextual grounding** (AWS-native): returns a **grounding** score (response
  grounded in source) **and** a **relevance** score (response relevant to query), with configurable thresholds
  → usable as an inline gate *and* an offline metric. Closest AWS "groundedness."
- **(b) Custom LLM-judge (RAGAS-style faithfulness/groundedness):** decompose answer into claims; mark each
  **SUPPORTED / NOT-SUPPORTED** by the context; score = supported ÷ total. Stronger discriminator than
  non-contradiction; also feeds the **live UI chip** (P0.4) so live == offline.
- **Recommendation:** (b) as the primary support-based groundedness (reused by the live chip); optionally (a)
  as an independent AWS-native cross-check / inline gate.

## Metric 3 — Downstream-input adequacy (the Fisher tie-in)
A targeted, **deterministic** check for the co-occurrence/statistical questions: does the assembled context
contain a **complete, sourced contingency** ready for a valid test?
- Checks: all 2×2 cells present · denominators present · each cell provenance-tagged (lake + cBioPortal) · no
  fabricated statistic.
- **L3 → adequate; L1 → inadequate** (missing cBioPortal / cohort cells). This converts "context quality" into a
  concrete **"is the downstream statistical input trustworthy?"** signal — the sharpest version of the story.

## Data dependency (shared with P0.4)
All three need the **retrieved/assembled context captured per question** = the **evidence bundle** from
`live-groundedness-ui-design.md` (agent returns `{answer, evidence[], layer}`). Building it once unblocks: the
live UI chip, Context Relevance, support-based Groundedness, and downstream-adequacy. **Do the evidence bundle
first.**

## Expected headline once added
| Metric | L1 | L3 | separates L1/L3? |
|---|---|---|---|
| Faithfulness (non-contradiction) | ~0.99 | ~1.00 | ✗ (both pass) |
| **Context relevance** | Not/Partially | Perfectly | **✓** |
| **Groundedness (support-based)** | low | high | **✓** |
| Correctness | 0.38 | 0.97 | ✓ |
| Downstream-input adequacy (Fisher) | inadequate | adequate | **✓** |

→ The narrative gains a **context-layer** proof: L3's advantage is that it **retrieves and assembles the right,
sufficient, sourced context** — which is what makes the downstream compute (Fisher) valid.

## Phasing
- **P1 — Evidence bundle** (shared with P0.4): agent returns its tool outputs per question.
- **P2 — Context Relevance:** add `Builtin.ContextRelevance` to `run_agentcore_eval.py` EVALUATORS (verify the
  `{retrieved_passages}` mapping; else custom judge) → run L1 vs L3 on the 63-Q + demo beats.
- **P3 — Support-based Groundedness:** custom RAGAS-style evaluator (reused by the live chip); optional Guardrails
  contextual-grounding cross-check.
- **P4 — Downstream-input adequacy:** deterministic contingency-completeness scorer for the co-occurrence questions.

## Open decisions
1. Confirm whether AgentCore Context Relevance auto-maps **tool outputs** → `{retrieved_passages}` for tool
   agents, or if we need a custom context-relevance judge.
2. Groundedness = custom RAGAS-style judge (recommended, reused by live chip) vs Bedrock Guardrails contextual
   grounding vs both?
3. Scope: 63-Q benchmark, the demo beats, or both? (Recommend: demo beats first — cheap, and the Fisher story is
   the motivator — then the 63-Q.)
