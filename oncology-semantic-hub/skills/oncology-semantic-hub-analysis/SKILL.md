---
name: oncology-semantic-hub-analysis
description: >-
  Use when a researcher asks about cancer biomarkers, TCGA patient mutations/expression/copy-number,
  drug–gene relationships, pan-cancer driver genes, pathway-level questions, disease–gene associations,
  or somatic clinical actionability that span PrimeKG + TCGA. Drives the Oncology Semantic Hub via its
  MCP tools (Neptune knowledge graph + Athena patient-data lake + RODA variant annotations + OLS
  ontology), discovers the live schema first, and attributes every fact with inline provenance tags.
  Pair with the grounding-faithfulness-eval skill to score the answer.
---

# Oncology Semantic Hub Analysis

Answer precision-oncology questions by combining the **Neptune knowledge graph** (PrimeKG + TCGA
case/sample nodes + ClinVar/COSMIC/MONDO enrichments) with the **Athena patient-data lake** (TCGA
mutations/expression/copy-number across 33 projects), **RODA** variant annotations (CIViC, ClinVar),
and the **OLS** ontology service.

## MCP servers used
- **oncology-hub-data** (Neptune + Athena): `query_knowledge_graph`, `query_patient_data`,
  `query_variant_annotation`, `get_hub_schema`.
