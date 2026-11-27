# Context Traceability & Confidence — Design

> **Status:** Draft for review · 2026-07-21 · Owner: Hasan
> **Goal:** let a scientist see, for any L3 answer, **what context the semantic hub gave the agent, from
> where, retrieved how, at what version — and how much to trust each piece.** Backlog **P0.3** (do before
> the Sonnet-4.5 re-baseline). Objective pillar: **trust**.

---

## 1. What we already do
- Every answer fact is tagged by **source system** — `[Graph]` / `[Lake: table]` / `[KB PMID]` / `[OLS:CURIE]`
  — plus a closing **"Sources & provenance"** section (edges traversed / table+filter / citations).
- Native AgentCore **Faithfulness** checks the answer is grounded in the agent's own tool outputs.
- `agentcore/kb/hybrid_check.py` proves cited PMIDs are **real corpus docs + grounded in retrieval** (no fabrication).
- Data is a **pinned snapshot** (`<your-graph-id>_2026-07`); `data-provenance.md` cites source versions.

**Gaps:** (a) no **record/version-level lineage** exposed to the user; (b) **no quantified confidence** of the context.

## 2. Signal inventory (probed live, 2026-07-21)
| Tier | Signals available | Notes / gap |
|---|---|---|
| **KB (hybrid)** | **similarity score** (0–1), citation (PMID/title/journal/year/source), **chunk-id** | score+citation returned by the tool today; **chunk-id is in the `Retrieve` response `location` but not yet surfaced** (§6.1) |
| **Graph nodes** | `source`, `cosmic_tier`, `clinvar_pathogenic_count`, `clinvar_top_significance` | node keys observed in probe; values populated on enriched genes only |
| **Graph edges** | **only `display_relation`** — no source/evidence | **edge provenance was dropped at load** — can't cite which of PrimeKG's 20 DBs asserted an edge (enhancement §6) |
| **OLS** | no numeric score, but **exact-vs-approximate derivable** (query vs returned `label`), hit/no-hit (`total_items`) | tool currently discards it (`ontology_lookup` returns only id+label) |
| **Lake (Athena)** | deterministic; **completeness/denominator**; pinned snapshot | row-count + snapshot are **derivable, not emitted by the tool today** (§6.3) |
| **Cross-run** | **reproducibility** (3-run agreement) | empirical confidence |

## 3. The design — a "Context Evidence Card"
For each answer, the hub emits a structured, per-item **evidence card** (machine-readable + rendered), so
the "Sources & provenance" section becomes *traceable and confidence-scored*:

```
context_item:
  claim:        "EGFR amplified in 253/570 GBM samples"
  source_tier:  Lake            # Graph | Lake | KB | OLS | External
  locator:      athena:source_cbioportal project_id='gbm_tcga' value=2   # table+filter / edge / PMID+chunk / CURIE
  retrieved_by: "SELECT count(distinct sample_id) …"                     # the exact query/tool call
  version:      snapshot <your-graph-id>_2026-07
  confidence:   High            # per-tier rule below
  confidence_why: "deterministic count; denominator known (570)"
```

## 4. Confidence model (per tier — use what we have; no fake single %)
- **KB:** similarity-score bands — **High ≥0.85 · Med 0.70–0.85 · Low <0.70**; boost if ≥2 corroborating passages; include recency (year).
- **Graph node facts:** **High** when backed by enrichment evidence (COSMIC Tier-1 / high ClinVar pathogenic count); **Med** otherwise; always name node `source`.
- **Graph relationship (edge) facts:** **Med by default** — mark *"curated PrimeKG relation; edge-level source not tracked"* (honest limitation) until edge provenance is loaded (§6).
- **OLS:** **High** = exact (query == returned label); **Low/flag** = approximate (parent/sibling term — the TCGA-LGG spotlight); **refuse** = no hit.
- **Lake:** **High** deterministic; **downgrade to Med** if the denominator is partial/unknown (state it, e.g. 371/617).
- **Reproducibility:** downgrade any item that varies across 3 runs.

**Overall grounding confidence = High/Med/Low + one-line rationale**, computed as the **min** across cited
items (weakest link), with **explicit low-confidence flags** surfaced (approximate OLS map, low KB score,
partial denominator). Never a single opaque number.

