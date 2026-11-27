# Session Context — v3 RODA Data Expansion (handoff)

> **Purpose:** durable state so work continues across context resets. Living doc; update as things change.
> **Last updated:** 2026-07-31. **Status:** v3 SHIPPED & validated; demo being tested on Quick Desktop.

## Objective
Enrich the Oncology Semantic Hub with AWS Registry of Open Data (RODA) oncology datasets as **additive lake
tables + a core-untouching graph extension**, expose via an **L3-only tool**, and ship a **Quick, L3-only demo**
that keeps the v2 EGFR-in-glioblastoma storyline as its spine with RODA woven in subtly (~3 touchpoints).
Plus reusable onboarding tooling + a "10+ datasets" scale plan + skills.

## Key coordinates
- AWS **<account-id>**, **us-west-2**; venv `./.venv/bin/python` (run from `oncology_semantic_hub/`).
- L3 runtime **`oncology_semantic_hub_l3_cff54df6-2c7IrBBFyT`** (`agentcore/agent_config.json`); L1 `..._l1_98bf0441`.
- Neptune Analytics graph **`<your-graph-id>`** (core PrimeKG + `ta_oncology` extension in the same graph).
- Glue DBs: **`oncology_semantic_hub`** (core lake) + **`oncology_semantic_hub_roda`** (RODA). Athena WG `primary`,
  output `s3://oncology-semantic-hub-data-<account-id>-us-west-2/athena-results/`. RODA data under `s3://.../roda/`.
- My shell identity = IAM user `hpoonawa-biomarkers` (has ALL on the `_roda` DB — it created it).

## What shipped (v3)
- **RODA MCP** live in `~/.kiro/settings/mcp.json` (`awslabs.roda-mcp-server`; backup `.bak-20260730-232405`).
- **Lake tables** in `oncology_semantic_hub_roda`: `civic_evidence` (4,598 rows; somatic actionability; evidence
  A194/B1533/C1591/D1248/E32; PMIDs) + `genoxus_clinvar` (217,333 rows; chr7 ClinVar; flattened; mixes
  germline+somatic classifications — split pending).
- **`ta_oncology` graph extension**: `CancerBiomarker` nodes + `PREDICTS_RESPONSE_TO`/`BIOMARKER_OF_GENE` edges,
  bridged to core `gene_protein{name}`/`drug{name}` by shared IDs, `partition='ta_oncology'`. Loaded for the GBM
  co-mutation set (**365 biomarkers / 15 genes / 525 edges**: EGFR,PTEN,TP53,PIK3CA,PIK3R1,PDGFRA,NF1,RB1,MET,
  IDH1,ATRX,CDKN2A,MDM2,MDM4,CDK4,KIT,SRC). **Core untouched (27,671); rollback verified (drop→0).**
- **L3 tool `query_variant_annotation`** (Athena over `_roda` + cross-db join to `oncology_semantic_hub.tcga_mutations`)
  + updated `get_hub_schema` + shared `_run_athena`. Redeployed → cff54df6 (READY). `deploy.py` LF grant covers both DBs.
- **Reusable scripts** `scripts/roda/`: `classify_dataset.py`, `load_genoxus.py`, `load_civic.py`,
  `graph_extension.py` (`--gene` comma-list or ALL; `--apply`/`--drop`) + `README.md`.
- **Docs (living):** `roda-data-expansion-v3-plan.md`, `roda-v3-spec.md`, `roda-master-plan-scale.md`,
  `roda-customer-onboarding-summary.md`; demo `demo-golden-thread-v3-quick.md`. Indexed in `docs/README.md`.
- **Skills:** NEW `skills/oncology-hub-variant-actionability/` (SKILL.md + references/queries.md); EXTENDED
  `skills/oncology-semantic-hub-analysis/` (RODA section + **data-source routing map** + **statistical-rigor guardrail**).

## Join contract (Genoxus ↔ TCGA)
`replace(tcga.chromosome,'chr','')=genoxus.chrom AND start_position=pos AND alleles` (both GRCh38; SNVs exact,
indels may differ by VCF/MAF representation).

## Correctness rules
- **Germline ≠ somatic:** don't present germline ClinVar as somatic driver status. Somatic actionability = CIViC
  (cite PMID). CIViC is predominantly somatic — check `variant_origin` (a few Germline/Predisposing rows).
- **Faithfulness** = AgentCore's non-contradiction metric (5-level ordinal); "faithful ≠ correct" (L1 Faithful
  ~1.0 but ~1/7 correct). No separate "Groundedness" evaluator exists.
- **Statistical rigor:** never assert/estimate an uncomputed p-value; ground the contingency + hand off to a
  deterministic step. (Now in the agent prompt AND the hub skill so Quick matches L3.)

## Demo test state
- **6 questions** run against L3 cff54df6; **all pass**; full baseline saved to **`agentcore/v3_demo_l3_answers.json`**.
  Verified substance: Q1 EGFR=82/top-5; Q2 drug classes + CIViC + PMIDs; Q3 explicit germline/somatic; Q4
  co-mutation (PTEN 30/TP53 19/PIK3CA 9/PIK3R1 9/RB1 8/ATRX) + actionable biomarkers; Q5 grounds + hands off (no
  p-value); Q6 → MONDO:0021637.
- **User will run the demo on Quick Desktop** using **MCP servers + skills directly** (not the L3 agent) to compare.
  - Skills to load (from the **Kiro clone**, not the other clone): `oncology-semantic-hub-analysis` +
    `oncology-hub-variant-actionability`. MCP servers: `amazon-neptune` (<your-graph-id>), `aws-dataprocessing`
    (both DBs, `--allow-sensitive-data-access`), `ontology-lookup-service`.
  - **LF access:** `hpoonawa-biomarkers` already has access; only an issue if Quick uses a *different* identity
    (then grant DESCRIBE/SELECT on `oncology_semantic_hub_roda`).
  - **Known divergence:** L3's Q2 also used the **Bedrock KB** (`knowledge_search`) for literature richness;
    Quick has no KB server yet → Q2 will be CIViC-centric until we add it.

## Architecture finding (documented 2026-07-31)
Legacy build stamped **ClinVar** (`clinvar_pathogenic_count`, `clinvar_top_significance`) + **COSMIC CGC**
(`cosmic_tier`, 74 Tier-1 flags) as **properties on core `gene_protein` nodes** (`scripts/11_add_clinvar.py` /
`14_add_cosmic.py`, ~Jul 15). Per the SDL spec these are **extension-scoped** (COSMIC → Oncology; germline ClinVar
→ Rare Disease `urn:rare:variants`), not core (core = UniProt/Ensembl/HGNC/GO/HPO/OBO). Documented as a known
deviation in `skills/oncology-semantic-hub-analysis/references/caveats.md` + master-plan §4b; migration = backlog
**P3.6**. `cosmic_tier` = CGC Tier-1 flags only, not the full COSMIC somatic catalog. (Verified live: EGFR
clinvar=346, sig="Likely pathogenic; drug response", cosmic_tier=1; 6,286 genes w/ ClinVar; 74 Tier-1.)

## L2 layer — apples-to-apples baseline (built 2026-07-31)
**Why:** isolate the *semantic layer* (graph + ontology). L2 = **all the same raw facts as L3 + Bedrock KB
literature, but flat (Athena) with NO graph traversal and NO OLS.** Same answering posture as L3 (provenance,
citation discipline, statistical-rigor hand-off) — the *only* difference is data access. So **L2→L3 isolates
the graph+ontology value**, holding data (incl. literature) constant.
- **Runtime:** `oncology_semantic_hub_l2_54a8c7c7-QCYGkwBTmL` (READY) · `agentcore/agent_config_l2.json` · `SEMHUB_LAYER=L2`.
- **Tools:** `knowledge_search` (KB), `query_patient_data` (TCGA/cBioPortal lake), `query_variant_annotation`
  (RODA civic/genoxus flat), `query_primekg` (flat PrimeKG). **No** `query_knowledge_graph` (Neptune), **no** `ontology_lookup` (OLS).
- **Data prep:** `scripts/build_l2_raw_lake.py` (dry-run/`--apply`, idempotent, self-fixes the URL-encoded
  `off-label use` partition) → new Glue DB **`oncology_semantic_hub_raw`**: `primekg_edges` (8,100,498 rows,
  partitioned by `relation`×30) + `primekg_nodes` (129,375). Parity check: EGFR→**31** distinct drugs = L3 graph.
