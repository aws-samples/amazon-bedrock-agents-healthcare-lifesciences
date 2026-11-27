# Hybrid Search (Vector + Graph + SQL) — Design (short)

**Status:** ✅ Implemented (v1) · 2026-07-16 · Owner: Hasan
**Goal:** add **hybrid search** to the hub — *semantic recall* over unstructured text (study descriptions
+ literature) → *graph + SQL precision* → an answer that **cites the evidence**. Delivered as one
capability (semantic literature/study search + citations) and added to the demo thread as a new beat.

## Status — shipped (v1)
Implemented as `agentcore/kb/` (build_corpus / knowledge_base / create_kb / hybrid_check + README) plus the
`knowledge_search` tool in `agentcore/semantic_hub_agent.py` and `bedrock:Retrieve` in `deploy.py`.
- **KB** `oncology-semantic-hub-kb` (S3 Vectors + Titan v2, 1024/cosine); id in SSM
  `/app/oncology-hub/knowledge_base/kb_id`. Ingested **93 docs** (33 TCGA + 60 PubMed), 0 failed.
- **L3 redeployed** with `knowledge_search` (recall → OLS → graph/SQL → cite). L1/L0 unchanged.
- **Verified live** (`agentcore/kb/hybrid_check.py`, all pass): study discovery surfaces TCGA-GBM/LGG;
  evidence cites real PMIDs (8/8 grounded in recall, **0 fabricated**); L1 declines the literature question.
- **Demo:** two-part **Q6** beat in [`demo-golden-thread.md`](demo-golden-thread.md).
- Rebuild/verify: `build_corpus.py` → `create_kb.py` → `deploy.py --layer L3` → `hybrid_check.py`.

## Why this matters (plain-language motivation)
A researcher asks questions in natural scientific language — *"which of our studies look at immune-checkpoint
resistance?"* or *"what's the published evidence for EGFR-therapy resistance in glioblastoma?"* Two things
break with a plain data lake (L1) or a bare LLM (L0):

