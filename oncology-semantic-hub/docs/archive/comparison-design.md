# Comparison Design — L0 < L1 < L3 as a "context-engine" ladder

> **Status:** Draft for review · 2026-07-20 · Owner: Hasan
> **Purpose:** Fix the layer-comparison so it (a) stays a clean **monotonic ladder** (L0 < L1 < L3), (b)
> does **not** hide obvious real-world capabilities (public/external tools), and (c) puts the **semantic
> hub** at the center as the thing that makes an agent trustworthy. Grounded in Anthropic's *"Paving the
> way for agents in biology"* (Jun 2026). Latest demo storyline: [`demo-golden-thread.md`](demo-golden-thread.md).

> ⚠️ **Numbers caveat:** the published **50.8% / 98.4%** were measured on **Claude Sonnet 4** with the
> **old L1 = lake-only** definition. This design **redefines L1** (adds raw external tools) and the agents
> now run **Sonnet 4.5**. Do **not** quote the old numbers under this framing — they must be **re-baselined**
> (see §6) first. `demo-golden-thread.md` also still describes the old L1 (lake-only) and needs syncing.

---

## 1. The problem with the old framing
The published comparison was **L0 (bare LLM) < L1 (raw Athena lake) < L3 (full hub)** — a nice monotonic
ladder, but on **internal data only**. Feedback: a real scientist's agent also has **skills + external
public tools** (Biomni gateway: Open Targets, GtoPdb, ClinicalTrials, PDB/AlphaFold, PubMed, …). Showing
the hub in isolation is misleading; but bolting on an "L4 = external" rung makes the ladder confusing and
mixes two different axes (internal-vs-external data scope ≠ increasing capability).

## 2. The reframe — vary the *layer*, not the *data scope* (Anthropic-aligned)
Anthropic's VirBench study found the bottleneck for biology agents is **not reasoning — it's the absence of
a deterministic retrieval/semantic layer.** Agents left to navigate raw infrastructure produce
**plausible-but-wrong, non-reproducible** answers (identical prompt → 266 vs 106 vs 15 vs 5 records). Adding
a **deterministic layer** ("context engine", e.g. *gget virus*) pushed accuracy to ~90–99.7%, **collapsed
run-to-run variability**, and made **model choice matter far less**. Anthropic names Biomni as one of the
*harnesses that connect agents to data* — i.e. **a tool tier, not a competitor to the semantic layer.**

**The semantic hub IS a context engine.** So the comparison axis is: *is there a deterministic + semantic
layer between the agent and the data?* Hold the **tools constant** (internal lake **and** external Biomni
**and** literature available throughout) and **vary only the layer**:

| Path | What the agent has | Predicted behavior (Anthropic pattern) |
|---|---|---|
| **L0 — model only** | no data/tools (parametric knowledge) | fluent, ungrounded, cannot see *your* data — hallucination floor |
| **L1 — model + raw tools** | the data lake **and** external public tools (Biomni), navigated **raw**: writes its own SQL, guesses identifiers, calls public APIs directly | reaches everything, but **plausible-but-wrong, non-reproducible, model-dependent** |
| **L3 — model + semantic hub (context engine)** | the **same** lake + **same** external tools, now behind the hub's deterministic + semantic layer, which also **orchestrates** the external tools | **high accuracy, reproducible, model-independent**, provenance-tagged |

Result: monotonic **L0 < L1 < L3**, no "L4", external tools present at **both** L1 (raw) and L3
(orchestrated). The differentiator is the **layer**.