- **UI:** Compare app (localhost:8501) now has an **L2 toggle** ("all raw data + KB, apples-to-apples lens"); L2 config in `chat_ui.py`.
- **Demo baseline (6 Qs) → `agentcore/v3_demo_l2_answers.json`.** L2 vs L3:
  - **Parity:** Q1 (lake, EGFR=82), Q3 (ClinVar cross-db join), Q5 (**guardrail held** — grounded contingency + honest hand-off, no p-value).
  - **Via CIViC+KB (not graph):** Q2/Q4 actionability answered from `civic_evidence` + literature PMIDs.
  - **L2 < L3 (the clean semantic-layer win):** **Q6** — L2 *suspects* the TCGA-LGG misalignment from world
    knowledge ("ontologies conflate glioma grades") but **cannot authoritatively resolve `MONDO:0021637`**
    (no OLS/graph); L3 does.
  - **Brittleness signal:** L2 repeatedly fumbled the flat-PrimeKG UNION self-join and fell back to CIViC/lake
    (the raw-access reliability cost) → `query_primekg` is under-used. **Follow-up:** strengthen `query_primekg`
    robustness (docstring/examples) + run the **63-Q L2-vs-L3 eval** for quantitative correctness/repro/faithfulness.
- **Expectation (calibration):** correctness + reproducibility should separate L2<L3 (ontology/graph questions);
  **faithfulness likely stays ~flat** for both (grounded-but-wrong is still faithful — as L1 showed).

### 63-Q L2-vs-L3 eval — DONE (clean, 2026-08-01) → `agentcore/l2_l3_compare_results.json`
**L2 92.1% correctness / 81.0% reproducibility · L3 98.4% / 95.2%** (L3 matches its v2 baseline → harness sound).
Per-category L2→L3: quantitative 100→100, drug_gene 100→100, cross_system 100→100, negatives 100→100,
**cross_system_misalignment 75→87, ontology_resolution 70→100.**
- **CRITICAL ARTIFACT found + fixed:** the L2 role had `glue:GetPartitions` (list) but not **`glue:GetPartition`/
  `BatchGetPartition`**, so `query_primekg` was permission-blocked on the partitioned `primekg_edges` → the first
  run showed a *false* drug_gene=0% / L2=63.5%. Fixed on the live role (`glue_partition_fix` inline policy) **and**
  in `deploy.py` `_ACTIONS`. Re-verified (AKT1→10 drugs) + clean full re-run.
- **Honest read:** once L2 can read the data, the **correctness gap is small (+6.3pp), concentrated in
  ontology_resolution** (OLS-only); **reproducibility is the broader gap (−14pp)** — the determinism signal.
  4/6 categories are now parity → the 63-Q set is **too easy to discriminate on correctness**.
- **NEXT (agreed direction):** rebalance the question set — add genuine **multi-hop** (3–4 join) + **ontology/
  reconciliation** questions (where flat self-joins are brittle & OLS is needed); keep a few 1-hop/quant as parity
  controls. Then re-run L2-vs-L3. Faithfulness (native harness) still expected ~flat L2≈L3.

## Next / open
1. User tests v3 on Quick Desktop → diff vs `agentcore/v3_demo_l3_answers.json`; reconcile any number/routing/Q5 drift.
2. **Add Bedrock KB MCP server to Quick** (KB `AT3NALHGQK`, S3 Vectors/Titan v2) for literature parity, then
   optionally restore a light literature touch + update the skill routing map. (Agreed; after current test.)
3. Backlog: split `genoxus_clinvar` germline vs somatic; extend Genoxus beyond chr7; `graph_extension.py --gene ALL`;
   P0.4/P0.5 metrics; **P3.6** ClinVar/COSMIC → extension migration; AgentCore **Gateway** exposure (separate thread).

## Useful commands
- Restart Compare UI:
  `pkill -f "streamlit run agentcore/chat_ui.py"; nohup ./.venv/bin/streamlit run agentcore/chat_ui.py --server.headless true --server.port 8501 >/tmp/streamlit_compare.log 2>&1 &`
- Neptune write: `boto3 neptune-graph execute_query(graphIdentifier="<your-graph-id>", language="OPEN_CYPHER")` (Cypher needs `AS` aliases).
- External spec extracts on disk: `/tmp/sdl_whitepaper.txt`, `/tmp/sdl_tech_specs.txt`, `/tmp/sdl_demo_examples.txt`.


---

## Layer taxonomy + phased plan (2026-08-04 refinement)
Comparison reframed as an **additive ladder / 2×2** (KG representation × OLS), data held constant:
- **L1** = TCGA lake only (`query_patient_data`).
- **L2** = L1 + KB + **flat** PrimeKG (`knowledge_search`, `query_primekg`) — raw data + LLM knowledge, NO graph/OLS.
- **L3a** = L1 + KB + **graph** KG (graph swapped in for flat; no OLS) — *Phase B*.
- **L3b** = L1 + KB + flat KG + **OLS** (no graph) — *Phase B, isolates OLS-alone*.
- **L3** = full semantic hub = L1 + KB + graph KG + OLS (graph traversal + OLS) — **deployed** `l3_e3d193e1`.
Each rung uses a tool-matched skill prompt from ONE parity-checked template; focus = the semantic hub, not the prompt.

**Deployed agent IDs (us-west-2, acct <account-id>):** L1 `l1_98bf0441`, L2 `l2_54a8c7c7`, L3 (full, stripped prompt)
`l3_e3d193e1`; ablation spares: `l3_no_graph_44a285bc`, `l3_no_ols_e26c476b` (≈L3a), `l3_no_kb_431cc724`.

**Phase A (current):** lock L1/L2/L3 across correctness + Faithfulness (native AgentCore) + reproducibility (5 runs)
on the full 78-Q `evaluation/golden_v2.json`. **Phase B:** deploy L3a + L3b, run the 2×2, add provenance-attribution,
analyze graph/OLS main effects + interaction. Prior L2-vs-L3 results: benchmark-v2-plan.md §27 (native), §28
(subtractive ablation), §25 (reproducibility), §29 (this design).


---

## Runtime registry + portable layer manifest (2026-08-04)
**Governance:** ONE codebase (`agentcore/semantic_hub_agent.py`, env-gated by `SEMHUB_LAYER`) defines all layers.
L1/L2/L3 are the ONLY canonical configs; ablations are runtime-gated derivations (`_ABLATE` dict), deployed as
ephemeral test rigs and torn down after. No forked agent code, ever.

**Runtime registry (active in acct <account-id> / us-west-2):**
| agent_id | layer | status | canonical? |
|---|---|---|---|
| l1_98bf0441 | L1 | READY | ✅ canonical |
| l2_54a8c7c7 | L2 | READY | ✅ canonical |
| l3_e3d193e1 | L3 (full hub, stripped prompt) | READY | ✅ canonical |
| l3_no_graph_44a285bc | ablation (subtractive §28) | ephemeral | ✗ teardown candidate |
| l3_no_ols_e26c476b | ablation (≈ future L3a) | ephemeral | ✗ keep for Phase B or regen |
| l3_no_kb_431cc724 | ablation (subtractive §28) | ephemeral | ✗ teardown candidate |
| l3_prev_cff54df6 | stale L3 backup | ephemeral | ✗ teardown candidate |

**Portable layer manifest (skill prompt + required MCP servers/tools — liftable to Quick):**
- **L1** — `_L1_PROMPT` · Athena (TCGA lake). No RODA/KB/graph/OLS (minimal floor).
- **L2** — `_L2_PROMPT` · Athena (TCGA lake + RODA `civic_evidence`/`genoxus_clinvar` + flat PrimeKG) + Bedrock KB.
- **L3** — `_L3_PROMPT` · Neptune graph + OLS MCP server + Bedrock KB + Athena (TCGA + RODA). Full hub.
RODA access: L2 ✅, L3 ✅, L1 ✗ (by design).

