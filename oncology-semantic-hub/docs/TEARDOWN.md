# Teardown — destroying Oncology Semantic Hub resources

The hub deploys real, billable AWS resources. **Orphaned infrastructure costs money** — the Neptune
Analytics graph (m-NCU, the dominant steady-state cost) and the Bedrock Knowledge Base keep billing
whether or not anyone queries them. This runbook destroys everything the accelerator creates, in
dependency order.

> Set the same environment the pipeline used before running anything here:
> ```bash
> export SEMHUB_ACCOUNT_ID=<account>   SEMHUB_REGION=us-west-2
> export SEMHUB_GRAPH_ID=g-xxxxxxxxxx  SEMHUB_ATHENA_DB=oncology_semantic_hub
> ```
> Prefer ReadOnly/least-privilege credentials for the `--list` previews; use write-capable
> credentials only for the actual deletes.

## What gets created (the full billable footprint)

| # | Resource | Created by | Cost driver |
|---|---|---|---|
| 1 | AgentCore Runtime(s) — one per deployed layer | `agentcore/deploy.py` | per-runtime; idle-cheap but not free |
| 2 | IAM execution role + inline policy (per runtime) | `agentcore/deploy.py` | none (hygiene) |
| 3 | Lake Formation grants to those roles | `agentcore/deploy.py` | none (hygiene) |
| 4 | S3 code bucket `bedrock-agentcore-code-<acct>-<region>` + zip objects | `agentcore/deploy.py` | per-GB (small) |
| 5 | Bedrock Knowledge Base + S3 Vectors + corpus bucket + IAM | `agentcore/kb/create_kb.py` | **vector storage (ongoing)** |
| 6 | Neptune Analytics graph | `scripts/08_neptune_bulk_import.py` | **m-NCU (ongoing, dominant)** |
| 7 | Glue databases + tables; Glue crawler | `scripts/07_create_athena_tables.py` | catalog storage (trivial) |
| 8 | Data-lake S3 `oncology-semantic-hub-data-<acct>-<region>` (lake/ + athena-results/) | `scripts/` | per-GB |
| 9 | SSM parameters (`/app/oncology-hub/...`) | `kb/create_kb.py` | none |

> The **OLS MCP server** and its Cognito stack are a **separate component** (not owned by this repo);
> tear it down from its own project.

## Order of teardown

Reverse of deploy: agents (consume the data plane) → Knowledge Base → Neptune → Glue/Athena → S3 → SSM.

### 1. Agents — runtimes, roles, code objects

Reverses `deploy.py`, reading `agent_config*.json` so it deletes only what was deployed.

```bash
python agentcore/cleanup.py                               # preview — deletes nothing
python agentcore/cleanup.py --all                         # delete every deployed layer's runtime + role + code object
python agentcore/cleanup.py --all --delete-code-bucket    # also empty + delete the shared code bucket
# or a single layer:
python agentcore/cleanup.py --layer L3
```

The config JSONs are left as a record; delete them by hand once teardown is confirmed. (They are
gitignored, so they never shipped.)

> ⚠️ **Known gap:** redeploying the *same* layer (e.g. `--layer L0` twice) overwrites the same
> `agent_config_l0.json`, so the **first** run's runtime + role becomes invisible to `cleanup.py` —
> it only reads the current file. If you redeployed a layer more than once, cross-check
> `aws bedrock-agentcore-control list-agent-runtimes` for any `oncology_semantic_hub_*` runtime
> `cleanup.py` didn't report, and delete it (+ its role) the same way by hand.

### 2. Knowledge Base — KB, S3 Vectors, IAM, SSM

```bash
python agentcore/kb/create_kb.py --delete
```

Deletes the KB, its vector index, and the IAM it created, and removes the `kb_id`/`ds_id` SSM
parameters. **Note:** it intentionally leaves the corpus S3 bucket intact — delete it in step 5.

### 3. Neptune Analytics graph (dominant cost — do not skip)

No repo script deletes the graph (deletion is destructive and irreversible). Delete it explicitly:

```bash
aws neptune-graph delete-graph --graph-identifier "$SEMHUB_GRAPH_ID" --region "$SEMHUB_REGION"
# confirm it is gone:
aws neptune-graph list-graphs --region "$SEMHUB_REGION"
```

> ⚠️ This permanently destroys the loaded graph (PrimeKG + TCGA nodes + enrichments). It can be
> rebuilt from `scripts/` but the rebuild takes time and re-incurs extraction cost.

### 4. Glue databases, tables, and crawler

```bash
for DB in oncology_semantic_hub oncology_semantic_hub_roda oncology_semantic_hub_raw; do
  aws glue delete-database --name "$DB" --region "$SEMHUB_REGION" 2>/dev/null \
    && echo "deleted $DB" || echo "$DB absent"
done
aws glue delete-crawler --name "${SEMHUB_CRAWLER:-oncology-hub-crawler}" --region "$SEMHUB_REGION" 2>/dev/null || true
```

Deleting a Glue database drops its tables with it. (The `oncology_semantic_hub_healthomics` DB is a
phase-3 experiment artifact, not part of this PR — delete it too only if it exists in your account.)

### 5. S3 buckets — data lake, Athena results, KB corpus

```bash
DATA_BUCKET="oncology-semantic-hub-data-${SEMHUB_ACCOUNT_ID}-${SEMHUB_REGION}"
KB_BUCKET="oncology-semantic-hub-kb-corpus-${SEMHUB_ACCOUNT_ID}-${SEMHUB_REGION}"
for B in "$DATA_BUCKET" "$KB_BUCKET"; do
  aws s3 rm "s3://$B" --recursive --region "$SEMHUB_REGION" 2>/dev/null || true
  aws s3api delete-bucket --bucket "$B" --region "$SEMHUB_REGION" 2>/dev/null \
    && echo "deleted $B" || echo "$B absent"
done
```

> ⚠️ `s3 rm --recursive` is irreversible. Confirm the bucket names resolve to **this** project before
> running, and check for versioned objects / retention locks if your account enables them.

### 6. Residual SSM parameters

```bash
aws ssm get-parameters-by-path --path /app/oncology-hub --recursive \
  --region "$SEMHUB_REGION" --query 'Parameters[].Name' --output text
# delete any that remain:
# aws ssm delete-parameter --name <name> --region "$SEMHUB_REGION"
```

## Verify nothing is left billing

```bash
aws neptune-graph list-graphs --region "$SEMHUB_REGION"                    # expect: none for this hub
aws bedrock-agentcore-control list-agent-runtimes --region "$SEMHUB_REGION" | grep oncology || echo "no runtimes"
aws s3 ls | grep -E "oncology-semantic-hub|bedrock-agentcore-code" || echo "no buckets"
```

If all three are empty, the hub incurs no further charges.