- **Finding the right studies is a *meaning* problem, not a keyword problem — so we vectorize study
  descriptions.** Study/project descriptions are free text, and a scientist rarely knows the exact project
  ID or the exact wording. Keyword/SQL search misses synonyms ("checkpoint blockade" ≈ "anti-PD-1
  resistance"; "Alzheimer's" ≈ "neurodegeneration"). Embedding the descriptions enables **semantic recall**
  — surfacing the relevant cohorts/studies *by meaning*, even with zero keyword overlap. This is exactly the
  gap AbbVie flagged (*"we have not embedded study/project descriptions yet"*). → drives **R1, R2**.
- **The value is *your* indexed evidence — public citation is not the differentiator.** A bare LLM (L0) can
  already recall many public papers, and a public PubMed/web tool can fetch fresher ones — so "L3 cites
  PubMed" is weak. The real value is that the knowledge base indexes **your organization's own evidence**
  (internal study reports, protocols, prior/unpublished analyses) that L0 and public APIs **cannot see**,
  behind your **governance** (in-account/VPC, access-controlled, PHI-safe, reproducible), and **fuses it with
  the hub's graph + SQL** so evidence is tied to *your* cohort. Our public PubMed + TCGA-description corpus is
  a shippable **proxy** for that private corpus (abstracts + descriptions, not full text). → drives the
  internal-evidence value + hub fusion.
- **Answers stay checkable — every claim carries a real citation.** In a scientific/regulated setting an
  unsupported claim is unusable; L3 cites **only** sources actually retrieved (PMID / study id), taken from
  the retrieved document — never a fabricated reference — so a human can verify it. → drives **R4, R8**.

**In one line:** semantic recall over *your governed corpus* finds the right evidence, citations make it
checkable, and the graph+SQL layer ties it to your cohort. That combination is what we mean by *hybrid search*.

## Why (grounding)
The AbbVie ProServe engagement (`Abbvie_Recommendations_Doc.docx`, **Rec #7 — hybrid semantic-structured
search**) validated a two-phase pattern: **Phase 1 semantic vector recall** (embed study descriptions;
they used Titan + ChromaDB; captures synonyms/meaning — "Alzheimer's" → "AD/neurodegeneration") → **Phase
2 structured SQL precision** (LLM entity extraction → parameterized SQL). It measurably improved study
discovery. **Their gap = ours:** *"we have not embedded study/project descriptions yet."* AbbVie did
**Vector + SQL**; **we extend to Vector + Graph + SQL** — adding the knowledge-graph precision layer they
listed as *future* work (their terminology/ontology layer, Rec #9). That's our differentiator.

## Iteration decisions (2026-07-16, one-at-a-time)
1. **Purpose/scope:** a **reusable capability** (BYOD customers point it at their own study descriptions
   + literature) — **and** we add it to the demo thread as a new beat. Not demo-only.
2. **Corpus A — TCGA descriptions:** ingest **all 33 TCGA project descriptions** (GDC project summaries),
   one doc per project, tagged with metadata (`project_id`, disease, MONDO id) for citation + graph/SQL pivot.
3. **Corpus B — PubMed abstracts:** **start ~50 (scalable to ~200)**, query-driven around the demo thread
   (glioblastoma/EGFR + immune-checkpoint resistance) + light pan-oncology; metadata = PMID, title,
   journal, year (for citations + optional filtering).
4. **Sources:** **public-only for v1** (TCGA descriptions + PubMed). Internal/proprietary docs deferred —
   same mechanism (another S3 prefix), and for BYOD it's the customer swapping in their own docs.
5. **Hybrid mechanic:** **agent-driven** entity pivot, and the agent uses the **OLS MCP
   (`ontology_lookup`) at invocation time** to resolve entities extracted from recalled passages →
   authoritative CURIEs *before* querying Neptune/Athena. Flow = **Vector recall → OLS resolution →
   Graph + SQL precision → cited answer** (OLS is the bridge from unstructured recall to structured
   precision; reuses the tool L3 already has). No ingest-time entity tagging in v1.
6. **Retrieve-time filtering:** the `knowledge_search` tool exposes an **optional metadata filter**
   (`disease` / `source` [PubMed|TCGA] / `min_year`). Default = no filter (pure semantic recall); filter
   applied when the query implies it — precision at the vector layer, complementing OLS→graph/SQL.
7. **Citations & grounding:** tool returns **structured** citations — PubMed: `Title (Journal, Year) —
   PMID:xxxxx` (+link); TCGA: `TCGA-XXX project` (+GDC link). Strict rule: the agent **cites only sources
   returned by `knowledge_search`**; if recall finds nothing relevant it says so — never invents a PMID
   (the sharp contrast vs L0, which fabricates citations).
8. **Demo beat (Q6 — hybrid multi-hop; refined 2026-07-17):** one query that starts from **KB evidence**
   ("which genes are implicated in EGFR-therapy resistance in glioblastoma?") → resolves entities →
   **graph + SQL** ("how many TCGA-GBM patients carry them, and are they druggable?") → **cited** synthesis
   (verified: PTEN 116 pts/1 drug … the "PTEN paradox"). Honest framing: public-citation is *not* the
   differentiator (L0/PubMed can cite public papers); L3's value is indexing **your organization's own
   evidence** (proxied here by public abstracts) + **fusing it with your cohort's graph/SQL**. L1 can't start
   (no literature, no graph). *(Supersedes the earlier two-part study-discovery + evidence sketch.)*
9. **Evaluation:** a **tiny separate hybrid-search check** (~5–8: recall quality + citation validity /
   no-fabrication), kept apart from the golden 63. If it proves out, optionally promote to the golden 63;
   otherwise keep it demo-only.
10. **Freshness:** **one-time ingest for v1** — no scheduled re-sync. Re-ingest is a manual ops step
    (re-run the ingest script → `start_ingestion_job`) if/when the corpus changes.

## Requirements
- **R1 — Vectorize** TCGA project/study descriptions **+** curated PubMed abstracts.
- **R2 — Semantic recall:** meaning-based retrieval, e.g. *"immune-checkpoint-resistance studies"* recalls
  the right studies/abstracts even without keyword matches.
- **R3 — Precision filtering (OLS-bridged):** entities from recalled text are resolved to canonical
  CURIEs via the **OLS MCP at invocation time**, then used to query the **Neptune knowledge graph**
  (gene/drug/pathway relationships) **and Athena SQL** (patient-level facts).
- **R4 — Cite evidence:** answers carry real, retrievable citations (PubMed PMIDs / study IDs) — not the
  hallucinated references a bare LLM (L0) emits.
- **R5 — L1/L3 contrast:** L3 gains the capability; L1 (lake-only) and L0 (bare LLM) visibly cannot.
- **R6 — AWS-native, minimal new infra;** integrate into the **deployed L3 Strands agent** (AgentCore
  Runtime); additive only (**do not modify the Core graph**).
- **R7 — Metadata-filterable recall:** `knowledge_search` supports an optional filter (`disease` /
  `source` / `min_year`); default = pure semantic recall.
- **R8 — No fabricated citations:** cite only sources returned by recall; if nothing relevant, say so.
- **R9 — One-time ingest (v1):** build/sync the KB once; re-ingest is a manual ops step (no scheduled refresh).

## Feasibility note
Our Neptune Analytics graph `<your-graph-id>` has **`vectorSearchConfiguration: null`** — native vector
search must be set at *graph creation* and **cannot be added to an existing graph**. So the semantic
layer is a **separate store**, not the graph. (Recreating the graph with a vector dimension is possible
but heavy — out of scope.)

## Options for the semantic layer
| # | Option | Pros | Cons |
|---|---|---|---|
| **A ✅** | **Bedrock Managed Knowledge Base** | Managed RAG (ingest/embed/index/retrieve/rerank) — **no infra**; **S3 connector**; **agentic + semantic hybrid** retrieval; **citations** built in; **AgentCore Gateway → MCP** into our Strands L3 in a few lines; us-west-2; can BYO Bedrock embedding (1024-dim float32) | Less low-level control; per-retrieval + storage cost |
| B | Customer-managed / DIY (S3 Vectors, OpenSearch Serverless, or a lightweight local index + Titan v2) | Full control; cheap at tiny scale | We build/maintain embeddings, index, retrieval, citations |
| ✗ | Neptune Analytics native vector search | one-store hybrid | **Not available** on the existing graph (no vector config) |

**Recommendation: Option A (Bedrock Managed Knowledge Base)** for a fully-managed production path.
**Decision for THIS build (2026-07-16): a *simple* customer-managed KB following the proven
`agentcore_template/prerequisite/knowledge_base.py` pattern** — see below. It's the fastest,
self-contained path (no Gateway) and reuses code the team already has; we keep Managed KB as the
managed upgrade later.

## Decision (2026-07-16) — simple customer-managed KB (template pattern)
Reuse/adapt `agentcore_template/prerequisite/knowledge_base.py`:
- **Vector store:** **Amazon S3 Vectors** (serverless, cheap — *no OpenSearch to run*), 1024-dim, cosine.
- **Embeddings:** **Titan Text Embeddings v2** (`amazon.titan-embed-text-v2:0`).
- **Bedrock KB:** `type=VECTOR`, `S3_VECTORS` storage; **S3 data source** (our corpus bucket); FIXED_SIZE
  chunking (512 tokens / 20% overlap); ingestion job to sync.
- **KB-as-a-tool:** the L3 agent calls **`bedrock-agent-runtime:Retrieve`** with the `kb_id` → returns
  passages **+ source citations** (S3 URI / metadata). **No AgentCore Gateway** — self-contained.
- **Discovery:** store `kb_id` in **SSM** (e.g. `/app/oncology-hub/knowledge_base/kb_id`), read by the agent.
- **Governance:** helper creates the KB execution role + policies (FM invoke, S3 read, S3 Vectors) — additive.

## Build plan
1. **Corpus prep** → build the ingest files (see below) and upload to an S3 data bucket.
2. **Create KB** → adapt the template helper (S3 Vectors + Titan v2 + S3 data source), run ingestion, store `kb_id` in SSM.
3. **Wire the tool** → add `knowledge_search(query)` to `agentcore/semantic_hub_agent.py` (calls `Retrieve`, returns passages + citations); grant the L3 role `bedrock:Retrieve`/`bedrock-agent-runtime:Retrieve` + `ssm:GetParameter`.
4. **Redeploy L3** (L1/L0 unchanged — the contrast).
5. **Verify** hybrid beat live (recall → graph/SQL precision → citations); add to the demo doc.

## Implementation plan (v1 build) — reusable & checked-in
**Code layout** — a self-contained, re-runnable `agentcore/kb/` package (no throwaway scripts; generated
corpus/artifacts are gitignored):
| Path | Role |
|---|---|
| `agentcore/kb/knowledge_base.py` | Adapted from `agentcore_template/prerequisite/knowledge_base.py` — S3 Vectors + Titan v2 KB helper (create/upload/ingest/delete, idempotent) |
| `agentcore/kb/build_corpus.py` | Fetch **33 TCGA** project summaries (GDC API) + **~50 PubMed** abstracts (E-utilities) → local `corpus/` as `<doc>.txt` + `<doc>.txt.metadata.json` sidecars |
| `agentcore/kb/create_kb.py` | Driver: create/retrieve KB (dedicated corpus bucket), upload corpus, run ingestion, write `kb_id`/`ds_id` to SSM |
| `agentcore/kb/hybrid_check.py` | Re-runnable verification: recall quality + citation validity (no fabricated PMIDs) — the tiny hybrid-search check |
| `agentcore/kb/README.md` | How to build the corpus, create the KB, and verify |
| `agentcore/kb/corpus/` | Generated docs + metadata — **gitignored** |
| *(modify)* `agentcore/semantic_hub_agent.py` | Add `knowledge_search` tool (Retrieve + optional `disease`/`source`/`min_year` filter, structured citations); update `_L3_PROMPT` (recall→OLS→graph/SQL, cite-only-retrieved); resolve `kb_id` from SSM (env override `SEMHUB_KB_ID`) |
| *(modify)* `agentcore/deploy.py` | Add `bedrock:Retrieve` to the L3 execution-role policy |

**Resource names (idempotent):** dedicated corpus bucket
`oncology-semantic-hub-kb-corpus-<account-id>-us-west-2`; KB `oncology-semantic-hub-kb`; embedding
`amazon.titan-embed-text-v2:0` (1024-dim, cosine); SSM `/app/oncology-hub/knowledge_base/kb_id`
(+ `/ds_id`). Fixed helper `suffix` so re-runs retrieve existing resources rather than duplicate.

**Metadata sidecars** — `<doc>.txt.metadata.json` = `{"metadataAttributes": {…}}`:
TCGA → `source=TCGA, project_id, disease, mondo`; PubMed → `source=PubMed, pmid, title, journal, year`.

**Verification** — `hybrid_check.py` runs the two-part Q7 + ~5–8 recall/citation checks against deployed
L3; assert cited PMIDs appear in the retrieved set (no fabrication). Cleanup: remove any scratch files;
keep only the checked-in package.

## Recommended architecture (Vector → OLS → Graph + SQL)
```
User query ("immune-checkpoint-resistance studies relevant to our GBM cohort, cite evidence")
        │
   L3 agent (Strands, AgentCore Runtime) orchestrates:
    1. Vector RECALL   → knowledge_search tool → Bedrock KB on S3 Vectors
                         (TCGA descriptions + PubMed abstracts)  → passages + CITATIONS
    2. OLS RESOLUTION  → ontology_lookup (OLS MCP): entities from the recalled text → canonical CURIEs
    3. Graph PRECISION → Neptune KG (genes/drugs/pathways) on the resolved IDs
       SQL PRECISION   → Athena (patient-level counts)
        ▼
   composed, CITED answer
```
- **KB (S3 Vectors)** = recall (Vector) · **OLS** = entity-resolution bridge · **Neptune** = relationship
  precision (Graph) · **Athena** = patient precision (SQL). L3 orchestrates all four = **hybrid search**.

## Documents to ingest & vectorize (→ S3 → S3 Vectors KB)
1. **TCGA project/study descriptions (all 33 projects)** — assembled per `project_id` (disease name + short
   description). Enables "which studies are about X" by meaning.
2. **PubMed abstracts (start ~50, scalable to ~200; curated)** — scoped to the demo thread + the recall
   example: **glioblastoma / EGFR** and **immune-checkpoint resistance in oncology** (fetched via PubMed
   esearch/efetch; keep PMID + title + journal + year + abstract for citations).

## Integration into L3
- **Chosen:** a `knowledge_search` tool in `semantic_hub_agent.py` calling the KB **`Retrieve`** API with
  the `kb_id` (from SSM) → returns passages + citations. Self-contained; **no AgentCore Gateway**.
- **Redeploy L3** to add the tool; L1/L0 unchanged (that's the contrast).
- *(Managed KB + AgentCore Gateway MCP remains the later production alternative.)*

## Demo beat (new Q7 — two-part, on the GBM/EGFR thread)
Uses **both** corpora (see decision #8):
1. **Study discovery (TCGA descriptions):** *"I'm looking at EGFR-driven glioma / resistance — which of our
   TCGA cohorts are relevant?"* → semantic recall over the 33 descriptions surfaces **TCGA-GBM (and LGG)**.
2. **Evidence (PubMed):** *"…and what's the published evidence on EGFR-therapy resistance in glioblastoma?
   Cite it."* → OLS resolves the entities → graph/SQL ties to the cohort's genes/drugs → answer **cites real PMIDs**.

Contrast across layers:
- **L1 (lake):** can't — no literature, no such column.
- **L3 (hybrid):** recall (meaning/synonyms: "checkpoint blockade" ≈ "anti-PD-1 resistance") → OLS → graph/SQL → **cited** answer.
- **L0 (bare LLM):** fluent, but **fabricated / unverifiable** citations.

## Open decisions
**All v1 design decisions are settled — see "Iteration decisions" above (10 items).** Nothing is pending
for v1. Deferred to later (not v1): internal/proprietary docs, scheduled refresh, promoting the
hybrid-search check into the golden 63, and the Managed KB + AgentCore Gateway production path.

## Validation-framework integration plan (evidence / hybrid search)
Fold KB evidence search into **both eval paths** so hybrid answers are *measured*, not just spot-checked
(extends decision #9; `agentcore/kb/hybrid_check.py` is the seed). The two guarantees to score are
**no fabrication** (every cited id is a real corpus doc) and **grounded recall** (it cites what retrieval
surfaced), plus the graph/SQL correctness of the multi-hop.

**A. Question set (golden data).** Add a new category `hybrid_search` (~6–10 Q) as a **labeled sibling set
`evaluation/golden_hybrid.json`** (keep the headline 63 comparable). Schema mirrors `golden_dataset.json`:
- new `answer_type: "cited_evidence"` — `expectedTrajectory` includes `knowledge_search` (+ `ontology_lookup`
  / `query_knowledge_graph` / `query_patient_data` for multi-hop like Q6/Q7); ground truth = the set of
  **relevant corpus PMIDs/projects** (programmatic, from corpus metadata), not a fixed string.
- reuse `answer_type: "negative"` for off-corpus queries (must refuse; **zero** fabricated PMIDs).
- `metadata.data_snapshot` gains a **corpus snapshot id** (see D).

**B. Scorers (`evaluation/scoring.py`).** Add `score_citations(answer, corpus_ids, relevant_ids, retrieved_ids)`:
- **no-fabrication (hard gate):** `cited ⊆ corpus_ids` — any cited id not in the corpus ⇒ fail.
- **recall:** `|cited ∩ relevant| / |relevant|` (reuse `recall_entities`).
- **grounding:** `|cited ∩ retrieved| / |cited|` (cited what recall surfaced, not memory).
- reuse `detect_refusal` for the negative/off-corpus case; PMID/project extraction via the regexes in `hybrid_check.py`.

**C. Harness.** Promote `hybrid_check.py` into a scored evaluator `evaluation/eval_hybrid.py` (local) and wire
it into `agentcore/run_agentcore_eval.py` (deployed) so it runs beside the native
Correctness / Faithfulness / ToolSelection / Trajectory evaluators. Reuse `hybrid_check.corpus_ids()` +
`retrieve_pmids()` for ground truth. Report: no-fabrication rate, recall@k, grounding, tool-trajectory
(knowledge_search-first), and graph/SQL correctness.

**D. Ground truth & reproducibility.** Ground truth = corpus metadata at a **pinned corpus snapshot id**
(add to `evaluation/config.py` + `data-provenance.md`). Membership checks are deterministic; use the
LLM judge only for relevance nuance. Add a corpus `verify_ground_truth` check (expected PMIDs still ingested).

**E. Layer contrast & reporting.** Run the hybrid set on **L3 / L1 / L0** to quantify the contrast — e.g.
**L0 fabrication rate vs L3 = 0%**, L1 = "no literature." Add a hybrid section to `generate_report.py` /
`BENCHMARK_REPORT_V2.md`.

**F. Rollout (phased).** (1) Land `golden_hybrid.json` (~8 Q) + `score_citations` + `eval_hybrid.py`; baseline on L3.
(2) Add L1/L0 contrast + report section. (3) If stable, promote a few into the golden 63 (decision #9) — and
**re-baseline the headline 63 on Sonnet 4.5** at the same time (the 50.8%/98.4% numbers were on Sonnet 4).

## Out of scope (for now)
Recreating Neptune with a vector dimension; clinical trials / OpenFDA / structure connectors; production
KB governance (ACLs, refresh cadence). Provenance depth beyond citation is tracked separately.
