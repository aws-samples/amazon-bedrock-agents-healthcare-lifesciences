# Bedrock Knowledge Base Retrieval — local MCP server (no deploy)

Provides the **`knowledge_search`** capability (semantic recall over the hub's literature corpus — TCGA
study descriptions + curated PubMed abstracts) to any MCP client, **reproducing the L3 agent's KB tool**.
This is the one L3 tool not on the deployed `oncology-hub-data` runtime MCP server: by decision, KB stays
a **local** MCP server run by the consuming harness (e.g. Amazon Quick), using the user's local AWS
credentials — we don't re-deploy a KB service. (A remote KB-retrieval MCP on AgentCore Runtime is deferred.)

Category: `aws-public` (pre-existing AWS Labs server, run locally via `uvx` — no deployment).

## The hub Knowledge Base
The hub's Bedrock KB id is stored in SSM:

```bash
aws ssm get-parameter --name /app/oncology-hub/knowledge_base/kb_id \
  --query Parameter.Value --output text --region us-west-2
```

The [AWS Labs `bedrock-kb-retrieval-mcp-server`](https://github.com/awslabs/mcp) discovers Knowledge Bases
by an **inclusion tag** (default key `mcp-multirag-kb`). Tag the hub KB once so the server exposes it:

```bash
KB_ID=$(aws ssm get-parameter --name /app/oncology-hub/knowledge_base/kb_id --query Parameter.Value --output text --region us-west-2)
aws bedrock-agent tag-resource --region us-west-2 \
  --resource-arn "arn:aws:bedrock:us-west-2:<ACCOUNT_ID>:knowledge-base/${KB_ID}" \
  --tags '{"mcp-multirag-kb":"true"}'
```

> Verify the exact package name, env vars, and KB-selection mechanism against the current AWS Labs MCP
> server docs before the demo — the tag key/behavior can change between versions.

## Required IAM (consumer-side, local credentials)
`bedrock:Retrieve` on the KB, plus `bedrock:InvokeModel` for the embedding model used by the KB, and
`bedrock-agent:ListKnowledgeBases` / `bedrock-agent:GetKnowledgeBase` (+ `ListTagsForResource`) for
tag-based discovery.

## Connect in Amazon Quick
**Settings > Capabilities > Add MCP Server** → type `stdio`, command `uvx awslabs.bedrock-kb-retrieval-mcp-server@latest`,
env `AWS_REGION=us-west-2`, `KB_INCLUSION_TAG_KEY=mcp-multirag-kb`. Alongside the two remote HTTP MCP servers
(`oncology-hub-data`, `ontology-lookup-service`) this completes the L3 tool set:
`knowledge_search` (here) · `query_knowledge_graph`/`query_patient_data`/`query_variant_annotation`/`get_hub_schema`
(oncology-hub-data) · `ontology_lookup` (OLS).

## Tools (typical)
- `QueryKnowledgeBases` — semantic retrieve over the tagged KB(s). Map its results to the `[KB PMID:...]` /
  `[KB TCGA-XXX]` provenance tags per the `oncology-semantic-hub-analysis` skill.