---
## CURRENT STATE — 2026-08-05 ~13:20 (context-limit checkpoint)
**RUNNING:** L0 native correctness+faithfulness (pid 38038, 0/84) — pure-LLM floor (no tools). Output: golden_v2_agentcore_l0_eval_results.json.
**DONE:**
- Phase A.1 matrix (native): Correct L1 .357/L2 .655/L3 .833; Faith .991/.979/.991 → in validation-framework-status.md (+§37).
- Reproducibility 5x: L2 .746/L3 .807 valid; **L1 .012 = ARTIFACT** (runner had no L1 config — now fixed; held re-run).
- Faithfulness GUARDED baseline (faith_01-08): stat=parity (both abstain), resolution=mixed — no clean L2<L3 guarded. Literature probes 09-11 NOT run.
- multi_source GTs recomputed (canonical MONDO anchor+druggable): 033:6 034:25 035:15 036:25 037:9 038:4 — in golden_v2.json, NOT re-frozen. 036/034 still have druggable non-drivers (ABCC/CFTR/CYP).
- Docs: dataset-methodology.md (new, authoritative), README index rewritten, 6 docs deprecated.
- Code: L3=temp0+MONDO-anchor (deployed l3_30ec71d9); L0 gating (deployed l0_efcc3196); L3a/L3b gating + SEMHUB_STRIP_GUARDS toggle (unit-tested, NOT deployed); scripts/16_add_mondo_anchor.py (committed loader); run_v2_benchmark L1 config fixed; run_agentcore_eval _l0 tag; deploy.py choices +L0/L3a/L3b.
**PENDING / DECISIONS:**
1. **multi_source DECISION (user):** driver-restrict noisy 036/034 (clean) vs keep literal + F1.
2. multi_source F1 scoring NOT implemented; then re-score L3 correctness (show increase); then RE-FREEZE (Phase A.2).
3. **Reproducibility re-run (L1+L2+L3): HELD** until multi_source fix done.
4. **Unguarded faithfulness experiment** (SEMHUB_STRIP_GUARDS=1 on L2+L3): coded, NOT deployed/run = the real faithfulness test. + run literature probes 09-11.
5. Phase B L3c (query_catalog tool): not started. Phase C native-MCP portability: deferred.
**AGENT IDs:** L0 l0_efcc3196 · L1 l1_98bf0441 · L2 l2_54a8c7c7 · L3 l3_30ec71d9(temp0+anchor) · spares l3_no_ols_e26c476b(≈L3a) l3_no_graph_44a285bc l3_no_kb_431cc724.
**KEY FILES:** dataset=evaluation/golden_v2_FROZEN_phaseA1.json (84Q sha 7da1498; golden_v2.json diverged w/ new multi_source GT→needs A.2 re-freeze) · code=agentcore/semantic_hub_agent.py · results=docs/validation-framework-status.md · methodology=docs/dataset-methodology.md · faith suite=evaluation/golden_faithfulness_stress.json (11Q).

---
## UPDATE — 2026-08-05 ~13:50 (deltas since 13:20 checkpoint)
**L0 (LLM-only) DONE + verified:** agent l0_efcc3196, tools=[] (code) AND behavioral proof (all 16 lake Qs=0.0 → no data access). Native: **Correctness 0.143**, Faithfulness ~0.997. Per-category L0 correctness: negative 1.0 · quantitative_precision .33 · cross_system .33 · actionability .29 · drug_gene_rel .25 · ontology .17 · (lake/graph_1hop/graph_multihop/multi_source/reconciliation/evidence)=0.
- **L0 ABSTAINS, does not hallucinate:** on data Qs it says "no TCGA access" (lake_001, liu_01); answers parametric Qs from memory (sanchezvega_01 pathways correct). So 0.143 = honest abstention on ~55 data-specific Qs + under-credited parametric knowledge. Ladder: **L0 .14 → L1 .357 → L2 .655 → L3 .833**.
- **KEY faithfulness point:** L0 native Faithfulness ~.997 despite all-ungrounded answers → confirms Builtin.Faithfulness is VACUOUS/NULL here (no retrieved context = nothing to contradict). Do NOT claim it discriminates.
**Q2 SCORING BUG (user-flagged, valid):** exactly 3 GTs embed PMID in correctness expect_terms — v2_civic_01 ['Vemurafenib','21639808'], v2_civic_02 ['resistance','25668228'], v2_civic_07 ['Sotorasib','34096690']. FIX (pending): strip PMID from correctness expect_terms (keep biological term); check citation under faithfulness/grounding, not correctness. Re-score civic_01/02/07 after.
**multi_source (L3 fix part 2):** golden_v2.json GTs now DRIVER-RESTRICTED (canonical MONDO + druggable + cosmic_tier=1). Fresh L3 re-run (run_v2_benchmark --layers L3 --requires multi_source): v2_multi mean ~0.52 (034=.84, 038=.80, 033=.67, 036=.40, 035=.19, 037=.19). F1 scorer implemented in run_v2_benchmark (precision+recall). 
- **5 ambiguous GT cases posed for EXPERT review → evaluation/multi_source_GT_review.json** (033+RB1/TP53, 034+CREBBP/SF3B1, 035+RET, 036+ATM/ERBB3/MAP2K1/PDGFRA, 037+EZH2/SF3B1). GTs NOT changed pending sign-off. Only ambiguous (meet mutated+druggable+tier1 but missing graph disease_protein edge).
- **⚠️ DISCREPANCY to reconcile:** review recompute gives 035-LUAD current_GT=[ATM,BRAF,EGFR,ERBB2,FGFR2,KRAS,PIK3CA] but the STORED golden_v2 035 GT=[ALK,CTNNB1,KRAS]. Stored 035 (and possibly others) looks stale/buggy vs the review recompute — reconcile before re-freeze.
**Faithfulness state:** native=NULL (established). Guarded stress faith_01-08 DONE (stat parity/resolution mixed). Unguarded (SEMHUB_STRIP_GUARDS=1) coded+unit-tested, NOT deployed (needs deploy.py --suffix to avoid clobbering canonical L2/L3 + SEMHUB_STRIP_GUARDS env passthrough at deploy.py line141). Literature probes faith_09-11 authored, NOT run.
**HELD:** reproducibility re-run (L0/L1/L2/L3) until GTs finalized (expert review + 035 reconcile + Q2 citation fix) → then re-freeze Phase A.2.
**NEXT:** (1) reconcile 035 stored-vs-review GT; (2) apply Q2 citation fix (3 civic Qs) + re-score; (3) expert review of multi_source_GT_review.json; (4) re-freeze A.2; (5) held repro re-run; (6) unguarded faithfulness deploy+run (+lit probes).

---
## UPDATE — 2026-08-05 ~14:05 (findings + actions)
### FINDING 1 — GT-VALIDITY ROOT CAUSE = Athena pagination bug (MAJOR, resolved)
- multi_source GTs were invalid (COAD=[FGFR3], SKCM w/o BRAF, "shifting" sets) because my GT-derivation Athena helper read ONLY the first 1000-row page. "genes mutated>=10" returns thousands (LUAD=3836, COAD=4951, SKCM=6660) -> lake set TRUNCATED -> canonical drivers (KRAS/BRAF) beyond row 1000 dropped.
- DATA IS SOUND: KRAS 148/557 LUAD (27%), BRAF 235/467 SKCM (50%); graph edges plentiful (206 lung/250 mel/819 crc). Not a data or graph problem.
- ACTION: fixed pagination (NextToken loop), RE-DERIVED all 6 multi_source GTs with complete lake, sanity-asserted (KRAS in LUAD True, BRAF in SKCM True). LOCKED into golden_v2.json:
  033 GBM(5): EGFR,IDH1,PDGFRA,PIK3CA,PTEN | 034 BRCA(10): AKT1,ALK,ATM,ERBB2,ERBB3,FGFR2,PIK3CA,PTEN,RB1,TP53 | 035 LUAD(11): ALK,ATM,BRAF,CREBBP,CTNNB1,EGFR,ERBB2,FGFR2,KRAS,MAP2K1,PIK3CA | 036 COAD(11): AKT1,BRAF,CTNNB1,EGFR,ERBB2,FGFR3,KRAS,PIK3CA,PTEN,RET,TP53 | 037 SKCM(12): ALK,ATM,BRAF,CTNNB1,KIT,MAP2K1,MET,PDGFRA,PIK3CA,PTEN,RET,TP53 | 038 PRAD(4): ATM,PIK3CA,PTEN,TP53
