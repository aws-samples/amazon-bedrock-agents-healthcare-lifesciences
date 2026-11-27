# Live groundedness metric in the Compare UI — design (planning)

**Status:** Design / planning (not yet implemented). Additive only; does not modify the Core graph or the
subject model. Aligns to — does not replace — `context-traceability-design.md` (§4a metrics, P0.3 evidence
card) and the O1 groundedness-gate concept.

## 1. Goal & non-goals
**Goal:** show a **per-question groundedness score + disposition** in each answer column of the Compare UI,
computed **inline and displayed immediately with the answer** (no async pipeline, no CloudWatch round-trip),
using **LLM-as-judge** faithfulness (answer vs the agent's own retrieved context).

**Non-goals (v1):**
- Not a delivery-time **gate** (blocking/rewriting). v1 is **display-only**; gating is the O1 follow-on and is
  a one-flag extension once the score is live.
- Not a replacement for **batch/native** evaluation — the live chip is the *surfacing*; native
  `Builtin.Faithfulness` + Correctness + Reproducibility remain the offline source of truth.
- Not L0 faithfulness (per decision): L0 has no retrieved context → **N/A** badge + list its cited sources.

## 2. What we measure (definition + parity)
**Live groundedness = LLM-judge faithfulness:** given `(question, answer, evidence)`, does every factual claim
in `answer` follow from / not contradict the `evidence` (the agent's tool outputs)? Score ∈ [0,1] + per-claim
support. This mirrors **`Builtin.Faithfulness`** semantics so the **live score is consistent with the batch
score** (same rubric; §9). It measures **grounding, not correctness or completeness** — surfaced in the chip
tooltip so viewers don't over-read it.

**Disposition (shown as the chip):**
- **RELEASE** — answer fully grounded in retrieved evidence.
- **CAVEAT** — grounded inputs, but a step is explicitly **deferred/uncomputed** (e.g. Beat 5 "run Fisher in a
  compute step") or partial coverage.
- **WITHHOLD** — claims **not supported** by retrieved context (ungrounded).
- **REFUSED (grounded)** — answer correctly declines because data isn't loaded (Beat 5b protein) → a *good*
  outcome, distinct from WITHHOLD.
- **N/A** — no retrieved context exists to score against (L0).

## 3. Architecture (data flow)
```
 UI (Compare)                 Agent Runtime (per layer)              Inline scorer (judge)
 ───────────                  ─────────────────────────              ─────────────────────
 prompt ───────────────────▶  invoke(): stream answer               (Bedrock Converse, temp 0)
                              + CAPTURE tool events  ──────────┐
                              return {answer, evidence[]}       │
 answer + evidence  ◀──────────────────────────────────────────┘
        │
        ├─ render answer (as today)
        └─ score(question, answer, evidence) ──▶ judge ──▶ {score, per_claim[], disposition}
                                                              │
                                              render CHIP + expandable "why"
```
**Key design choice — where the evidence comes from.** Faithfulness needs the *retrieved context*, which the
agent currently throws away. Three options:
- **(A) Agent emits an evidence bundle in its response** *(recommended)* — the `invoke` entrypoint already
  streams events; capture each tool's `(name, input, output)` and return
  `{"answer": ..., "evidence": [...]}` instead of a bare string. Deterministic, synchronous, no extra latency
  to fetch. Additive to `semantic_hub_agent.py`.
- **(B) Fetch the OTel trace/spans post-answer** — same source native Faithfulness uses, **but async**
  (spans take seconds–minutes to ingest; we saw a 180 s batch delay). ✗ violates "immediately with the answer."
- **(C) UI re-runs retrieval** — redundant, and may diverge from what the agent actually used. ✗
→ **Adopt (A).**

## 4. Component 1 — Evidence bundle (agent → UI)
Return shape (backward-compatible: UI treats a plain string as "no evidence"):
```json
{
  "answer": "…final text…",
  "evidence": [
    {"tool": "query_patient_data", "input": "SELECT … FROM tcga_mutations …",
     "output": "[{\"hugo_symbol\":\"EGFR\",\"n\":82}, …]", "provenance": "Lake: tcga_mutations", "rows": 5},
    {"tool": "knowledge_search", "input": "EGFR resistance glioblastoma",
     "output": "…passages…", "citations": ["PMID:33187135"], "provenance": "KB: AT3NALHGQK"}
  ],
  "layer": "L3"
}
```
- Captured in `invoke()` from the Strands stream's tool-use / tool-result events (additive; the answer text
  path is unchanged).
- **Truncation policy:** cap each tool `output` (e.g. first N rows / M chars) to bound judge cost; keep the
  fields the answer's claims reference.
- **L1** naturally emits only `query_patient_data` evidence; **L0** emits `evidence: []`.

## 5. Component 2 — Inline scorer (LLM-as-judge)
- **Model:** a judge via Bedrock Converse, **temperature 0**, small `maxTokens`. Decision pending (§12):
  same Sonnet 4.5 (consistency) vs a **separate/independent** judge (less self-preference bias).
- **Prompt/rubric (parity with `Builtin.Faithfulness`):** "Given QUESTION, EVIDENCE (tool outputs), and
  ANSWER, mark each factual claim as SUPPORTED / NOT_SUPPORTED / DEFERRED(explicitly not computed). Return
  JSON: `{score: supported/total, claims: [...], deferred: bool, disposition}`." Deterministic JSON out.
- **Output schema:** `{score: float, claims: [{text, verdict, evidence_ref}], deferred: bool,
  disposition: RELEASE|CAVEAT|WITHHOLD|REFUSED|NA}`.
- **Latency budget:** one extra call, ~2–5 s, fired **after** the answer streams; chip shows a **"scoring…"**
  state then resolves. Score per layer independently (parallelize across columns).
- **Determinism add-on (optional):** for structured anchors (82, 253, 31, MONDO:0021637) do a
  **deterministic value-match** against the evidence rows → a hard "grounded" signal that complements the
  judge (strongest for numbers; §9 in context-traceability-design).

## 6. Component 3 — Disposition mapping
Provisional rules (thresholds to tune on the demo set):
- `evidence == []` → **N/A** (L0).
- answer is a scoped refusal ("not loaded / cannot determine") **and** consistent with schema → **REFUSED (grounded)**.
- `deferred == true` (explicit handoff, e.g. no p-value asserted) with grounded inputs → **CAVEAT**.
- `score ≥ 0.95` → **RELEASE**; `0.6 ≤ score < 0.95` → **CAVEAT**; `< 0.6` → **WITHHOLD**.
- judge/evidence error → **"score unavailable"** (never a fake pass).

## 7. Per-layer behavior (expected, from measured demo metrics)
| Layer | Evidence | Live chip (expected) |
|---|---|---|
| **L3** | KB + graph + SQL + OLS | mostly **RELEASE**; Beat 5 **CAVEAT** (deferred stat); Beat 5b **REFUSED** |
| **L1** | lake SQL only | **RELEASE** where lake-answerable (Beat 1); elsewhere it declines/partial — chip is honest that it's *grounded but narrow* (faithful ≠ correct) |
| **L0** | none | **N/A** + list cited sources as-is (fair-to-L0); tooltip: "no retrieved context to ground against" |

> Note the measured subtlety: **L1 is faithful (1.0) but correct only 1/7** — so the chip must not be read as
> "quality." Pair the live groundedness chip with a **correctness caveat in the tooltip** ("grounding, not
> correctness") to avoid implying L1 ≈ L3.

## 8. UI / UX
- **Placement:** a chip at the **top of each answer column**, next to the layer label.
- **States:** `scoring…` (spinner) → resolved chip (colour by disposition: RELEASE green / CAVEAT amber /
  WITHHOLD red / REFUSED blue / N-A grey).
- **Expandable "why":** click → per-claim SUPPORTED/NOT_SUPPORTED/DEFERRED with the evidence snippet each maps
  to; for L0, the list of its (ungrounded) citations.
- **Toggle:** a UI switch "show groundedness" (default on) so the chip can be hidden for a clean capture.
- Implemented in `chat_ui.py` alongside `_handle_compare` (score each layer's `(answer, evidence)` after render).

## 9. Consistency with batch / online eval
- **Same rubric = same number.** Author the judge prompt once and reuse it both inline (UI) and as an
  **AgentCore custom evaluator** → the live chip and a future **online evaluation** report the *same*
  groundedness definition; native `Builtin.Faithfulness` remains the batch cross-check.
- The **evidence bundle** doubles as a reusable artifact for the deterministic value-match and for the P0.3
  evidence card.

## 10. Failure modes & safeguards
- Judge unavailable / throttled → **"score unavailable"**, not a pass.
- Empty/oversized evidence → N/A / truncate (bounded cost).
- Judge self-preference bias → consider an independent judge model (§12).
- Never let scoring block the **answer** render (fire-and-display; answer is never gated in v1).

## 11. Phasing
- **P1 — Evidence bundle:** modify `invoke()` to capture tool events + return `{answer, evidence, layer}`;
  UI parses (string still supported). *Unblocks everything; low risk, additive.*
- **P2 — Inline scorer:** judge call + rubric + disposition mapping; unit-test on the 7 demo answers (expect
  L3 RELEASE/CAVEAT/REFUSED, L1 RELEASE-or-narrow, L0 N/A).
- **P3 — UI chip:** chip + states + expandable "why" + toggle.
- **P4 (optional):** deterministic value-match add-on; register the rubric as an AgentCore custom evaluator
  for online-eval parity; **gate** (O1) — flip display→gate.

## 12. Open decisions (recommended defaults recorded; confirm before build)
1. **Judge model:** reuse Sonnet 4.5 (consistency) **or** an independent model (less self-preference bias)?
   → **Recommended default: independent judge model** (reduces self-preference bias; also the more defensible design).
2. **Disposition thresholds:** accept the provisional 0.95 / 0.6 cutoffs, or tune on the demo set first?
   → **Recommended default: ship provisional 0.95 / 0.6, then tune on the 7 demo answers** before wider use.
3. **Scorer location:** run the judge **in the UI process** (simplest) or a **separate scoring tool/endpoint**
   (reusable by online eval)?
   → **Recommended default: a small reusable scorer module** (importable by the UI *and* registrable as an
   AgentCore custom evaluator) — avoids forking the rubric.
4. **Score granularity in the chip:** show the numeric score, or **disposition only** (cleaner for the demo)?
   → **Recommended default: disposition-only chip, numeric score on hover/expand.**
5. **L0:** N/A + citations only (current decision) — confirm we're *not* doing the citation-support check now.
   → **Recommended default: N/A + list citations as-is** (defer citation-support check).
6. **v1 = display-only** (gating deferred to O1) — confirm.
   → **Recommended default: display-only v1**; gating is the P4/O1 flip once the live score is trusted.

_Status: documented plan only — no implementation started. P1 (evidence bundle) begins after these are confirmed._
