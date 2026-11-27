# Oncology Semantic Hub — Amazon Quick Setup

Connect the Oncology Semantic Hub to your **Amazon Quick** environment and run the demo. This uses an
**already-deployed** set of MCP servers — you don't deploy anything.

Two HTTP MCP servers (`oncology-hub-data`, `ontology-lookup-service`) share one Cognito token; a third
(`bedrock-kb-retrieval`) runs locally over stdio with your AWS credentials.

## Prerequisites

- AWS credentials in the deployment account (`us-west-2`) with **`ssm:GetParameter`** on
  `/app/ontology-lookup-service/agentcore/*` and `/app/oncology-hub-data/agentcore/*`.
- You do **not** need any AWS data permissions (Neptune/Athena) — the server's execution role does the
  data access; you only present a JWT.
- `uvx` (from [uv](https://docs.astral.sh/uv/)) for the local KB server, and `python3` + `curl` for token minting.

---

## Step 1 — Mint a token + get the data-server URL

```bash
cd mcp-servers/agentcore-runtime/oncology-hub-data
source get-token.sh
```

This exports `HUB_MCP_URL` and `HUB_MCP_TOKEN` (~60-min TTL). For hands-off renewal instead of re-minting
manually, run `./refresh-token.sh` (re-mints every ~50 min).

## Step 2 — Get the OLS server URL

Same token works (shared Cognito):

```bash
aws ssm get-parameter --region us-west-2 \
  --name /app/ontology-lookup-service/agentcore/mcp_url \
  --query Parameter.Value --output text
```

## Step 3 — Add three MCP servers in Quick

In Quick → **Settings > Capabilities > Add MCP Server**:

| Name | Transport | URL / Command | Auth |
|---|---|---|---|
| `oncology-hub-data` | HTTP | `$HUB_MCP_URL` (step 1) | header `Authorization: Bearer <HUB_MCP_TOKEN>` |
| `ontology-lookup-service` | HTTP | OLS url (step 2) | header `Authorization: Bearer <HUB_MCP_TOKEN>` (same token) |
| `bedrock-kb-retrieval` | stdio | `uvx awslabs.bedrock-kb-retrieval-mcp-server@latest` | env `AWS_REGION=us-west-2`, `KB_INCLUSION_TAG_KEY=mcp-multirag-kb` |

**Server descriptions** (for the Quick description field):

- **oncology-hub-data** — Read-only query tools for the Oncology Semantic Hub: patient/molecular data
  (Athena), the biomedical knowledge graph (Neptune), variant annotations (ClinVar/CIViC), and live schema.
- **ontology-lookup-service** — Resolves disease/gene/phenotype terms to standard ontology IDs
  (MONDO, HPO, and 200+ others) via EBI OLS.
- **bedrock-kb-retrieval** — Semantic search over the oncology literature/evidence knowledge base
  (Bedrock Knowledge Base).

## Step 4 — Install the skill

Agents & skills → Skills → **Import** `skills/oncology-semantic-hub-analysis/SKILL.md`. The skill teaches
the agent how to compose across the three servers and how to score its own grounding/faithfulness.

## Step 5 — Ask a scientific question

Start a fresh conversation, then ask one of the demo questions below.

---

## Demo questions

Pure scientific phrasing — no tool/method hints; the agent chooses the path. In Quick (all tools + Code
Execution) the standouts are **Q5** and **Q3** (both compute a real p-value).

**Q1 — Correctness**
> In our TCGA-GBM cohort, how many distinct genes are mutated? And separately, how many genes are known to be associated with glioblastoma as a disease? Give both numbers.

**Q2 — Reproducibility**
> How many distinct genes are associated with the type of cancer studied in the TCGA-GBM cohort?

**Q3 — Groundedness (computed p-value)**
> Is the co-occurrence of EGFR and PTEN mutations in TCGA-GBM statistically significant? Give the p-value.

**Q4 — Multi-hop orchestration**
> EGFR is a key driver in glioblastoma. Which signaling pathways is EGFR part of, which OTHER genes in those pathways are also mutated in our TCGA-GBM cohort, and are any of them druggable? Cite sources.

**Q5 — Full-hub + computed test (flagship)**
> In glioblastoma, are EGFR and PTEN mutations mutually exclusive or do they tend to co-occur across the TCGA-GBM patient cohort — and is that association statistically significant? Are the two genes in the same signaling pathway, and what are the treatment implications?

**Expected on the grounded path (Q5):** cohort n=371 (EGFR 82, PTEN 116, both 30), Fisher's exact
OR≈1.36, **p≈0.28 (not significant)**, glioblastoma→MONDO:0018177, EGFR/PTEN share PI3K/AKT, plus CIViC
actionability with PMIDs. A bare LLM fabricates the p-value (and gets it wrong) — the hub computes it from
your actual cohort data.

Full demo narrative and expected results: `docs/demo-golden-thread-v4.md`.

---

## Troubleshooting

- **Calls start failing after ~an hour** → the token expired. Re-run `source get-token.sh` (or keep
  `./refresh-token.sh` running) and update the Bearer header in Quick.
- **`[ERR] Could not read Cognito params from SSM`** → check `aws sts get-caller-identity` works, region
  is `us-west-2`, and you have `ssm:GetParameter`.
- **`mcp_url` not found** → the `oncology-hub-data` server isn't deployed in this account/region; see
  `mcp-servers/agentcore-runtime/oncology-hub-data/README.md` to deploy it.
