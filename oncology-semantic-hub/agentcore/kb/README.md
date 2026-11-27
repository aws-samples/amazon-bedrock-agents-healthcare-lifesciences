# Hybrid-search knowledge base (`agentcore/kb/`)

Reusable, checked-in code that gives the L3 agent **hybrid search**: semantic **recall** over
unstructured text (TCGA study descriptions + curated PubMed abstracts) → **OLS** entity resolution →
**graph + SQL** precision → an answer that **cites the evidence**. Design + decisions:
[`../../docs/hybrid-search-design.md`](../../docs/hybrid-search-design.md).

The vector layer is a **customer-managed Amazon Bedrock Knowledge Base on S3 Vectors** (serverless — no
OpenSearch) with **Titan Text Embeddings v2** (1024-dim, cosine). The L3 agent calls it as the
`knowledge_search` tool via the `bedrock-agent-runtime:Retrieve` API (no AgentCore Gateway).

## Files
| File | What it does |
|---|---|
| `build_corpus.py` | Fetch all 33 TCGA project descriptions (GDC API) + ~50–60 PubMed abstracts (NCBI E-utilities) → local `corpus/` as `<doc>.txt` + `<doc>.txt.metadata.json` sidecars. Stdlib only. |
| `knowledge_base.py` | Helper (adapted from `agentcore_template/prerequisite/knowledge_base.py`): create/retrieve the KB (S3 Vectors + Titan v2), IAM role/policies, ingest, delete. Idempotent. |
| `create_kb.py` | Driver: create/retrieve KB, upload the corpus to a dedicated bucket, run ingestion, store `kb_id`/`ds_id` in SSM. `--delete` tears it all down. |
| `hybrid_check.py` | Re-runnable verification against the deployed L3: recall quality, study discovery, and **no fabricated citations** (cited PMIDs must be real corpus docs *and* grounded in KB recall). |
| `corpus/` | Generated documents + metadata — **gitignored** (rebuild with `build_corpus.py`). |

## Build / create / verify
```bash
# 1. Build the corpus (writes agentcore/kb/corpus/)
./.venv/bin/python agentcore/kb/build_corpus.py            # 33 TCGA + ~60 PubMed docs

# 2. Create the KB, upload, ingest, store kb_id in SSM
./.venv/bin/python agentcore/kb/create_kb.py

# 3. Wire the tool into L3 and redeploy (adds knowledge_search + bedrock:Retrieve)
./.venv/bin/python agentcore/deploy.py --layer L3

# 4. Verify the live hybrid flow (grounding + no fabrication)
./.venv/bin/python agentcore/kb/hybrid_check.py

# Teardown (KB + S3 Vectors + IAM; leaves the corpus S3 bucket)
./.venv/bin/python agentcore/kb/create_kb.py --delete
```

## How the agent uses it
`agentcore/semantic_hub_agent.py` exposes `knowledge_search(query, source="", min_year=0, disease="",
max_results=5)`:
- resolves the KB id from SSM `/app/oncology-hub/knowledge_base/kb_id` (override with env `SEMHUB_KB_ID`),
- calls `Retrieve` with an optional metadata filter — `source` (`PubMed`|`TCGA`) and `min_year` are true
  metadata filters; `disease` is appended to the semantic query (the `disease` attribute is TCGA-only, and
  PubMed abstracts encode disease in text, so a hard equals filter would wrongly drop literature),
- returns passages with **structured citations** (PubMed → `… — PMID:xxxxx`; TCGA → `TCGA-XXX project`),
- the L3 prompt then chains recall → `ontology_lookup` (OLS) → `query_knowledge_graph` / `query_patient_data`,
  and **cites only sources returned by `knowledge_search`** (never invents a PMID).

## Resources (region + account are your own; set via SEMHUB_* env vars)
- KB `oncology-semantic-hub-kb` (id in SSM) · S3 Vectors bucket `…-kb-vec-v1` / index `…-kb-idx-v1`
- Corpus S3 bucket `oncology-semantic-hub-kb-corpus-<acct>-<region>` (public access blocked)
- SSM `/app/oncology-hub/knowledge_base/kb_id` and `/ds_id`

## Notes
- **One-time ingest** (v1): re-run `create_kb.py` to re-sync after changing the corpus (no scheduled refresh).
- **BYOD:** point the corpus at your own `.txt` + `.metadata.json` files and re-run — the rest is unchanged.
- Sources are **public** (TCGA/GDC + PubMed); PubMed fetch identifies the tool with a placeholder contact.