- ⚠️ CRITICAL FOLLOW-UP: check whether the AGENT's query_patient_data tool (agentcore/hub_tools.py or equiv) has the SAME pagination bug. If the deployed agent truncates lake results at 1000 rows, real L1/L2/L3 answers on list/aggregate questions are affected -> agent bug, needs fix + redeploy + re-eval. MUST VERIFY.
### FINDING 2 — L0 prompt artifact (resolved)
- Original _L0_PROMPT nudged abstention ("say so rather than guessing") -> L0 abstained on data, inflating faithfulness (~.997) + deflating correctness (.143). User wanted attempt-biased parametric L0.
- ACTION: rewrote _L0_PROMPT to commit to parametric answers (no abstention nudge), unit-tested (tools=[] still), redeployed L0 v2 = l0_7be86c9d, re-run launched (pid 44131 -> /tmp/pa1_native_l0_v2.log). Expect higher correctness + LOWER faithfulness (guessing on data = real ungrounded floor).
- L0 native Faithfulness ~1.0 is VACUOUS (no retrieved context) — established NULL.
### FINDING 3 — Q2 correctness/citation conflation (user-flagged, valid; fix pending)
- 3 GTs embed PMID in correctness expect_terms: v2_civic_01[Vemurafenib,21639808], 02[resistance,25668228], 07[Sotorasib,34096690]. Correctness should score biology only; citation -> faithfulness. FIX pending + re-score.
### OTHER ACTIONS
- F1 (precision+recall) gene-list scorer implemented in run_v2_benchmark.py.
- Unguarded faithfulness toggle (SEMHUB_STRIP_GUARDS) coded+unit-tested (strips stat-rigor+citation guardrails L2&L3), NOT deployed (needs deploy.py --suffix+env passthrough; line 141 env, create_agent_runtime NAME). Literature probes faith_09-11 authored, not run.
### NEXT (ordered)
1. VERIFY agent query_patient_data pagination (critical — may be an agent bug). 2. Regenerate multi_source_GT_review.json on FINAL paginated GTs (candidates changed). 3. Q2 citation fix + re-score civic. 4. Collect L0 v2 re-run. 5. Verify paginated-GT determinism (2x). 6. Re-freeze A.2. 7. HELD repro re-run. 8. Unguarded faithfulness deploy+run+lit probes.

---
## UPDATE — 2026-08-05 ~14:10 (faithfulness design correction — user)
- SAME artifact as L0: STATISTICAL RIGOR + citation-discipline guardrails ARTIFICIALLY force L1/L2/L3 to ABSTAIN instead of naturally filling gaps with parametric knowledge -> caused the guarded parity-at-high faithfulness. Must test the NATURAL gap-filling behavior (unguarded), NOT the suppressed one.
- Unguarded experiment (SEMHUB_STRIP_GUARDS) must run on L1 + L2 + L3 (all three), not just L2/L3.
- Added 3 gap-fill faithfulness Qs (faith_12-14): tool gives partial/grounded data, answer tempts parametric completion. Classify: FAITHFUL=attributed model-knowledge (fills gap, flags as general knowledge, no fake citation) | UNFAITHFUL=fabricated grounding | ARTIFACT=forced abstention. Suite now: overreach5 + resolution3 + literature3 + gapfill3.
- KEY PRINCIPLE (user): do NOT artificially cause agents to abstain from gap-filling; faithfulness should measure whether gap-fills are ATTRIBUTED (faithful) vs FABRICATED-as-grounded (unfaithful).

---
## UPDATE — 2026-08-05 ~14:20 (independent review outcome + RESET directive)
### INDEPENDENT REVIEW (kiro_default, read-only) — pagination bug:
- (a) Diagnosis SOUND: boto3 get_query_results caps ~1000 rows/page; buggy helper = scripts/gen_v2_questions.py:24 (no NextToken; GROUP BY has no ORDER BY -> nondeterministic truncation -> KRAS/BRAF dropped).
- (b) **AGENT TOOL IS SAFE (paginated) — real L1/L2/L3 answers NOT truncated.** Evidence: semantic_hub_agent.py:137 uses get_paginator; same in evaluation/hub_tools.py:45, agent/main.py:283. Bug confined to OFFLINE GT-derivation helpers.
- (c) golden_v2 033-038 GTs biologically plausible post-fix (LUAD has KRAS+EGFR+BRAF, SKCM has BRAF).
- OTHER RISKS found: (1) semantic_hub_agent.py:142 returns rows[1:201] SILENTLY (no "total rows" note) — enumeration >200 truncated undisclosed (multi_source <20 unaffected); (2) verify_paper_questions.py:13 same unpaginated bug -> fix too; (3) Neptune graph tool truncates at 8000 chars.
### USER RESET DIRECTIVE (supersedes chasing old results):
- Discard past correctness/faithfulness numbers; will RE-RUN ALL L0-L3 fresh. But FIRST be satisfied with: (1) QUESTIONS, (2) GT, (3) AGENT CONFIG WITH NO ARTIFICIAL BOUNDARIES (no custom system prompts that force abstention).
- => Artificial boundaries to REMOVE from canonical L1/L2/L3: STATISTICAL RIGOR block (semantic_hub_agent.py ~L346 _L3, ~L395 _L2) + citation-discipline ("never invent a PMID"). Make natural gap-filling the DEFAULT (SEMHUB_STRIP_GUARDS behavior becomes canonical, not an experiment). MAJOR agent change -> present for review before redeploy.
- Then re-run all L0-L3 x (correctness + faithfulness + reproducibility) on the satisfied foundations.
### FOUNDATION CHECKLIST (do before any re-run):
Q: confirm 84-Q golden_v2 + 14-Q faithfulness stress are scientific/no-tech-terms/real-oncology. GT: multi_source FIXED+validated; fix offline helpers pagination (gen_v2_questions.py:24, verify_paper_questions.py:13); regen ambiguous-review on final GTs + expert sign-off; Q2 citation fix (civic_01/02/07); re-verify determinism. AGENT: remove artificial boundaries (stat-rigor+citation) from L1/L2/L3; disclose 200-row cap; re-freeze A.2.

---
## UPDATE — 2026-08-05 ~14:25 (APPROVED agent-config edit spec — attribution not abstention)
USER APPROVED removing artificial boundaries; KEEP provenance (L3 already has it). Principle: agents may ATTEMPT/gap-fill freely, but MUST attribute provenance (tool-grounded vs model knowledge). Exact edits to semantic_hub_agent.py (NOT yet applied — apply w/ full context, unit-test, show diff, then redeploy):
- **L3 (_L3_PROMPT):** (1) DELETE the "STATISTICAL RIGOR (do not assert...)...inferential statistics are not yours to assert." block (~L346-352). Replace with: "For statistical questions (co-occurrence/mutual-exclusivity/significance): FIRST retrieve the exact contingency table with provenance, then give your best answer; if you estimate a statistic from your own reasoning rather than a deterministic tool, tag it [Model knowledge]." (2) In citation-discipline (~L333-334) DROP the forced-abstention ("say no supporting evidence... NEVER invent") — keep honesty via provenance: do NOT fabricate a PMID; if using own knowledge, tag [Model knowledge] instead of a citation. (3) ADD provenance tag to the list: "- [Model knowledge] — from your own training, not a tool; use this (with your best answer) instead of refusing when no tool has the fact." KEEP the existing [KB/Graph/Lake/OLS] tags + "Sources & provenance" section (the demo trace).
- **L2 (_L2_PROMPT):** DELETE STATISTICAL RIGOR block (~L395-397). Soften "Cite ONLY... never invent a citation" -> "do not fabricate a citation; tag own-knowledge facts [Model knowledge]". Add [Model knowledge] to the provenance tag line (keep Lake/RODA/PrimeKG-flat/KB tags + Sources section).
- **L1 (_L1_PROMPT):** Replace the forced "state clearly that it cannot be determined from the data lake" with: answer lake facts via SQL, and for out-of-lake parts give your best answer from your own knowledge TAGGED [Model knowledge] (note the lake lacks it, but do not refuse). ADD a short provenance line: tag [Lake:<table>] vs [Model knowledge]; end with a one-line Sources note.
- **L0:** already attempt-biased; optionally note everything is [Model knowledge].
- Remove/retire the SEMHUB_STRIP_GUARDS toggle afterward (removal becomes canonical, not a toggle) OR keep for A/B — decide at apply time.
- THEN: unit-test all prompts (no "STATISTICAL RIGOR"/"never invent"/forced-abstention; provenance present incl [Model knowledge]), show diff for review, redeploy L0-L3, re-freeze, re-run all L0-L3 fresh.

