# Oncology Semantic Hub — Data MCP Server (AgentCore Runtime)

Read-only **Neptune + Athena** tools for the Oncology Semantic Hub, deployed as an MCP endpoint on
Amazon Bedrock AgentCore Runtime. Any MCP client (Amazon Quick, Claude Code, Kiro, a custom agent) can
query the hub over HTTPS + JWT with **no local AWS credentials**. Query + schema logic is shared with
the benchmark agent via `oncology_semantic_hub/hub_core/` (single source of truth); read-only is enforced
by in-process guards + least-privilege IAM.

## Tools
| Tool | What | Provenance tag |
|------|------|----------------|
| `get_hub_schema` | LIVE graph labels/props + Athena tables (incl. onboarded `*_staging`) + curated hints | (structural) |
| `query_knowledge_graph` | read-only openCypher on Neptune Analytics | `[Graph]` |
| `query_patient_data` | read-only SQL on the TCGA lake (Athena) | `[Lake:<table>]` |
| `query_variant_annotation` | read-only SQL on RODA tables (CIViC/ClinVar + onboarded) | `[RODA:<table>]` |

`knowledge_search` (Bedrock KB) and `ontology_lookup` (OLS) are **separate** MCP servers — see
`mcp-servers/aws-public/bedrock-kb-retrieval/` and `mcp-servers/agentcore-runtime/ontology-lookup-service/`.

## Prerequisites
- The hub is built (Neptune Analytics graph + Athena databases `oncology_semantic_hub` / `_roda`).
- **Deploy the OLS Runtime MCP server first** (`../ontology-lookup-service`) — this server **reuses its
  Cognito** for the CUSTOM_JWT authorizer (reads `/app/ontology-lookup-service/agentcore/*` SSM). It creates
  no Cognito of its own; `deploy.py` fails fast if those params are absent.
- Python 3.13 + `uv` (or pip), AWS creds with the deploy permissions below.

## Deploy
```bash
SEMHUB_GRAPH_ID=<neptune-analytics-graph-id> python deploy.py --region us-west-2
```
`deploy.py` (boto3, no Docker): read-only IAM role (Neptune `ReadDataViaQuery`/`GetGraph`/`GetGraphSummary`,
Athena, Glue read, S3 results, logs) + **Lake Formation** DESCRIBE/SELECT grants on both databases (a fresh
role has none — else Athena fails silently) + bundles `hub_core` + `create_agent_runtime(serverProtocol=MCP,
customJWTAuthorizer=OLS Cognito, env=SEMHUB_*)`. Writes `/app/oncology-hub-data/agentcore/{mcp_url,agent_arn,
agent_id}` to SSM and `runtime_config.json`.

## Use an existing deployment in Amazon Quick (consumers — no deploy)

If an admin has already deployed these servers, anyone can connect from **their own** Amazon Quick with
just a token — **no AWS data permissions needed** (the server's execution role does the Neptune/Athena
access; you only present a JWT).

**Prerequisite:** AWS credentials in the deployment account with `ssm:GetParameter` on
`/app/ontology-lookup-service/agentcore/*` and `/app/oncology-hub-data/agentcore/*` (used to read the
endpoint URLs and mint the token). *Or* have the admin hand you the `mcp_url`s + a bearer token directly.

**Steps:**
1. Get a token + the data-server URL (from this folder):
   ```bash
   source get-token.sh
   # prints HUB_MCP_URL and sets HUB_MCP_TOKEN  (~60-min TTL; run ./refresh-token.sh to auto-renew)
   ```
2. Get the OLS server URL (same token works — shared Cognito):
   ```bash
   aws ssm get-parameter --region us-west-2 \
     --name /app/ontology-lookup-service/agentcore/mcp_url --query Parameter.Value --output text
   ```
3. In Quick → **Settings > Capabilities > Add MCP Server**, add three:
   | Name | Transport | URL / Command | Auth |
   |---|---|---|---|
   | `oncology-hub-data` | HTTP | `$HUB_MCP_URL` | header `Authorization: Bearer <HUB_MCP_TOKEN>` |
   | `ontology-lookup-service` | HTTP | (OLS url from step 2) | header `Authorization: Bearer <HUB_MCP_TOKEN>` (same token) |
   | `bedrock-kb-retrieval` | stdio | `uvx awslabs.bedrock-kb-retrieval-mcp-server@latest` | env `AWS_REGION=us-west-2`, `KB_INCLUSION_TAG_KEY=mcp-multirag-kb` (uses your local AWS creds; see `mcp-servers/aws-public/bedrock-kb-retrieval/`) |
4. Install the **`oncology-semantic-hub-analysis`** skill (Agents & skills → Skills → Import from file → its `SKILL.md`). It self-contains the grounding/faithfulness scorer.
5. Ask a scientific question (e.g. the EGFR-GBM thread in `docs/demo-golden-thread-v4.md`). If calls start
   failing after ~an hour, the token expired — re-run `source get-token.sh` (or keep `./refresh-token.sh` running).

## Connect (other harnesses)

## Validate
```bash
source get-token.sh
# initialize -> tools/list (4 tools) -> tools/call query_knowledge_graph "MATCH (n) RETURN count(n)"
# expect a live count; a write Cypher / non-SELECT SQL returns "Rejected (read-only endpoint): ...".
```

## Files
`mcp_server.py` (FastMCP, 4 tools, read-only guards) · `deploy.py` · `get-token.sh` · `refresh-token.sh` ·
`cleanup.py` · `requirements.txt` (`mcp>=1.23,<2.0` — 2.0 moved `mcp.server.fastmcp`).

## Cleanup
```bash
python cleanup.py    # deletes the runtime + endpoint, IAM role/policy, and this server's SSM params
```
Does NOT touch the OLS Cognito (owned by the OLS component).
