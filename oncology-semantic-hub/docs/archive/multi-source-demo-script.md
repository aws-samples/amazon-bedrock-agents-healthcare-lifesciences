# Multi-Data-Source Oncology Demo Script (Quick Desktop)

> **Purpose:** A recordable 5-question demo showing a bioinformatician doing **data analysis + literature review** in **Amazon Quick Desktop**, moving across four data tiers — **Athena → Neptune → public databases → literature** — in plain English, no SQL, no tool names spoken.
> **Scope:** Data analysis + literature, with **statistical inference delegated to Claude Code** (configured inside Quick). No statistics service of our own, no hypothesis generation, no new build. Everything below runs on existing skills + MCP servers + Claude Code as a compute delegate.
> **Status:** Skills + servers validated (repo validator: 0 errors). Numbers are verified against the live hub (June 2026); Q4–Q5 hit live public sources so treat their outputs as expected behavior, not fixed counts.

---

## Premise

A bioinformatician triages candidate drug targets in **breast cancer**, building evidence from patient data, the knowledge graph, public databases, and the published literature — each question adding one more data source.

- **Interface:** Amazon Quick Desktop
- **Persona:** Bioinformatician / computational biologist

---

## Why this demo — intent & thought process

> Read this before the demo. It explains *what we're proving and why*, not just the clicks. (Also intended as source material for slides.)

### The elevator pitch
**One natural-language agent in Quick Desktop that reasons across a scientist's private data, the world's public databases, and the published literature — in a single workflow.** It works because MCP turns every data source into a uniform tool, and skills route the scientist's *intent* to the right tool. No SQL, no Cypher, no naming servers, no per-source integration code, and the private data never leaves the customer's account.

### The problem we're addressing
Target identification and biomarker discovery are bottlenecked by **fragmented data**, not by a lack of intelligence. Biomedical knowledge is scattered across internal repositories, dozens of public databases, evolving ontologies, and millions of publications. Scientists spend the majority of their time wrangling and reconciling these sources by hand. No single tool spans **internal proprietary data + external public knowledge + literature** — so researchers stitch them together manually, and insights get lost in the seams.

### The core idea
Treat the **fusion** as the product. The differentiated value isn't any one database — it's answering a question that requires *all of them at once*, with the provenance of every fact preserved. That is something a general-purpose LLM (no access to your data or live sources) and a single-source tool (no breadth) each cannot do.

The enabling architecture is a clean separation of concerns:
- **Data** — the Oncology Semantic Hub (Neptune knowledge graph + Athena patient lake) and the customer's own internal lake/graph.
- **MCP servers** — uniform tool interfaces to every source (internal, public, literature).
- **Skills** — domain know-how that maps a scientist's plain-English intent to the right server.
- **The consumer** — Quick Desktop here; swappable (Claude Code, deployed agents) without changing the layers below.