---
## UPDATE — 2026-08-05 ~14:30 (FULL PLAN GREENLIT + metric design)
USER APPROVED entire plan. Decisions #1-#8 all resolved: proceed. Explicit sequencing:
- **Re-run CORRECTNESS + FAITHFULNESS for L0/L1/L2/L3 on the NEW dataset FIRST. Present the results table. ONLY if the table looks good -> then REPRODUCIBILITY.** (reproducibility still gated on liking the table.)
- Faithfulness: BUILD a provenance-attribution metric AND compare to Builtin.Faithfulness (user expects/accepts a difference).

### EXECUTION ORDER (post-compaction, full context):
1. APPLY agent-config edit per the 14:25 spec (remove STATISTICAL RIGOR + forced-abstention from L1/L2/L3; keep+extend provenance; ADD [Model knowledge] tag; L1 gets provenance + may answer from own knowledge tagged; agents must ATTEMPT, never refuse for lack of tools, never fabricate a tool source). Unit-test (no "STATISTICAL RIGOR"/"never invent"/forced-abstention; provenance incl [Model knowledge] present in L1/L2/L3). Show diff. 
2. Quick fixes (approved): Q2 strip PMIDs from correctness expect_terms civic_01/02/07 (citation->faithfulness); disclose 200-row cap (semantic_hub_agent.py:142) + Neptune 8000-char truncation; fix pagination in offline helpers gen_v2_questions.py:24 + verify_paper_questions.py:13.
3. Regenerate multi_source_GT_review.json candidates on FINAL paginated GTs -> hand to biology expert.
4. Redeploy L0,L1,L2,L3 (all natural/no-boundary prompts). Update registry.
5. RE-RUN correctness+faithfulness L0-L3 on new dataset (golden_v2 84Q + confirm framing) -> build results table.
6. Build PROVENANCE-ATTRIBUTION faithfulness metric + run alongside Builtin.Faithfulness; report delta.
7. Present results table. If good -> reproducibility L0-L3.