**Two distinct things the L3 layer contributes (keep them separate — don't overclaim "pure determinism"):**
- **(a) Net-new curated knowledge** — the **PrimeKG relationship graph** (gene↔drug, gene↔pathway, disease↔gene…)
  that L1 *simply does not have*. This is new capability, not a reliability wrapper. Beats Q3/Q4 rest on this.
- **(b) A context-engine reliability layer** — deterministic retrieval + OLS entity resolution + provenance +
  reproducibility, which also makes the **same external tools** reliable. Beats Spotlight/Q6/Q7 and the
  external-orchestration rest on this. *This is the direct Anthropic/gget-virus analogue.*
> Honesty note: gget virus added **only** determinism (no new data). Our hub adds **both** (a) and (b). We
> state both so the story isn't mis-sold as pure determinism.

## 3. What is the L3 layer? (the "context engine", precisely)
L3 = the semantic hub sitting between the agent and the data, composed of:
1. **PrimeKG knowledge graph (Neptune) — curated node-entity *relationships*.** Genes↔drugs, genes↔pathways,
   disease↔genes, pathway↔genes, etc. across 129K entities / ~4M edges from 20 curated DBs. *This is what
   lets the agent answer relationship and multi-hop questions at all* (druggability, pathway partners,
   network medicine) — a raw lake has rows, not relationships. **First-class differentiator.**
2. **Deterministic retrieval** — curated Athena schema + openCypher, so queries are correct and repeatable
   (the "gget virus" role): counts, joins, partition-aware SQL that the agent would otherwise get wrong.
3. **OLS entity resolution** — canonical identifiers (MONDO/HGNC/…) that harmonize *within* the hub **and
   make external tool calls correct** (e.g. "stomach cancer" → gastric cancer `MONDO:0001056`;
   `gbm_tcga` = `TCGA-GBM`).
4. **Hybrid-search knowledge base** (Bedrock KB on S3 Vectors + Titan v2) — semantic recall over study
   descriptions + curated literature; the internal-evidence tier, cited, no fabrication.
5. **Provenance** — every fact tagged by source (`[Graph]`/`[Lake]`/`[KB PMID]`/`[OLS]`), auditable, reproducible.
6. **External orchestration** — the hub uses its resolved identifiers to call Biomni's public tools
   *reliably*, and joins the results to *your* cohort.

L1 has none of 1–6: it can reach the same lake and the same public APIs, but must reconstruct schema,
relationships, and identifiers on the fly — the Anthropic failure mode.

**Pre-empting "the hub is just one more tool/MCP server":** unlike a raw tool, the hub is **curated at
build time** (relationships + ontology map), **reproducible** (pinned snapshot, deterministic queries), and
**provenance-tagged**. The **Spotlight** beat is the proof — the hub doesn't just *serve* data, it *corrects*
a wrong mapping (TCGA-LGG → a dental term → fixed to `MONDO:0021637`) that a raw tool would have passed
through silently. That is trust a bare tool cannot provide.

## 4. The storyline (mapped to `demo-golden-thread.md`)
One thread — **EGFR in glioblastoma** — escalating from lake-native facts to graph/ontology/hybrid, with
external tools entering where breadth is needed. Each beat is annotated for **where the layer matters**.

| Beat | Question (science-natural) | What it exercises | L1 (raw lake + raw public tools) | L3 (context engine) |
|---|---|---|---|---|
| **Q1** | Top-5 mutated genes in TCGA-GBM | lake-native count | ✅ parity | ✅ parity |
| **Q2** | How many carry EGFR mutations (=82) | lake-native count | ✅ parity | ✅ parity |
| **Q3** | Which drugs target EGFR — how many, what source | **KG relationships** vs raw public lookup | ~ partial: can scrape drugs from raw Open Targets/GtoPdb, but **ungrounded, no count/provenance, variable** | ✅ curated count + source (PrimeKG), cohort-linked, provenance |
| **Q4** | EGFR pathway partners, co-mutated + druggable | **KG multi-hop** (climax) | ✗ **can't** — no relationship graph to traverse | ✅ gene→pathway→genes→drugs |
| **Q5** | EGFR protein abundance? | grounding/scoping | ✅ refuse | ✅ refuse (scopes to loaded data: mRNA ≠ protein) |
| **Q6** | Resistance evidence → tie to cohort, cite | **hybrid KB + OLS + graph/SQL** vs raw PubMed | ~ partial: raw PubMed returns papers, but **can't tie to your cohort, no entity resolution, citations unverified** | ✅ cited PMIDs + cohort tie-in, no fabrication |
| **Q7** | Which amplified genes are druggable | **cBioPortal CNA + KG**, id reconciliation | ✗ **can't** reliably — no graph for druggability; fumbles `gbm_tcga`≠`TCGA-GBM` | ✅ CNA + druggability, provenance |
| **Spotlight** | Does the graph map TCGA-LGG correctly | **OLS entity resolution** | ✗ **can't** — no ontology layer | ✅ fixes → `MONDO:0021637` |

**Read the L1 column two ways** (matches §2's two contributions): **"✗ can't"** = net-new capability L1
lacks entirely (Q4 graph multi-hop, Q7 CNA+graph, Spotlight OLS). **"~ partial"** = L1 can *reach*
something with raw tools but the result is **ungrounded to your cohort, unresolved, un-provenanced, and
non-reproducible** (Q3, Q6) — the determinism/trust contrast, not a capability gap. **Q1–Q2 = the honest
floor** (lake-native → parity). Avoid claiming "L1 can't" where raw public tools actually return *something*.

### 4a. The external-tools extension (new — makes it holistic, keeps the hub central)
Add a **cross-scope** beat (or extend Q3/Q7) that *requires* public tools, so the external tier is exercised
and the **determinism contrast** is visible on the *same* question:
> *"For our GBM cohort's amplified targets, what's the public target tractability, active trials, and safety —
> and how does that compare to our internal evidence?"*
- **L1 (raw):** calls Biomni with its own id guesses → wrong/ambiguous lookups (e.g. `TCGA-GBM` returns 0 in
  a source keyed by `gbm_tcga`; "stomach cancer" → 0) → **plausible-but-wrong, varies run-to-run.**
- **L3:** hub resolves the cohort's targets to canonical ids (OLS) → calls Biomni (`query_opentarget`,
  `query_clinicaltrials`, `query_openfda`, `query_pubmed`) **correctly** → joins to the cohort → provenance-tagged.
This is the **Q3 OLS-harmonization moment as the determinism story** — the exact analogue of the gget-virus chart.
> **Pick ambiguous/non-canonical identifiers for this beat** — e.g. cBioPortal `gbm_tcga` (≠ GDC `TCGA-GBM`),
> "stomach cancer" (→ gastric cancer `MONDO:0001056`), or non-coding gene symbols. **Famous unambiguous
> targets like EGFR will NOT surface L1's id-fragility** (raw tools resolve them fine), so the contrast
> would look weak. The failure mode only appears where identifiers are messy — which is most of real data.

## 5. Bonus headline — "buy the layer, not the biggest model"
Anthropic's second result (the layer makes model choice matter less) is a compelling enterprise message and
directly testable: run L1 vs L3 across **2–3 models**; expect L1's spread wide/unreliable, **L3 converging
high + reproducible**. **⚠️ Hypothesis for us — NOT yet measured.** Do not state it as our result until the
multi-model ablation is run (backlog "model independence + ablations", slide 12 "Next").

## 6. Benchmark implications (if adopted)
1. **Redefine L1** = lake **+ raw external tools** (not lake-only) — more honest, more compelling.
2. **Re-run the 63-Q benchmark** under the new L1 (fold into the **Sonnet 4.5 re-baseline**, backlog P0.1);
   the current 50.8%/98.4% were on Sonnet 4 (slide 18).
3. **Add cross-scope questions** (backlog P2.3) that need internal+external, so raw-L1's identifier/tooling
   unreliability is measured against L3's orchestration.
4. Optional **multi-model ablation** for the model-independence headline.
5. Keep the metrics: correctness + **reproducibility (3 runs)** — reproducibility is the Anthropic point.

## 7. What stays the same
- The EGFR-in-GBM thread and beats (`demo-golden-thread.md`) — unchanged science storyline; only the L1
  definition and the framing (determinism/context-engine) change, plus the external-tools cross-scope beat.
- L0 remains the bare-LLM floor.
- Provenance tiering already implemented in L3 answers.

## 8. Open decision — implement now or later
- **Now:** redefine L1 (add raw external tools), re-run benchmark on Sonnet 4.5 with cross-scope questions,
  add the external-tools beat to the demo, (optional) multi-model ablation.
- **Later:** keep the current internal-only benchmark as-is for now; adopt the framing in slides/docs first,
  implement the L1-redefinition + cross-scope questions in the next benchmark pass.
- **Recommendation:** adopt the **framing now** (this doc + slides), and implement the **L1-redefinition +
  re-baseline** together with P0.1 (Sonnet 4.5) so we only re-run the benchmark once.

## 9. Validation (independent agent — done 2026-07-20)
An independent reviewer agent validated this storyline against the demo beats + the Anthropic framing.
**Verdict: APPROVE-WITH-CHANGES.** Hub-centrality, monotonicity, and Q4/Q7/Spotlight attribution passed.
Changes it flagged — **now applied above**:
1. Resolved the L1 contradiction: Q3/Q6 are reframed as **determinism/grounding/provenance** contrasts
   ("~ partial", not "L1 can't"); "L1 can't" reserved for Q4/Q7/Spotlight (§4 table + read-guide).
2. Separated the layer's **two contributions** — net-new PrimeKG knowledge vs context-engine determinism —
   so "same tools" doesn't hide the graph, and we don't over-sell "pure determinism" (§2).
3. Added the **numbers-caveat / re-baseline banner** and the note that `demo-golden-thread.md` still uses the
   old L1 and must be synced (top banner + §6/§8).
4. Required **ambiguous identifiers** (not EGFR) for the external-tools beat (§4a).
5. Caveated the **model-independence** headline as an unmeasured hypothesis (§5).
6. Added the **"hub is just one more tool" pre-emption** with Spotlight as proof (§3).

Remaining before implementation: sync `demo-golden-thread.md` to the new L1 definition + framing, then
re-baseline (§6/§8).