- **ontology-lookup-service** (OLS): `search_terms`, `get_term_info`, … for canonical id resolution (`ontology_lookup`).
- **knowledge-base** (Bedrock KB retrieval — a **local** MCP server connected in the harness, e.g. Quick,
  pointed at the hub's Bedrock Knowledge Base): `knowledge_search` — semantic recall over TCGA study
  descriptions + curated PubMed abstracts. Call it FIRST for published-evidence / prior-work /
  "which studies or cohorts relate to X" questions. (See `mcp-servers/aws-public/bedrock-kb-retrieval/`.)

## Discover schema first
Call **`get_hub_schema` at the start of a session** to read the live graph labels/edges + Athena tables
(including any newly onboarded `*_staging`). Do not memorize the schema — it changes as data is onboarded.

## Provenance tagging (REQUIRED)
Put an inline bracket tag immediately after EVERY fact, in the same sentence — tool → tag:
- `knowledge_search` (KB) recall → **`[KB PMID:xxxxx]`** or **`[KB TCGA-XXX]`** (use the REAL citation returned)
- `query_knowledge_graph` result → **`[Graph]`**
- `query_patient_data` number → **`[Lake:<table>]`** (e.g. `[Lake:tcga_mutations]`)
- `query_variant_annotation` → **`[RODA:<table>]`** (or `[Lake:<table>]`)
- a statistic you COMPUTED in Code Execution (Fisher's exact, chi-square, correlation, …) → **`[Compute]`** (show the code; the input counts still get `[Lake]`)
- OLS resolution → **`[OLS:<CURIE>]`**
- your own knowledge (no tool) → **`[Model knowledge]`**; a specific remembered source → `[Recalled: <src>]`
Never leave a number or name untagged — inline tags are the PRIMARY provenance mechanism; a trailing
"Sources" paragraph does NOT satisfy it (you may add one only IN ADDITION). This makes the answer
auditable and lets grounding-faithfulness-eval score it.

**Citation discipline:** cite a PMID / TCGA id ONLY if `knowledge_search` actually returned it — never
fabricate a citation or a tool source. If a fact is from your own knowledge, tag it `[Model knowledge]`.

## Hybrid search (chain the tools) — for literature / evidence / study-discovery questions
1. `knowledge_search` FIRST to recall relevant abstracts/cohorts by meaning;
2. extract entities (genes, diseases) from the recalled passages and resolve them to canonical ids with `ontology_lookup`;
3. use those ids for precise facts via `query_knowledge_graph` / `query_patient_data`;
4. answer, CITING the exact sources `knowledge_search` returned (`[KB PMID:...]` / `[KB TCGA-XXX]`).

## Statistics
For co-occurrence / mutual-exclusivity / significance questions: (1) retrieve the EXACT contingency
table from the lake (counts + denominators, tagged `[Lake:<table>]`); (2) **compute** the statistic
(Fisher's exact, chi-square, correlation, …) using the **Code Execution tool** and tag the computed
value **`[Compute]`** (show the code you ran) — do NOT tag a computed statistic `[Lake]` (the lake holds
counts, not p-values). Only if you cannot run code and must estimate from memory, tag it
`[Model knowledge]`. Do not refuse.

## If the data is not in the hub
If the requested data is absent (e.g. tumor stage, protein abundance, imaging, treatment/response, or a
gene not in the graph), say the hub does not contain it and give your best answer from your own knowledge
tagged `[Model knowledge]` — do NOT refuse, but NEVER fabricate a tool source or citation.

## Workflow patterns
- **Graph-only** (drug targets, pathway membership, disease→gene): `MATCH (g:gene_protein {name:'EGFR'})-[:drug_protein]-(d:drug) RETURN DISTINCT d` — traverse UNDIRECTED, `COUNT(DISTINCT ...)`.
- **Disease-anchored**: resolve the disease with OLS to its MONDO CURIE, then anchor on the single canonical node `(d:disease {mondo:'<CURIE>'})` — a disease NAME fans out to subtypes and gives non-reproducible counts.
- **Lake-only** (patient counts): `SELECT ... FROM tcga_mutations WHERE project_id='TCGA-GBM' ...` — always filter the partition column; count patients by `COUNT(DISTINCT case_id)`, samples by `COUNT(DISTINCT sample_id)`.
- **Copy-number/amplification**: use the cBioPortal table with GISTIC `value=2` (not the mutations table); its `project_id` uses cBioPortal ids (`gbm_tcga`) which differ from GDC (`TCGA-GBM`).
- **Actionability**: CIViC via `query_variant_annotation` (evidence_level A–E); cite the PMID (`citation_id`).
- **Cross-system**: combine lake counts with graph relationships (e.g. top mutated genes → druggable in graph).

## Quality conventions
- Ground every graph query in `get_hub_schema` results; never invent gene/drug/table names not returned by a tool.
- For "read-only" endpoints, only SELECT/MATCH-style reads are permitted (the server rejects writes).

## Final step (REQUIRED) — score and report grounding + faithfulness
Do this **LAST**, only after the ENTIRE answer is written — every fact tagged AND all caveats/notes
included (the trailing `[Model knowledge]` caveat is a common LAST edit — it MUST be in the text you
score). Do NOT compute numbers in your head or from a draft. Procedure:

1. Finish the complete final answer first.
2. Paste your **complete, final** answer **verbatim** into `ANSWER` and run it with the **Run Python**
   code-execution tool (sandboxed, offline). Delimiter safety: use `r'''…'''`; if your answer contains
   `'''`, switch to `r"""…"""`; if it contains both, join string pieces with `+` — never edit the
   answer to fit the delimiter.

```python
import re, json, hashlib
VALID = {"quick": {"kb","graph","lake","roda","ols","compute","model","recalled"}}   # connected tools
def _tt(t):
    t = t.lower()
    if "model knowledge" in t: return "model"
    if t.startswith("compute") or t.startswith("code"): return "compute"
    for p in ("recalled","lake","graph","ols","kb","roda","web"):
        if t.startswith(p): return p
    return "primekg-flat" if "primekg" in t else "other"
def score(ans, inv="quick"):
    ty = [_tt(t) for t in re.findall(r"\[([^\]]+)\]", ans or "")]
    ty = [t for t in ty if t in {"model","recalled","lake","graph","ols","kb","roda","primekg-flat","web","compute"}]
    if not ty: return {"grounding_rate": None, "provenance_faithfulness": None, "n_tags": 0, "note": "unauditable"}
    valid = VALID.get(inv, {"model"})
    fab  = [t for t in ty if t not in valid]
    tool = [t for t in ty if t not in ("model","recalled")]
    return {"grounding_rate": round(len(tool)/len(ty),3),
            "provenance_faithfulness": round(1-len(fab)/len(ty),3),
            "n_tags": len(ty), "fabricated": sorted(set(fab))}
ANSWER = r'''<paste your COMPLETE final answer here, verbatim, including all caveats>'''
res = score(ANSWER, "quick")
res["tag_census"]  = re.findall(r"\[([^\]]+)\]", ANSWER)          # every bracket tag, in order (audit)
res["answer_sha12"] = hashlib.sha1(ANSWER.encode()).hexdigest()[:12]
res["answer_tail"]  = ANSWER[-160:]                               # confirm the FINAL text was scored
print(json.dumps(res, indent=2))
```

3. **Paste the raw JSON the snippet printed** (it must appear in your message BEFORE the grounding line).
   Self-check against that JSON before writing the line:
   - `answer_tail` ends with your answer's actual last sentence (proves you scored the FINAL text, incl. the caveat);
   - every tag in `tag_census` appears verbatim in your answer, and there are none you didn't write;
   - the numbers you report are **character-for-character** the printed `grounding_rate` / `provenance_faithfulness` (3 decimals).
4. End with this exact line, numbers copied verbatim from the JSON:

> **Grounding:** grounding_rate=<x> · provenance_faithfulness=<y> (inventory=quick)

**Hard rules:** never report a grounding number you did not just print. If you add/remove/edit ANY tagged
sentence after running, run again and use the new JSON. If `grounding_rate` is `null` (unauditable), your
answer has no tags — go add them and re-run; do not invent a number. If the code-execution tool is
unavailable, **omit the grounding line entirely** (do NOT self-report a number).

Definitions: `grounding_rate` = tool tags (`[Graph]/[Lake]/[OLS]/[KB]/[RODA]/[Web]/[Compute]`) ÷ all tags;
`provenance_faithfulness` = 1 − fabricated ÷ all tags. Mirrors
`grounding-faithfulness-eval/scripts/score_provenance.py` (same algorithm). The authoritative value is a
post-hoc run of that scorer over your emitted answer — the inline number must match it.