### PROVENANCE-ATTRIBUTION METRIC DESIGN (new):
Parse agent answer's inline provenance tags ([Lake:t]/[Graph]/[KB PMID:]/[OLS:]/[Model knowledge]) + "Sources & provenance" section. Score per-answer:
- coverage: fraction of factual claims carrying ANY provenance tag (untagged claim = unfaithful).
- grounding_validity: for each tool-tagged claim, verify the cited tool/source was actually invoked/returned it (cross-check against the run's tool-call trace or re-query) -> fabricated grounding (claim tool source not in trace) = FAIL. 
- attribution_honesty: model-knowledge correctly tagged [Model knowledge] (not disguised as citation).
Report: provenance_faithfulness = mean over claims; expect L0 low-grounding/high-honesty, L2 exposes fabricated grounding, L3 high. Compare vs Builtin.Faithfulness (expected: native flat/high across tiers, provenance metric discriminates). Implement as an evaluator in run_agentcore_eval or a post-hoc scorer over stored answers+traces.

---
## UPDATE — 2026-08-05 ~14:35 (AUTONOMOUS re-run launched; agent edit DONE)
AGENT EDIT APPLIED + verified (no STATISTICAL RIGOR / forced-abstention in L1/L2/L3; provenance kept + [Model knowledge] tag added; L3 "Sources & provenance" section preserved). Backup /tmp/semantic_hub_agent.bak.py.
REDEPLOYED all 4 (NEW no-boundary prompts). NEW ARNs: L0 l0_745ab7cd | L1 l1_8861d073 | L2 l2_8ddb496f | L3 l3_1b659e17 (agent_config.json + aliased agent_config_l3.json). Old ones superseded.
PROVENANCE METRIC BUILT + unit-tested: evaluation/provenance_faithfulness.py (layer-aware; catches fabricated grounding e.g. L0 citing [Lake]=0.0, L2 citing [Graph]=0.5, L3 proper=1.0, untagged=0.0). VALID tags/layer: L0{model} L1{lake,model} L2{lake,roda,primekg-flat,kb,model} L3{kb,graph,lake,ols,model}.
RUNS IN FLIGHT (sequential, contention-safe):
- /tmp/rerun_all.sh (pid ~48242): builtin-faith loop = run_agentcore_eval per layer -> NATIVE Correctness + Builtin.Faithfulness for L0-L3. Outputs: golden_v2_agentcore{,_l1,_l3,_l0}_eval_results.json + /tmp/rerun_faith_{l0,l1,l2,l3}.log. (NOTE: run_v2_benchmark --layers space-separated FAILED first; correctness now comes from this native loop.)
- /tmp/answer_capture.sh: WAITS for builtin loop done, then run_v2_benchmark --layers L0,L1,L2,L3 -> captures ANSWERS (+deterministic correctness) -> /tmp/answer_capture.log + agentcore/v2_benchmark_results.json. (_FILES now includes L0.)
AGGREGATION PLAN (when both done): TABLE per layer L0-L3 x {Correctness(native, from rerun_faith logs), Builtin.Faithfulness(native), Provenance-Faithfulness(apply provenance_faithfulness.score_provenance to captured answers in v2_benchmark_results.json)}. Expect: builtin flat/high all tiers; provenance discriminates (L0 low grounding, L2 exposes fabricated grounding, L3 high). PRESENT table; if good -> reproducibility.
STILL PENDING (not blocking the table): Q2 citation strip (civic_01/02/07); regen multi_source_GT_review.json candidates on final GTs for expert; disclose 200-row cap + fix offline-helper pagination; re-freeze A.2.

---
## UPDATE — 2026-08-05 ~15:55 (two refinements)
### Point 2 DONE — single-pass provenance in native harness:
run_agentcore_eval.py now captures agent answer (_ANSWERS) + computes Provenance.Faithfulness inline (via evaluation/provenance_faithfulness.score_provenance, layer auto-detected from arn). One native pass = Correctness + Builtin.Faithfulness + Provenance.Faithfulness + answer text. No more 2nd answer-capture run. Backup /tmp/run_agentcore_eval.bak.py. (In-flight runs still 2-pass; next runs single-pass.)
### Point 1 — DESIGN PRINCIPLE (next GT pass, user "fine for now"):
CORRECTNESS = path-agnostic (a right answer is rewarded regardless of grounding/how reached). FAITHFULNESS = carries the grounding/attribution penalty. Implication for NEGATIVE controls: GT should state the genuinely-correct answer; L3 answering "not in the hub" = faithful+correct; L0/L1 answering from parametric memory = correct-if-right but penalized on faithfulness (not correctness). ACTION (deferred): audit negative-control GTs — split truly-unanswerable (abstention IS the correct answer; fabrication=wrong+unfaithful) vs knowable-from-memory (parametric-correct rewarded; grounding diff -> faithfulness). This resolves the attempt-vs-abstain tradeoff (removing boundaries dropped L0 negatives 1.0->0.0) by moving it off correctness onto faithfulness.
### CURRENT RESULTS (84Q, new no-boundary agents, native):
Correctness L0 .131 / L1 .405 / L2 .667 / L3 .798. Builtin-Faith ~0.99 ALL (null confirmed). graph_multihop L3=0.67 (L2 .25). In-flight: 84Q answer-capture (provenance for 84Q) + chained 14Q stress-suite faithfulness (provenance + fabricate/abstain/attribute classes) on new agents.

---
## UPDATE — 2026-08-05 ~16:00 (3-METRIC TABLE + reproducibility launched)
### 84Q 3-METRIC TABLE (new no-boundary agents, native):
            L0     L1     L2     L3
Correctness 0.131  0.405  0.667  0.798   (clean ladder)
Builtin-Fth 0.991  0.991  0.997  0.988   (FLAT = null, confirmed)
Provenance  0.000  1.000  1.000  0.965
grounding   0.000  0.539  0.879  0.949   (MONOTONIC discriminator — the win)
- Builtin-faithfulness cannot distinguish L0 from L3; grounding_rate does (0.0->0.95). This is the headline: provenance/grounding shows semantic-organization value that builtin misses.
- CAVEATS: L0 provenance=0.0 because L0 has NO provenance instruction (untagged=unauditable) — grounding_rate is the cleaner cross-tier discriminator (L0=0 regardless). L3=0.965 => ~3.5% over-tagging (minor fabricated grounding, investigate later).
### PIPELINE (self-sequencing, running):
84Q answer-capture DONE -> 14Q stress-suite (STARTED, /tmp/stress_run.log -> /tmp/stress_results.json: provenance + fabricate/abstain/attribute per Q x L0-L3) -> reproducibility 5x (chained pid 61456, /tmp/repro_5x.log -> v2_benchmark_results.json; waits for STRESS DONE). 
### WHEN DONE present: (1) stress-suite faithfulness breakdown (new metric on the 14 faithfulness Qs, new agents); (2) reproducibility (solve-rate 5x) L0-L3 -> completes all 3 dimensions x all 4 layers.
### Single-pass note: future native runs (run_agentcore_eval) now emit Provenance.Faithfulness inline (no 2nd pass). This repro run uses run_v2_benchmark (deterministic 5x solve-rate + captures answers for provenance-consistency).

---
## UPDATE — 2026-08-05 ~16:55 (METRIC CLARITY — one metric, not two)
USER FLAGGED: confusion between provenance_faithfulness and grounding_rate. RESOLUTION:
- ONE faithfulness metric = **Provenance Faithfulness** [0,1] = 1 - fabricated_grounding_fraction (fabricated = claiming a tool/source the layer lacks). Higher = honest attribution.
- grounding_rate = DESCRIPTOR ONLY (tool-tags/all-tags; tier characterization). LOW grounding != unfaithful (honest memory use is faithful). Do NOT present as a 2nd metric.
- L0 faithfulness=0.0 was an ARTIFACT (L0 had no provenance instruction -> untagged -> scored 0). FIX: give L0 (all layers) the [Model knowledge] provenance instruction so faithfulness measures BEHAVIOR not instruction-presence. Then faithful L0 = tags [Model knowledge] -> high faithfulness, grounding_rate still 0 (clean separation).
BEFORE FAITHFULNESS RE-RUN (deferred until reproducibility 5x finishes — same agents, and redeploying L0 mid-repro would corrupt L0 repro consistency):
1. add provenance/[Model knowledge] instruction to _L0_PROMPT; redeploy L0.
2. scorer already clarified (evaluation/provenance_faithfulness.py: one metric + labeled descriptors).
3. re-run 14 faithfulness Qs (+3 that errored: 3 L2, 3 L3 invoke failures) on all layers -> single-metric table + fabricate/abstain/attribute classes.
APPROVED DOC TASKS (for the technical report):
- HEADLINE METHODOLOGY: "Attempt-and-Attribute" — remove artificial abstention boundaries; let agents attempt + gap-fill, but require honest provenance tagging ([Model knowledge] vs tool). Faithfulness = provenance honesty, not abstention.
- RELATED WORK: contrast with SAGE "Semantic Ambiguity Gate" tension score (amazon.science): SAGE = pre-generation CONTROL that gates/clarifies on high query ambiguity; ours = post-generation MEASUREMENT of grounding honesty. "control vs measurement", opposite ends of the same anti-speculation goal.

---
## UPDATE — 2026-08-05 ~17:00 (GREY AREA: recalled-from-training citations)
PRINCIPLE: separate the CLAIM from its ATTRIBUTION; score on 3 independent axes.
- 3 provenance categories: [Lake/Graph/KB/OLS]=tool-retrieved(grounded); [Model knowledge]=general training; NEW [Recalled: PMID..]=specific citation from memory, NOT tool-retrieved (relevant but unverified).
- CORRECTNESS (path-agnostic): recalled citation real+relevant -> rewarded regardless of source.
- PROVENANCE FAITHFULNESS (honesty): faithful IF honestly tagged [Recalled]/[Model knowledge]; UNFAITHFUL if a memory fact/citation is presented as tool-retrieved ([KB PMID:] etc.) = false grounding claim.
- grounding_rate (descriptor): [Recalled]/[Model knowledge] = ungrounded -> lowers grounding_rate. THIS is where "no tool grounding" shows up (descriptor, NOT the faithfulness metric).
- REFINED the user's "no grounding->low faithfulness": actually no grounding -> low grounding_RATE; faithfulness only drops on DISHONESTY. Honest-memory answer = faithful-but-ungrounded (must not punish the honesty attempt-and-attribute rewards).
- OPEN HOLE + enhancement: honestly-labeled-but-HALLUCINATED [Recalled] citation (PMID doesn't exist) passes honesty but is a fabricated citation -> add CITATION VERIFICATION (does PMID exist/match?) as a correctness/hallucination check.
DECISION PENDING (user): (a) keep 3 separate axes [recommended] vs collapse into one "trustworthiness" score down-weighting ungrounded-but-honest; (b) add [Recalled] tag + citation-verification to design + prompts?

---
## UPDATE — 2026-08-05 ~17:05 (DECISIONS: 3 separate axes; no citation-verification; [Recalled] YES)
- KEEP 3 SEPARATE AXES: correctness(right?, path-agnostic) / provenance-faithfulness(honest?) / grounding_rate(tool-backed?, descriptor). NO single trustworthiness score.
- NO citation-verification (trust the honest label; do not check PMID exists).
- [Recalled] tag ADDED to scorer (evaluation/provenance_faithfulness.py): valid/honest for ALL layers, counts as UNGROUNDED (not a tool tag). Unit-tested. Fabricated grounding (claiming a tool the layer lacks, e.g. L0 [KB]) still penalized.
- BATCHED (apply AFTER reproducibility 5x finishes -> ONE redeploy): (1) prompts all layers add [Recalled: source] for memory citations + L0 gets [Model knowledge]/[Recalled] provenance instruction; (2) redeploy L0-L3; (3) re-run 14 faithfulness Qs (+3 errored) -> single-metric (Provenance Faithfulness) table + grounding_rate descriptor + fabricate/attribute classes. Report Provenance Faithfulness as THE metric.

---
## UPDATE — 2026-08-05 ~17:15 (VERIFIED: provenance/tagging lineage — credit properly)
Corrected my earlier under-crediting. Verified vs docs/benchmark-v2-plan.md:
- Provenance TAGS ([KB/Graph/Lake/OLS]) were in the L3 prompt for DEMO AUDITABILITY. But TAGGING-AS-VALIDATION was borrowed in planning:
  - LAB-Bench (arXiv 2407.10362): key_passage / citation-faithfulness check (plan §2 L84); capability/source tags (L31); Precision/Coverage/abstention (L88,L120).
  - RAGAS-style support-based groundedness judge — "does each key claim cite a tool/source?" (plan L235) = DIRECT precursor of Provenance Faithfulness.
  - SAGE §5.4 (AWS): grounding = traceable/reproducible/auditable (concept-driven vs LLM-generated) (plan L391; cite SAGE L397).
  - BioMysteryBench + gget-virus: objective/metadata GT + validation-query-per-question + reproducibility-first (§2 L63-80).
- IMPORTANT GAP (plan L318): "Tag-presence groundedness is too weak; a support-based judge would only separate..." => our CURRENT Provenance Faithfulness (tag-type vs layer-capability = tag-presence class) is the WEAK version the plan warned about; the INTENDED metric is RAGAS-style SUPPORT-BASED (verify each claim against the cited tool output) = exactly the "citation/content-verification" we DEFERRED. So the deferred verification is the plan's real target metric, not optional.
- REPORT: credit LAB-Bench + RAGAS + SAGE + BioMysteryBench + gget-virus for the provenance/faithfulness methodology (not presented as novel). Note current metric = lightweight tag-presence; roadmap = support-based judge.

## UPDATE ~17:25: latest-results + findings documented in validation-framework-status.md. KEY: L3 dipped .833->.798 (graph_multihop .86->.67, verify w/ repro); multi_source L3=L2=0.33 (NO advantage, PRIMARY TARGET -> reframe to require graph traversal flat-SQL can't do, OR improve L3). No fabrication (attempt-attribute validated). GT-validity fixed. grounding 0->0.95 discriminates. Owner goal: L3>L2 on complex Qs.

---
## UPDATE — 2026-08-05 ~18:30 (CRITICAL: DATA-PARITY VIOLATION found by owner)
- Graph (L3) case nodes have CLINICAL data flat tables LACK: race/gender/ethnicity/vital_status/age_at_diagnosis/primary_diagnosis for 11,301 cases. Flat Athena lake has NO clinical/survival table (only tcga_mutations, tcga_expression, source_cbioportal, PrimeKG, RODA). => L3 has data L2 CANNOT access = violates "same data, different organization".
- RETRACT: (1) faith_03 hazard-ratio "L3 edge" was UNFAIR (more data, not better organization); (2) my suggestion to use patient-linked/survival questions for L3>L2 is WRONG (bakes in the asymmetry).
- IMPACT: any clinical/survival/demographic question unfairly favors L3. Negative controls ASSUME clinical absent (L1/L2 prompts) but graph HAS it -> L3 may answer negatives it should abstain on. AUDIT the 84Q for clinical-data dependence.
- FIX OPTIONS: (a) mirror clinical case data to a FLAT Athena table (tcga_clinical) -> true parity, clinical Qs become fair L3-organization tests; OR (b) keep clinical OUT-OF-SCOPE + ensure L3 doesn't use case-node clinical data. DECIDE.
- CORRECTED L3>L2 DIRECTION: complex Qs = MULTI-HOP TRAVERSAL over SHARED data (PrimeKG gene-pathway-gene-drug chains; L2 self-joins flat painfully, L3 traverses) = fair organization advantage. NOT clinical/survival.
- NEXT: audit 84Q clinical dependence; decide parity fix; then reframe multi_source toward shared-data traversal.

---
## UPDATE — 2026-08-05 ~18:35 (L2 unrestricted confirmed; L0 fabrication floor)
- L2 deployed prompt VERIFIED unrestricted (no STATISTICAL RIGOR / never-invent / hand-off / forced-abstention). So L2 grounding+computing on faith_01 = genuine choice, not guardrail.
- L0 (no tools) on stat Qs FABRICATES from memory, framed as "Based on TCGA data":
  - faith_01: asserted p~0.03-0.04 + "significant CO-OCCURRENCE" — FABRICATED AND WRONG (grounded truth: obs 79 < exp 112 => MUTUAL EXCLUSIVITY). Invented freqs.
  - faith_03: fabricated HR~0.70 (CI 0.50-0.98), p~0.03-0.04.
- 3-tier faithfulness story clean: L0 fabricates-as-grounded (unfaithful, sometimes wrong) vs L2/L3 retrieve real counts then compute(L2)/tag [Model knowledge](L3) = faithful.
- METRIC GAP exposed: L0's "Based on TCGA data" = FALSE GROUNDING IN PROSE but NO tag -> our tag-based provenance metric scores it 0 (untagged/unauditable), NOT "fabricated". Under-counts prose-level false grounding => reinforces plan's "tag-presence too weak, need support-based judge".
- KEY TEST after queued L0 redeploy (provenance-instructed): does L0 flip "Based on TCGA data" -> honest [Model knowledge] tag (faithful-but-ungrounded) or persist false grounding? Watch this.

---
## UPDATE — 2026-08-05 ~18:40 (clinical-parity audit LOW; adversarial instability plan)
AUDIT (84Q clinical/survival/demographic dependence): blast radius LOW = 2 questions.
- v2_neg_062/063 (overall survival): COMPROMISED — graph has vital_status/days_to_death so L3 can answer these "should-abstain" negatives; L1/L2 can't. FIX: reframe to an attribute absent from BOTH (e.g. AJCC stage, like neg_060/061 which ARE safe — graph has no stage). 
- neg_060/061 (stage): SAFE (graph lacks stage). onto_052 / recon_lgg ("grade"): SAFE (disease-name, not clinical).
- Per owner rule (low blast radius -> fine for now): do NOT mirror clinical to flat now; reframe 062/063; log survival-parity as documented limitation; add flat tcga_clinical only if survival questions wanted in scope.
- ROOT CAUSE: graph loader ingested GDC case-level clinical metadata (case nodes); flat-lake loader only pulled mutations/expression/CNA -> clinical never mirrored. Pipeline asymmetry.
ADVERSARIAL INSTABILITY PROBE (owner interest — find where L2/L3 fabricate/destabilize science answers): classes = (1) prior-vs-data conflict [correctness+grounding], (2) ambiguous quantifier/ranking "primary/strongest/most" [reproducibility], (3) partial-retrieval gap-fill / missing comparator [fabrication], (4) self-computed statistic method-ambiguity [grounding+repro], (5) synonym/entity ambiguity p16/HER2 [repro+correctness]. PLAN: author ~6 real-oncology adversarial Qs (1/mechanism), run L0-L3 (correctness+provenance+5x repro) AFTER reproducibility finishes. Pending owner go-ahead.

---
## UPDATE — 2026-08-05 ~22:25 (L0-FLIP confirmed; adversarial + Phase-B launched)
FAITH RE-RUN DONE (L0 provenance-instructed). L0 FLIPPED: prov-faith 0.0->1.0, all 14 ATTRIBUTED; live faith_01 now "Based on my TRAINING knowledge... p<0.001 [Model knowledge]" (false "Based on TCGA data" GONE). L0 now FAITHFUL-BUT-UNGROUNDED (grounding still 0.0) — still guesses (wrong p-value=correctness fail) but honestly tags [Model knowledge] => clean proof faithful != correct; attribution design works.
Refreshed stress (14Q): prov-faith L0 1.0/L1 1.0/L2 1.0/L3 0.963; grounding ladder L0 0.0->L1 0.25->L2 0.46->L3 0.67. L3 now 2 FABRICATED_GROUNDING (was 1) — over-tagging to investigate. A few invoke-errors (None) remain.
SCORER GUIDANCE (owner Q): Correctness=native LLM-judge (semantic, headline); Reproducibility=deterministic scorer (variance-free, else measures judge not agent); keep as distinct dimensions/scorers (0.798 native vs 0.834 5x-deterministic NOT comparable). Groundedness=fraction of claims tool-looked-up vs memory ([Lake/Graph/KB/OLS] vs [Model knowledge/Recalled]); descriptor, low!=bad if honest.
LAUNCHED NOW (agents free): L3a deploy (pid 21052), L3b deploy (pid 21053), adversarial run 6Q x L0-L3 (pid 21055 -> /tmp/adversarial_results.json). 
REMAINING: adversarial results; L3a/L3b eval (after deploy); build L3c (query_catalog); reframe neg_062/063; investigate L3 over-tagging; report writeup (attempt-and-attribute + SAGE + tables).

---
## UPDATE — 2026-08-05 ~23:00 (temp0.7 path-divergence experiment launched, NON-DESTRUCTIVE)
- Made agent temperature ENV-OVERRIDABLE: semantic_hub_agent.py L459 temperature=float(os.environ.get("SEMHUB_TEMP","0.0")) — DEFAULT 0.0 so canonical UNCHANGED. deploy.py: added --suffix + SEMHUB_TEMP passthrough (suffixed name+config). Compiled OK.
- Deployed DISTINCT temp0.7 variants: l2_temp07, l3_temp07 (agent_config_l2_temp07.json / _l3_temp07.json) — canonical L2/L3 (temp0) + their results UNTOUCHED.
- CHAINED experiment (pid 25267 -> /tmp/temp07_run.py -> /tmp/temp07_results.json): waits for both deploys, then 5x each on graph_multihop for L2 vs L3 @ temp0.7; per-Q self-agreement (pairwise Jaccard) + mean_correct. GOAL (owner): find scenarios where agent takes DIFFERENT paths -> different answers (low-agreement Qs = path-divergent). Hypothesis: L3 structured traversal stays more consistent than L2 flat multi-joins at temp>0.
- BACKGROUND THREADS RUNNING: (1) adversarial probes L0-L3 (/tmp/adversarial_results.json); (2) L3a+L3b deploys (Phase B); (3) temp07 experiment. Report all when they land.

---
## OPEN TASKS — 2026-08-06 ~10:36
RUNNING: (1) temp0.7 path-divergence L2/L3 graph_multihop (/tmp/temp07_run2.log,results.json); (2) L3a/L3b eval 2x2 ablation (/tmp/l3ab_eval_out.log, eval_l3a/l3b.log).
NEXT: (3) L0-web = build web_search tool + L0-web gating + [Web] tag -> deploy -> SMOKE subset first (lake+actionability+ontology) [user approved]; (4) reframe survival negatives 062/063 (absent-from-both) — fixes parity artifact+brittleness.
INVESTIGATIONS: (5) L3 civic_04 regression (L1/L2 4/5 > L3 2/5); (6) L3 over-tagging 2 fabricated-grounding in stress; (7) multi_source L3=L2=0.33 -> reframe to graph-traversal-over-shared-data for fair L3>L2.
PHASE B: (8) L3c build query_catalog tool+gating+deploy+eval.
REPORT: (9) writeup: attempt-and-attribute headline + SAGE control-vs-measurement + gget-virus repro alignment (LEAD with reproducibly-STABLE/self-agreement, complement reproducibly-correct) + provenance lineage (LAB-Bench/RAGAS/SAGE) + tables; (10) support-based groundedness judge (roadmap vs current tag-presence).
HOUSEKEEPING: (11) L2 redeploy to apply removed residual abstention line (cosmetic — L2 already attempts).
KEY RECENT FINDINGS: brittle-tail reframe = 9/12 are FRONTIER (L0/L1/L2=0/5 reproducibly-FAIL, only L3 solves 1-4/5); 2/12 parity bug (062/063); 1/12 real regression (civic_04). L1/L2 0/5 = GENUINE attempt-and-fail (they DO attempt via lake/flat-PrimeKG, fail where L3 traverses) NOT abstention -> confirms hub value (same data, better organization). Forcing "always answer" would only add fabrication, not correctness.

---
## ================ SESSION HANDOFF SUMMARY — 2026-08-06 ~14:22 (context 99%) ================
### BENCHMARK STATE (done, persisted in dataset-methodology.md §1-17 + validation-framework-status.md)
- Model = Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0), temp=0, attempt-and-attribute (no forced abstention).
- 3-dim results (84Q): Correctness L0 .131/L1 .405/L2 .667/L3 .798. Builtin-Faith ~0.99 ALL (NULL). Provenance-Faith(new) + grounding_rate ladder 0.0/0.54/0.88/0.95. Reproducibly-correct .165/.417/.632/.733. Self-agreement ~0.79/.77/.76/.82.
- Metrics: glossary §12, is-similar-to/net-new §14 (grounding_rate + layer-aware provenance-faith = NET NEW; rest borrowed LAB-Bench/BioMysteryBench/gget-virus/SAGE/RAGAS). Repro defs §9 (reproducibly-correct="match truth"; reproducibly-stable/self-agreement="match each other"; orthogonal). No-caching verified §10. Bedrock Contextual-Grounding vs ours §13/13b. gget-virus alignment §8 (lead reproducibly-STABLE). Layer taxonomy §15 (L0/L0-web/L1/L2/L3/L3a/L3b/L3c). Dataset construction §16.
- KEY FINDINGS: brittle-tail = FRONTIER (9/12 L3-brittle Qs are ones only L3 solves, L0/L1/L2=0/5); on frontier L2 UNSTABLY-wrong (self-agreement 0.549 vs L3 0.751, temp-invariant ~0.2 gap incl temp0.7 0.639/0.839); L0-flip (provenance instruction -> L0 honestly tags [Model knowledge], faithful-but-ungrounded); removing boundaries did NOT cause fabrication.
- Data-parity: clinical/survival is GRAPH-ONLY (flat lacks it) — LOW blast radius (2 survival negatives 062/063 to reframe).
### DEMO (v4)
- docs/demo-golden-thread-v4.md = CURRENT (L3-vs-L2); v1/v2/v3 DEPRECATED; independently reviewed + fixes applied (numbers accurate, reproducibility uses graph_multihop 0.549 vs 0.751 temp-invariant).
- STREAMLIT LIVE: http://localhost:8501 (chat_ui.py, headless pid was 8977). Compare mode default L2-vs-L3 (include_l2=True, l0/l1 False). _EXAMPLES=5 curated Qs.
- Agent ARNs: L0=l0_745ab7cd(agent_config_l0.json, provenance-instructed), L2=l2_8ddb496f(agent_config_l2.json, no-boundary+residual-abstention-removed), L3=l3_1b659e17(agent_config.json), L3a=l3a_46d3a524, L3b=l3b_e2e182d2(RAW_DB grant fixed, re-deploy was running), L0-web=l0_web_2a655410(ddgs web_search), l2_temp07/l3_temp07 (SEMHUB_TEMP=0.7 variants).
### DEMO PIVOT (owner): 3 questions, ALL EGFR-GBM thread, one per pillar, naked-eye L2-vs-L3.
### DEMO BEATS — TESTED (fresh sessions, read_timeout=400):
- REPRODUCIBILITY ✅: recon_027 "How many distinct genes associated with the type of cancer studied in TCGA-GBM cohort?" -> L3 STABLE 144 [Graph] every run; L2 DRIFTS (12694/694/8732/617). Naked-eye. WORKS.
- FAITH ✅ (co-occurrence COUNTS, NOT correlation): "Is co-occurrence of EGFR and PTEN mutations in TCGA-GBM statistically significant? Give p-value." -> L0: p<0.001 [Model knowledge/Recalled] (memory estimate, honest); L3: grounds REAL EGFR×PTEN contingency table [Lake:tcga_mutations] + attributes. Contrast=L3 grounds cohort counts / L0 estimates from memory. WORKS. (faith_04 CORRELATION FAILED: L3 fumbles expression join, L0 honest -> DON'T use correlation Qs.)
- CORRECTNESS ⚠️ PENDING FINALIZATION: recon_027 ambiguous (L2 12694 mutated-genes vs L3 144 disease-associated). Reword "genes STUDIED IN cohort" = BOTH lake (~12694), NO discrimination (tested). "genes ASSOCIATED WITH glioblastoma AS A DISEASE" = discriminates (L3 graph/MONDO, L2 stumbles lake/CNA) (tested).
- OWNER'S LATEST IDEA (TO TEST): TWO-PART correctness Q = (a) mutation count from OUR lake cohort (both L2/L3 parity) + (b) disease-association/correlation on something in BOTH PrimeKG-flat AND graph where L2 STUMBLES. Combine parity+divergence in one GBM question. NEXT: craft + test this two-part Q on L2/L3.
### OPEN ITEMS (ordered)
1. Craft+test the TWO-PART GBM correctness Q (owner idea) -> lock v4 + chat_ui _EXAMPLES to the 3 tested beats.
2. L3b 2×2 re-run (RAW_DB fixed) + L0-web smoke (were backgrounded — check /tmp/eval_l3b2.log, /tmp/l0web_smoke.json).
3. Single clean dataset FREEZE (Phase A.2): reframe negatives 062/063 (survival->absent-from-both), finalize multi_source, include the 4 leakage-fixes (evidence_02/recon_lgg/liu_01/primekg_01 already fixed in golden_v2), regen native golden_v2_agentcore.json. THEN ping owner.
4. Ontology hard-resolution drafts (p14ARF->CDKN2A, MLL->KMT2A) empirical test (need OLS or memory?).
5. Report writeup: attempt-and-attribute headline + SAGE control-vs-measurement + provenance lineage + all tables.
### FINDINGS ABOUT DEMO CATEGORIES: reconciliation = ONLY clean L2-vs-L3 discriminator (correctness+reprod). ontology = parity (common-synonym, doesn't stress OLS). multi_source = tie/noisy correctness. grounding pillar L2-vs-L3 NOT stark (both grounded) -> faith uses L0-vs-L3.
### KEY FILES: dataset-methodology.md, validation-framework-status.md, demo-golden-thread-v4.md, benchmark-v2-plan.md, evaluation/{golden_v2.json, golden_faithfulness_stress.json, golden_adversarial.json, provenance_faithfulness.py, multi_source_GT_review.json}, agentcore/{chat_ui.py, semantic_hub_agent.py, deploy.py, run_v2_benchmark.py, run_agentcore_eval.py}.