**Caveats (state these — the signals *bound* trust, they don't *guarantee* correctness):**
- KB similarity is **relevance, not correctness/faithfulness** — a high score means "on-topic", not "true".
- A "deterministic" lake result means **the query ran exactly as written** — *not* that the data is complete
  or that the SQL semantics matched intent. Always show the **denominator + snapshot + the query**.
- OLS **exact-string match can still be the wrong *sense*** — it raises confidence, not proof of the right concept.
- The overall band is a **conservative floor** (min across items), **not** a composite quality score — tier
  scales aren't commensurable; read it as "no cited item is weaker than X", and pair it with the flags.
This matches the hub's "grounded refusal / honest scope" ethos.

## 4a. Metric choice — AgentCore built-ins first (+ optional O1 gate)
For *measured* groundedness, **default to AgentCore's built-in evaluators** (per owner guidance):
- **`Builtin.Faithfulness` is the primary groundedness metric** — it scores the answer against the agent's
  own tool outputs, so it covers **all L3 tiers in one** (KB + graph + SQL + OLS), on the OTel trace, **no
  custom pipeline**. Pair with **Correctness** (vs ground truth), **Reproducibility** (3 runs), and
  **`Builtin.ToolSelectionAccuracy` / Trajectory**.
- The per-tier signals in §2/§4 (KB score, OLS exact-vs-approximate, denominator, node evidence) drive the
  **displayed confidence + disposition annotation** — not a separate scoring pipeline.
- **Disposition (RELEASE / CAVEAT / WITHHOLD)** derives from Faithfulness-score bands + the explicit flags.
- **Optional, O1-aligned add-ons (not required for the demo):** a **binding-integrity SHA-256 hash** of
  `(answer, context)` for audit; **Bedrock Guardrails contextual-grounding** as an **inline delivery-time
  gate** for the KB/text tier. Treat full O1 (interceptor + hash-chained provenance + tiers) as a governance
  layer we **align to, not rebuild**.

## 5. Surfacing
- **In the answer:** upgrade "Sources & provenance" → an **evidence card** table (claim · tier · locator ·
  version · confidence + why), with low-confidence items flagged ⚠️.
- **Machine-readable:** the same as JSON, for the eval harness and any UI panel.
- **UI:** a "Context & confidence" expander in `chat_ui.py` (pairs with the P0.2 narration-collapse).

## 6. Enablement (tool changes needed to *produce* the card)
The tools must surface the signals the card needs:
1. **`knowledge_search`** — already returns `score` + citation; **also emit chunk-id** as the locator. *(small)*
2. **`ontology_lookup`** — **surface exactness** (compare query vs top label → exact/approximate) + hit count,
   instead of discarding it. This directly encodes the Spotlight confidence. *(small)*
3. **`query_patient_data`** — return the raw **row count** + snapshot with results *(small)*. The scientific
   **denominator** (e.g. total cohort = 617) is question-dependent → obtain via a **second cohort-total query**
   and assemble in the **prompt (§6.5)**, not mechanically in the tool.
4. **`query_knowledge_graph`** — node `source`/`cosmic_tier`/`clinvar_*` are surfaced via a **cypher `RETURN`
   + prompt pattern** (instruct the agent to return and cite those keys), *not* a tool code change; edge facts
   labelled *"edge-source not tracked."*
5. **L3 prompt** — instruct building the evidence card + overall confidence (and the denominator query) from these fields.

**Enhancement (separate, additive — needs care, touches the Core graph load):** give PrimeKG **edges a
`source` property** via **in-place openCypher `SET` keyed by edge identity** — **not** a bulk re-import
(which can *duplicate* edges in Neptune Analytics). Add **edge-count invariant checks** (count by type
before/after must match). Do NOT rebuild the Core destructively. Follow-on, not required for v1 of the card.

## 7. Validation-run integration (feeds P0.1)
Add **context-traceability metrics** to the benchmark: % of answer facts with a **resolvable locator**;
count of **low-confidence flags**; KB **score distribution**; **OLS exact-vs-approximate** rate; and keep
**reproducibility**. These quantify "how trustworthy was the context," complementing native Faithfulness
(which only checks answer↔context consistency, not context *quality*).

## 8. Phased plan
1. **v1 (prompt + tool signals):** tool changes §6.1–6.5 → evidence card in answers + overall confidence. No graph reload. Verify on the demo beats (esp. Spotlight = low-confidence OLS catch; Q7 = deterministic lake High).
2. **v2 (metric):** add the §7 metrics to `eval_hybrid.py` / the compare harness; report in the re-baseline.
3. **v3 (edge provenance):** additive PrimeKG edge-`source` reload → relationship facts cite the asserting DB.

## 9. Open decision & validation
- **Implement v1 now (before P0.1)** per owner, or land the design only and implement with P0.1.
- **Independently validated (2026-07-21): APPROVE-WITH-CHANGES.** Reviewer confirmed the design is sound,
  honestly scoped, and grounded in the real hub (min-band + flags preferred over a single %). Fixes applied:
  §4 caveats (relevance≠correctness, deterministic≠complete, exact-string≠correct-sense; band = conservative
  floor); §2 corrected (chunk-id present in Retrieve response but not surfaced yet; lake counts derivable/not
  emitted); §6 re-scoped (denominator = prompt + 2nd query; node props via cypher/prompt pattern, not a tool
  code change); §6 enhancement specified as in-place `SET` + edge-count invariants (not bulk re-import).