### What we are — and aren't — showing
- ✅ **Showing:** data analysis + literature review across **four data tiers**, plus delegated **statistical inference** — running **today** on existing skills + MCP servers + the user's Claude Code, with **zero new build**.
- ⏸️ **Not showing (deliberately):** autonomous hypothesis generation, experimental validation, or a statistics service of our own. Those are a later lane. This demo proves the **data-integration foundation** honestly, with reproducible numbers — the credible base everything else builds on. *(Note: systems like Google's Co-Scientist inspired the "AI accelerates discovery" framing, but this demo is intentionally scoped to data analysis, not hypothesis generation.)*

### Why the storyboard escalates the way it does
Each question adds exactly **one** data source or capability, so the audience sees every tier light up, then the synthesis. The arc mirrors a real target-triage thought process:

| Question | Adds | The real-world question it mirrors |
|----------|------|-------------------------------------|
| Q1 | Internal/patient lake (Athena) | *What's altered in these patients?* — establish trust with real, verifiable data |
| Q2 | + Knowledge graph (Neptune) | *What does it connect to — is it druggable?* — the **1+1=3** cross-system moment |
| Q3 | + Terminology (OLS) | *Does it mean the same thing across sources?* — harmonization is the **glue** for internal↔external joins |
| Q4 | + Public evidence (Open Targets/Biomni) | *What does the wider world know?* — beyond the curated hub to live public data |
| Q5 | + Literature (PubMed) | *What's actually published?* — the full four-tier chain on one actionable target |
| Q6 | + Statistical inference (Claude Code) | *Is the pattern statistically real?* — rigorous compute, delegated locally |

### Key messages (slide-ready)
- **MCP is the universal connector** — add a server, the agent can use it; no bespoke integration per source.
- **Internal + external + literature in one answer**, every fact provenance-tagged (🔒 your data / 🌐 public / 📚 literature).
- **Data sovereignty** — internal sources are reached through the customer's own AWS account and identity; nothing is exfiltrated.
- **No-code for scientists** — plain English; intent is routed to the right tool automatically.
- **Composable & portable** — Quick is one consumer; the same skills + servers work elsewhere, and Claude Code adds local compute.
- **Zero new build** — existing skills + existing MCP servers + the customer's Claude Code.

### Who it's for
**Bioinformaticians / computational biologists** as the hands-on users; **R&D and portfolio leaders** as the economic buyers who care about the time saved reconciling data and the reduced risk from evidence-backed, provenance-tracked answers.

---

## Pre-record setup (once)

**Load these skills** (Settings → Skills → Add Skill):

| Skill | Role in demo |
|-------|--------------|
| `oncology-semantic-hub-analysis` | Athena (lake) + Neptune (graph) + OLS term resolution |
| `research-biomedical-databases` | Public DB evidence (UniProt protein class, GtoPdb inhibitors; Open Targets where available) |
| `biomarker-pathway-analysis` | Pathway / druggable-target context |
| `research-deep-literature-review` | Published + preprint literature |
| `terminology-ontology-lookup` | Ontology harmonization (used inline) |

**Connect these MCP servers** (Settings → Capabilities → Add MCP Server):

| Server | Transport | Notes |
|--------|-----------|-------|
| `amazon-neptune` | stdio (`uvx awslabs.amazon-neptune-mcp-server@latest`) | `NEPTUNE_ENDPOINT=neptune-graph://<your-graph-id>`, `AWS_REGION=us-west-2` |
| `aws-dataprocessing` | stdio (`uvx awslabs.aws-dataprocessing-mcp-server@latest --allow-sensitive-data-access`) | `AWS_REGION=us-west-2`; needs read on Athena DB `oncology_semantic_hub` |
| `biomni-research` | HTTP | Gateway URL + `Bearer` token (`get-token.sh`) |
| `ontology-lookup-service` | HTTP | Runtime URL + `Bearer` token (`get-token.sh`) |
| `pubmed` | HTTP (`https://pubmed.mcp.claude.com/mcp`) | no auth |

Optional literature breadth: `consensus`, `biorxiv` (HTTP, no auth).

**Compute delegate:** Claude Code is configured inside Quick Desktop. Quick delegates statistical / code-execution tasks (Fisher's exact, chi-square, two-proportion tests) to it — the demo's path to inferential statistics without a dedicated stats container. Quick retrieves the rows; Claude Code runs the computation locally on those rows.

**Before rolling:** pre-warm uvx (`uvx awslabs.amazon-neptune-mcp-server@latest --help`), kill stale procs (`pkill -f "uvx awslabs"`), and dry-run Q1–Q3 once to confirm numbers.

---

## The questions

### Q1 — Patient data lake *(1 source: Athena)*
**Type into Quick:**
> What are the top 5 most frequently mutated genes in TCGA breast cancer?

- **Hop 1 · Athena** — skill `oncology-semantic-hub-analysis` → `aws-dataprocessing`
- **Expected (verified):** TP53 (330), PIK3CA (328), TTN (182), CDH1 (128), GATA3 (125)
- **Talking point:** "Real patient-level data — 1.8M TCGA mutations in an Athena lake. In your environment this same question runs against your internal cohort."

### Q2 — Add the knowledge graph *(Athena → Neptune)*
**Type into Quick:**
> For those top 5 genes, how many drugs target each in the knowledge graph, and what's their ClinVar pathogenic variant count?

- **Hops 1→2 · Athena → Neptune** — `oncology-semantic-hub-analysis` → `aws-dataprocessing` + `amazon-neptune`
- **Expected (verified):** TP53 → 8 drugs / 1,661 · PIK3CA → 7 / 111 · TTN → 0 / 9,931 · CDH1 → 0 / 1,123 · GATA3 → 0 / 58
- **Talking point:** "The 1+1=3 moment — the lake says what's mutated, the graph says what's druggable. TTN: huge ClinVar count, zero drugs — a passenger mutation. The hub makes that obvious in one answer."

### Q3 — Terminology harmonization *(OLS → Neptune)*
**Type into Quick:**
> What drugs target genes associated with stomach cancer?

- **Hop · OLS → Neptune** — `oncology-semantic-hub-analysis` (Step 6) → `ontology-lookup-service` + `amazon-neptune`
- **Expected (verified):** "stomach cancer" returns 0 → OLS resolves to **gastric cancer (MONDO:0001056)** → **303 gene associations** → drugs returned
- **Talking point:** "Real data uses different vocabularies. OLS auto-harmonizes the term so internal and public data line up — this is what makes joining your data to public sources work."

### Q4 — Public evidence *(external DBs)*
**Type into Quick:**
> Compare the public druggability of TP53 and PIK3CA — their target tractability, and known small-molecule inhibitors/ligands.

- **Hop 3 · Public DBs** — `research-biomedical-databases` → `biomni-research` (`query_opentarget` for tractability, `query_gtopdb` for inhibitors/ligands)
- **Expected (live):** TP53 → limited tractability across modalities (few small-molecule routes) · PIK3CA → small-molecule tractable, known inhibitor **Alpelisib** (also a drug edge in Q2)
- **Talking point:** "Live public druggability evidence beyond the curated hub — Open Targets tractability plus the pharmacology DB pivot us to PIK3CA. TP53 is the famous undruggable target; PIK3CA is actionable."
> **Depends on the Biomni lambda `max_items` fix** (applied — see *Known issues & fixes*) so the 28-item tractability list comes through. Known inhibitors come from **GtoPdb**, not Open Targets `knownDrugs` (which still 400s).

### Q5 — Full chain + literature *(all 4 sources — finale)*
**Type into Quick:**
> For PIK3CA in breast cancer: mutation burden in the cohort, the drugs that target it in the knowledge graph, its public target tractability, and a summary of the latest published clinical evidence.

- **Hops 1→2→3→4 · Athena → Neptune → Biomni → PubMed** — `oncology-semantic-hub-analysis` + `research-deep-literature-review` → `aws-dataprocessing` + `amazon-neptune` + `biomni-research` + `pubmed`
- **Expected:** 328 BRCA patients (Athena) → 7 drugs incl. **Alpelisib** (Neptune) → small-molecule tractable (Open Targets) → published evidence on **alpelisib in PIK3CA-mutant HR+ breast cancer (e.g., SOLAR-1)** (PubMed)
- **Talking point:** "One plain-English question, four data tiers — prevalence, druggability, public tractability, clinical literature — synthesized with provenance on every fact. No single database has all four. Internal + external + literature in one workflow, zero new build."

### Q6 — Statistical inference via Claude Code *(compute delegation)*
**Type into Quick:**
> Test whether TP53 and PIK3CA mutations are mutually exclusive in TCGA breast cancer: pull the co-occurrence counts from the cohort and run a Fisher's exact test.

- **Hop · Athena → Claude Code** — `oncology-semantic-hub-analysis` → `aws-dataprocessing` builds the 2×2 contingency (patients in TCGA-BRCA with: both mutated / TP53 only / PIK3CA only / neither). Quick then **delegates the test to Claude Code**, which runs Fisher's exact (scipy) and returns the odds ratio + p-value.
- **Expected (live):** a 2×2 table from Athena, then an odds ratio + p-value computed in Claude Code, with a plain-English read (tendency to **mutual exclusivity** if OR < 1 and p < 0.05; **co-occurrence** if OR > 1).
- **Talking point:** "Quick orchestrates the data across sources and hands the rigorous statistics to Claude Code running in the same desktop — so we get inferential tests (Fisher's exact, chi-square, proportion tests) without standing up a stats service. The data provenance stays with the hub; the computation is auditable in Claude Code."

Alternative phrasings to keep handy:
- "Compare the PIK3CA mutation rate in TCGA-BRCA vs TCGA-LUAD and test if the difference is significant (two-proportion test)."
- "Is PIK3CA co-mutated with TP53 more than expected by chance in TCGA-BRCA (chi-square)?"

---

## Routing (intent → skill → server)

| Q | Intent keywords (the trigger) | Skill that fires | MCP server(s) |
|---|---|---|---|
| Q1 | "top mutated genes", "TCGA breast cancer" | oncology-semantic-hub-analysis | `aws-dataprocessing` |
| Q2 | "drugs target… knowledge graph", "ClinVar pathogenic variant count" | oncology-semantic-hub-analysis | `amazon-neptune` |
| Q3 | "drugs target genes associated with stomach cancer" (non-canonical name) | oncology-semantic-hub-analysis | `amazon-neptune` + `ontology-lookup-service` |
| Q4 | "public druggability… target tractability… known inhibitors/ligands" | research-biomedical-databases | `biomni-research` (`query_opentarget` tractability, `query_gtopdb` inhibitors) |
| Q5 | "mutation burden… drugs in the knowledge graph" → "public tractability" → "latest published clinical evidence" | oncology-semantic-hub-analysis → research-biomedical-databases → research-deep-literature-review | `aws-dataprocessing` + `amazon-neptune` → `biomni-research` → `pubmed` |
| Q6 | "mutually exclusive… Fisher's exact test… significance / p-value" | oncology-semantic-hub-analysis (data) + **Claude Code** (compute) | `aws-dataprocessing` → Claude Code |

Each question's wording contains the exact phrases in the target skill's trigger; each skill body names the server. Intent is clear on both sides.

---

## Recording notes

- **Provenance on screen:** the hub skill tags each fact (internal-Athena / Neptune / Biomni / PubMed) — point to these; it's the audit-trail story.
- **Q5 is the only multi-skill question.** The hub skill fires first; its hop-out plus the sharpened public/literature triggers carry the chain. If it stops after the graph step, nudge: "…and what's the latest published evidence?"
- **Q6 delegates compute to Claude Code.** Quick retrieves the contingency counts from Athena, then hands the numbers to Claude Code for the test. If Quick tries to estimate a p-value itself, nudge: "use Claude Code to run the Fisher's exact test on these counts." Confirm Claude Code echoes the test name + the 2×2 inputs before trusting the result.
- **Internal-data version:** for a customer cut, repoint `aws-dataprocessing` at their Athena cohort; Q1 and Q5 then show *their* numbers vs TCGA. The public TCGA-BRCA version is the reproducible one for recording.
- **Reproducibility:** Q1–Q3 numbers are verified-stable (June 2026); Q4–Q5 hit live public sources — re-run once before recording to confirm.
- **Timing/arc:** 1 source → 2 → +terminology → +public → all 4 → +statistical inference (Claude Code). ~8–10 min total.

---

## Known issues & fixes

**Open Targets via `query_opentarget` (Biomni lambda):**

1. **List truncation — FIXED (applied 2026-06-03, verified in env).** `_format_query_results` summarized any list longer than `max_items` (default **5**) into a `_summary`/`_sample` stub, truncating Open Targets' 28-item tractability field. Fix at the `query_opentarget` formatter call in `agents_catalog/28-Research-agent-biomni-gateway-tools/prerequisite/lambda-database/python/database.py`:
   ```python
   api_result["result"] = _format_query_results(api_result["result"], {"max_items": 50})
   ```
   Applied in the repo source and manually in the deployed Lambda. This is the **single source** — `mcp-servers/agentcore-gateway/biomni-research-tools/deploy.sh` packages the lambda from `agents_catalog/28`, so both deploy paths inherit the fix. Tractability now returns all entries.

2. **`knownDrugs` 400 — still open (avoided).** The GraphQL is LLM-generated from `schema_db/opentarget.json`; the model emits a field the current Open Targets v4 schema rejects. Not a clean static fix. **Known inhibitors are sourced from GtoPdb** (or the PrimeKG graph drug edge from Q2), not Open Targets `knownDrugs`.

---

## Feedback log

_(Fill in after trying it out: which questions routed correctly, where the agent needed a nudge, any number drift, any server/auth issues.)_

---

## Appendix — Backup questions (optional)

> Not part of the core 6-question arc. These extend coverage to the remaining TargetID data modalities from the AWS "three-week drug discovery agent" blog — **clinical trials** and **safety signals** — so prevalence → druggability → **trials → safety** → literature is complete. Both route through `research-biomedical-databases` → `biomni-research`. If routing is weak, name the source in the question, or author the dedicated stub skills (`clinical-trial-search`, `drug-safety-signal-detection`).

### Q7 — Clinical trials *(external: ClinicalTrials.gov)*
**Type into Quick:**
> What clinical trials target PIK3CA in breast cancer, and what are their phases and status?

- **Hop · Public DBs** — `research-biomedical-databases` → `biomni-research` (`query_clinicaltrials`)
- **Expected (live):** PIK3CA-inhibitor trials in breast cancer (e.g., alpelisib — SOLAR-1 phase 3, BYLieve phase 2), with phase and status; cited.
- **Talking point:** "Adds the clinical-trial modality — connecting the molecular target to where it's actually being tested in patients. Same agent, one more public source."

### Q8 — Safety signals *(external: OpenFDA)*
**Type into Quick:**
> What adverse-event signals are reported for alpelisib?

- **Hop · Public DBs** — `research-biomedical-databases` → `biomni-research` (`query_openfda`)
- **Expected (live):** common reported adverse events for alpelisib (e.g., hyperglycemia, rash, diarrhea) from OpenFDA/FAERS; cited.
- **Talking point:** "Closes the loop with safety — before committing to a target or drug, check the adverse-event signal. Completes the TargetID picture: prevalence → druggability → trials → safety → literature."

**Routing**

| Q | Intent keywords | Skill | MCP server |
|---|---|---|---|
| Q7 | "clinical trials… phases… status/outcomes" | research-biomedical-databases | `biomni-research` (`query_clinicaltrials`) |
| Q8 | "adverse-event signals… reported for \<drug\>" | research-biomedical-databases | `biomni-research` (`query_openfda`) |
