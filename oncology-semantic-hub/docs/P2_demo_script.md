# Demo Storyline — Perspective 2: Providing Context via the Semantic Hub (Video Walkthrough)

**Video:** SemanticHub_Research_cropped_lowres.mp4 (3:23)
**Interface:** Amazon Quick Desktop + Compare UI (Streamlit over deployed AgentCore Runtime agents)
**Thread:** EGFR in Glioblastoma (TCGA-GBM)

---

## Scene 1 — Quick Desktop: A Complex Research Question, End to End (0:00–1:30)

### The question

A neuro-oncology researcher types a single question into Amazon Quick Desktop — no tool hints, no method instructions:

> *"In glioblastoma, are EGFR and PTEN mutations mutually exclusive or do they tend to co-occur across the TCGA-GBM patient cohort — and is that association statistically significant? Are the two genes in the same signaling pathway, and what are the treatment implications?"*

### Why this is hard

This is not one question — it's five, spanning four data sources and a computation:
1. **Patient data** — how many GBM patients carry EGFR mutations? PTEN mutations? Both?
2. **Statistics** — are the two genes co-occurring more than chance? (requires a real Fisher's exact test, not an estimate)
3. **Knowledge graph** — are EGFR and PTEN in the same signaling pathway?
4. **Clinical evidence** — what does the published literature say about actionability (CIViC evidence levels, PMIDs)?
5. **Interpretation** — what does this mean for treatment strategy?

No single database answers this. A bare LLM would estimate the statistics from training memory (and get them wrong — see Scene 3). A flat data lake has the patient counts but no pathway knowledge, no CIViC evidence, and no statistical computation.

### How the research agent handles it

The `oncology-semantic-hub-analysis` skill routes the question to the right MCP servers — the agent composes the multi-tool path autonomously:

| Step | MCP Server / Tool | What it does |
|---|---|---|
| 1 | Athena · `query_patient_data` | Retrieves mutation frequencies from the TCGA-GBM lake: EGFR 82, PTEN 116, both 30, n=371 |
| 2 | Code Execution · Python | Runs a real Fisher's exact test on the 2×2 contingency table: **OR 1.36, p=0.30 — NOT significant** |
| 3 | Neptune · `query_knowledge_graph` | Traverses PI3K/AKT pathway membership, checks for direct EGFR–PTEN interaction, retrieves EGFR drug targets |
| 4 | Athena RODA · `query_variant_annotation` | Retrieves CIViC clinical evidence: EGFRvIII→TKIs, PTEN expression predicts TKI response (with PMIDs) |
| 5 | Model memory | Adds clinical interpretation: RTK/PI3K/AKT mechanism, PTEN-loss resistance rationale, combination-therapy strategy |

Each fact in the response is tagged to its source — `[Lake]`, `[Compute]`, `[Graph]`, `[RODA]`, `[Model knowledge]`.

### The output — and the groundedness score

When the full response appears, the video shows the **groundedness score** computed live from the provenance tags:

| Tag | Count | What it produced | Tool-backed? |
|---|---|---|---|
| `[Lake]` ×1 | Mutation frequencies (EGFR 82, PTEN 116, both 30) | ✅ tool |
| `[Compute]` ×2 | Fisher's exact test — OR 1.36, p=0.30 (not significant) | ✅ tool |
| `[Graph]` ×4 | Pathway memberships, interaction check, drug targets | ✅ tool |
| `[RODA/CIViC]` ×3 | Clinical evidence + PMIDs | ✅ tool |
| `[Model knowledge]` ×3 | Clinical interpretation + caveats | ✗ memory |

**Grounding rate = 0.77** (10 of 13 claims tool-backed)
**Provenance-faithfulness = 1.00** (0 fabricated — the agent never claims a tool source it didn't use)

**What to say:** *"One question. Five hub components. A real computed statistic — not an estimate. And a trust score you can read: 77% is tool-backed and verifiable, 23% is honest clinical interpretation labeled as model knowledge, and 0% is fabricated. This is what a trustworthy research answer looks like."*

## Scene 2 — Compare UI: Correctness + Reproducibility (1:50–2:30)

**Transition slide:** "Correctness — is it right?"

**What the viewer sees:**
The Compare UI (Streamlit) showing **L2 vs L3** side by side. L2 is the strong baseline (same data, flat); L3 is the semantic hub. Both use Claude Sonnet 4.5, temp=0, attempt-and-attribute.

**Q1 — Correctness (L2 vs L3):**
> *"In our TCGA-GBM cohort, how many distinct genes are mutated? And separately, how many genes are known to be associated with glioblastoma as a disease? Give both numbers."*

| Part | L2 | L3 |
|---|---|---|
| (a) genes mutated in cohort | **12,694** `[Lake]` ✓ | **12,694** `[Lake]` ✓ |
| (b) genes associated with glioblastoma (disease) | **166** `[PrimeKG-flat]` ← inflated | **144** `[Graph]` ✓ canonical |

**What to narrate:** *"Both nail part (a) — parity floor, L2 is no strawman. On part (b) they diverge: L3 resolves to the canonical MONDO node (MONDO:0018177) and gets 144 genes; L2 name-matches the flat table, sweeps subtypes — including 'astrocytoma (excluding glioblastoma)', a node definitionally NOT glioblastoma — and inflates to 166."*

**The KEY INTUITION (say this):** *"L2 has no ontology service, so it name-matches the flat table → sweeps subtypes → 166. The hub does canonical MONDO anchoring automatically and reproducibly; the flat approach requires the analyst to already know the exact canonical node name, and it's unstable across runs."*

**Honest caveat (pre-empt the skeptic):** *"The flat table also contains the correct 144 — under the exact node 'glioblastoma (disease)'. L2's error is name-matching without canonical resolution, not bad data. The hub makes this automatic and reproducible; the flat path is unstable."*

**Q2 — Reproducibility (L2 vs L3):**
> *"How many distinct genes are associated with the type of cancer studied in the TCGA-GBM cohort?"*

Run 3–5× in Compare mode.
- **L3:** stable at **144** every run (MONDO-anchored)
- **L2:** flips between **166** (disease-association reading) and **12,694** (mutated-in-cohort reading)

**What to narrate:** *"Same mechanism as Q1 — without canonical resolution, the LLM interprets the ambiguous question differently each run. The semantic hub eliminates this instability. One mechanism — name fan-out vs canonical MONDO anchor — drives BOTH the correctness gap (166 vs 144) and the reproducibility gap (L2 flips interpretation run-to-run)."*

## Scene 3 — Compare UI: Groundedness (2:50–3:23)

**What the viewer sees:**
Compare UI showing **L0 (bare LLM, no tools) vs L3 (full semantic hub)** side by side.

**Q3 — Groundedness (L0 vs L3):**
> *"Is the co-occurrence of EGFR and PTEN mutations in TCGA-GBM statistically significant? Give the p-value."*

| | L0 | L3 |
|---|---|---|
| Answer | `p<0.001`, "significant" `[Model knowledge]` | Retrieves real 2×2 table → p≈0.28, "not significant" `[Lake]` |
| Correct? | **Wrong** (true p = 0.28) | **Correct** |
| Grounded? | No — estimated from memory | Yes — real contingency table from TCGA-GBM |

**What to narrate:** *"L0 confidently fabricates a p-value from training data and reaches the WRONG scientific conclusion. L3 retrieves the actual patient data and reaches the correct conclusion. Both are honest about their sources — attempt-and-attribute is working — the issue is that memory doesn't have your cohort's data."*

*"This is the 80/20 trustworthiness problem. The LLM sounds authoritative — it cites a real study, it gives a plausible range. But the p-value is fabricated from memory and the conclusion is wrong. The semantic hub retrieves YOUR cohort's actual data and computes the real answer."*

## The Arc (what the video demonstrates)

| Scene | What it proves | Comparison | Hub layers exercised |
|---|---|---|---|
| 1 (Quick Desktop) | Full-hub orchestration + computed statistic | L3 standalone | Lake + Compute + Graph + RODA |
| 2 (Compare UI) | Correctness (144 vs 166) + reproducibility | L2 vs L3 | Graph + OLS vs flat PrimeKG |
| 3 (Compare UI) | Groundedness (real p-value vs fabricated) | L0 vs L3 | Lake + Compute vs parametric memory |

**Closing line:** *"Same model throughout. The infrastructure — not the model — is what makes the agent correct, reproducible, and trustworthy."*
