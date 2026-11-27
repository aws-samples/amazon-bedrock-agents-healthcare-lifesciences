# Pre-PR review — Oncology Semantic Hub (decoupling + docs/quality)

Reviewing the current working-tree state of `oncology_semantic_hub/` as the proposed PR (the whole
subproject is untracked in the monorepo — `git ls-files` returns 0 tracked files — so "the PR" is
everything that would be added, respecting `.gitignore`). Audience: external customer engineers of a
public `aws-samples` accelerator. Scope: decoupling of skills / agents / MCP servers / data, plus
documentation and code-quality against the supplied rubric.

The runtime decoupling story is real and well-executed in code: the agent is env-gated and
schema-discovery-first, `dataset_onboarding/` is genuinely non-coupled, and the shared query core
removes drift. The blockers are all in **documentation completeness** (no teardown, no cost analysis,
no ADRs) and one **doc-vs-code architecture mismatch** in the BYOD doc. There is also a real but
contained **portability bug** in the ETL scripts that undercuts the "config-only" BYOD claim for the
pipeline.

**Watch for:**
- No teardown documentation anywhere — AgentCore runtimes, IAM roles, Neptune Analytics graph,
  Athena/Glue, S3, and the Bedrock KB all cost money and have no documented destroy path (blocker, confirmed).
- `docs/bring-your-own-data.md` describes a *different architecture* than ships — AWS Labs
  `amazon-neptune` / `aws-dataprocessing` MCP servers, `NEPTUNE_ENDPOINT`, `get_graph_schema()` /
  `list-table-metadata`, and "skills" — none of which exist in the code (should-fix, confirmed).
- ~11 `scripts/` ETL steps hardcode `REGION = "us-west-2"` as a module constant while importing
  `_config` for everything else, so `SEMHUB_REGION` does not actually move the pipeline off us-west-2
  (should-fix, confirmed).
- No cost analysis doc and no ADR directory; the only cost figure is "~$70/month steady-state" in two
  docs (should-fix, confirmed).

**Verdict:** NEEDS_CHANGES — fix the blocker (teardown) and the BYOD doc-vs-code mismatch before
submitting; the decoupling claims themselves hold up in code.

## High-level view

The agent is a single env-gated file (`agentcore/semantic_hub_agent.py`). Layer selection (`SEMHUB_LAYER`
L0–L3 + ablations) is the only switch that changes the tool list and prompt; everything else — region,
graph id, Athena databases, Athena output, model id, KB id — is read from environment with safe
placeholder defaults. There is no hardcoded account, no hardcoded graph id, no embedded ARN in any
committable source. This is the central decoupling claim and it is true.

Tool wiring is schema-discovery-first exactly as the design docs claim. `get_hub_schema` resolves to
`hub_core/schema.py`, which introspects Glue (`get_tables`) and Neptune (`GetGraphSummary`) live, so a
newly onboarded `*_staging` table surfaces with no code change. The data tools are generic
(`query_knowledge_graph`, `query_patient_data`, `query_variant_annotation`) — parameterized Cypher/SQL
executors, not per-dataset tools. The shared `hub_core/queries.py` is the single implementation the
agent uses, which is what the remote-MCP design doc intended as its refactor foundation.

`dataset_onboarding/` is genuinely self-contained: no Python import reaches back into
`semantic_hub_agent.py` or `agentcore/`. Its only coupling to the agent is at runtime — it reads the
generated `agent_config.json` to invoke the deployed L3 over the network, with a self-contained SQL
fallback when L3 is unreachable. Its footprint on the hub is additive lake tables, matching
`docs/skill-design-roda-onboarding.md`'s "generic-wrapper" principle.

The MCP picture needs care because two different "MCP" things appear. The onboarding pipeline *does*
use a live MCP client (`awslabs.roda-mcp-server` over stdio) for dataset discovery, with a graceful
fallback to a curated catalog. The *remote* MCP server that would wrap the hub's Neptune/Athena tools
is design-only and correctly labeled `Status: PLAN` in `docs/remote-mcp-server-design.md` — it is not
in the code, and nothing claims it is. The problem is a third doc (`bring-your-own-data.md`) that
describes the BYOD path in terms of AWS Labs MCP servers and "skills" that the shipped agent does not
use.

Documentation answers "what is this?", "how do I run it?", and "why" reasonably well across the README,
`agentcore/README.md`, `scripts/README.md`, and the benchmark report. It does **not** answer "how do I
tear this down?" at all, and the "why" rationale is scattered through design/status docs rather than
captured as decision records. Cost is a single steady-state number, not a pilot/production/10x analysis.

<details>
<summary>Issues (9)</summary>

1. **No teardown documentation** (blocker) — add a teardown runbook (and ideally a `cleanup` script) covering AgentCore runtimes + their IAM roles, the Neptune graph, Athena/Glue databases, the `bedrock-agentcore-code-*` and data S3 buckets, and the Bedrock KB. Orphaned Neptune Analytics NCUs alone are the bulk of the ~$70/month.
2. **BYOD doc describes a non-shipped architecture** (should-fix) — `docs/bring-your-own-data.md` cites `amazon-neptune`/`aws-dataprocessing` MCP servers, `NEPTUNE_ENDPOINT`, `get_graph_schema()`/`list-table-metadata`, and "skills" that do not exist in code. Rewrite to match the shipped agent (direct-boto3 Strands tools, `get_hub_schema`, `SEMHUB_*` env vars) or clearly mark the MCP/skills framing as a target-state alternative.
3. **Hardcoded region in ~11 ETL scripts** (should-fix) — `scripts/{05,06,09,10,11,12,14}_*.py`, `scripts/build_l2_raw_lake.py`, and `scripts/roda/{load_civic,load_genoxus,graph_extension}.py` set `REGION = "us-west-2"` as a module constant despite importing `_config`. Use `C.REGION`. This undercuts the BYOD "config-only" claim for the pipeline.
4. **No cost analysis** (should-fix) — add `docs/COST_ANALYSIS.md` with pilot/production/10x scale estimates, per-service breakdown with cost drivers, documented assumptions, and scale trade-offs. Promote the ~$70/month figure into the pilot row.
5. **No ADRs** (nice-to-have, borderline should-fix for an accelerator) — the "why" (Neptune Analytics vs Neptune DB, graph-vs-flat L2/L3 split, schema-discovery-first, additive-staging onboarding, in-process tools vs remote MCP) lives in design/status docs. Promote these decisions into `docs/adr/`.
6. **Hardcoded Glue DB in `09_validate.py`** (nice-to-have) — `GLUE_DB = 'oncology_semantic_hub'` (line 9) should be `C.ATHENA_DB` for consistency with the env-driven config.
7. **Root README deploy block omits config prerequisites** (should-fix) — the top-level `README.md` "Deploy" section jumps to `deploy.py --layer L3` without the `SEMHUB_*` env setup or the data-pipeline prerequisite; a first-time reader following only the README cannot reach "it's running." `agentcore/README.md` has the prerequisites — cross-link them.
8. **Note the gitignored deploy config in the README** (nice-to-have) — add a line that `deploy.py` writes a gitignored `agent_config*.json` containing account-specific ARNs, so readers understand why it isn't checked in and don't commit it.
9. **Architecture diagram updated and re-verified** (resolved) — `images/Research_agent_accelerators_oncology/system-architecture-observability.png` now wired into the main README and `docs/README.md`; it shows the shipped in-process boto3 tools (not the design-only remote MCP server). The target-state MCP/skills diagram (`overview.png`) is placed in `remote-mcp-server-design.md`, explicitly labeled target-state, so it no longer implies current state.

</details>

<details>
<summary>Details</summary>

### Env-driven decoupling holds across every runtime component

The claim that configuration is env-driven with no hardcoded account/region is accurate for everything
that runs or deploys:

- `scripts/_config.py` is the model: every value from `SEMHUB_*`, `require()` fails loudly with setup
  guidance, bucket derived from account+region, nothing account-specific baked in.
- `agentcore/semantic_hub_agent.py:30-45` reads `SEMHUB_REGION`, `SEMHUB_GRAPH_ID`, `SEMHUB_ATHENA_DB`,
  `SEMHUB_RODA_DB`, `SEMHUB_RAW_DB`, `SEMHUB_SUBJECT_MODEL`, `SEMHUB_OLS_SSM_PREFIX`, `SEMHUB_KB_ID`
  from the environment. `GRAPH_ID` defaults to empty and is injected at deploy time.
- `hub_core/schema.py:24-30` and `hub_core/queries.py:22-27` read the same env vars — one config
  surface, no drift.
- `agentcore/deploy.py` derives the account from `sts:GetCallerIdentity` (line 44) and region from the
  CLI arg / `Session().region_name` (line 30), never a literal. It *requires* `SEMHUB_GRAPH_ID` for L3
  (lines 196-199, fails loudly) and injects `SEMHUB_REGION` / `SEMHUB_ATHENA_OUTPUT` / `SEMHUB_GRAPH_ID`
  into the runtime environment (lines 200-215).

Grep across the committable set for `<ACCOUNT_ID>`, live `arn:aws:(iam|bedrock-agentcore)` ARNs,
`g-<10+>` graph ids, and `oncology-semantic-hub-data-<account>` bucket names returned **nothing** — all
such values live only in gitignored artifacts (`agentcore/agent_config*.json` is ignored with an
`!agent_config.example.json` exception; `dataset_onboarding/P1-STATUS.md` and siblings are ignored by
`dataset_onboarding/.gitignore`). The account id *is* present in those local files, but none of them
would be committed. This is exactly the right posture; the only improvement is a one-line note in the
README that `deploy.py` writes a gitignored config containing account-specific ARNs.

### Schema-discovery-first is implemented, not just claimed

`get_hub_schema` (`semantic_hub_agent.py:71-80`) delegates to `hub_core/schema.py:get_hub_schema`,
which builds the schema from live Glue `get_tables` across the hub databases
(`schema.py:_lake_schema`) and live Neptune `GetGraphSummary` (`schema.py:_graph_schema`), plus a small
curated semantics preamble. It degrades to a static snapshot only on introspection failure
(`semantic_hub_agent.py:76-79`). The data tools are generic executors over `hub_core/queries.py`
(`run_opencypher`, `run_athena_sql`), parameterized by database — not one tool per dataset. This
matches the "generate queries, don't memorize" / "list-table-metadata" intent in the design docs, so a
customer pointing `SEMHUB_GRAPH_ID` / `SEMHUB_ATHENA_DB` at their own resources gets a schema composed
from *their* catalog with no code change.

The one caveat worth a line in the agent docstring: `_databases()` (`schema.py:64-71`) excludes the raw
flat-PrimeKG DB by default and is overridable via `SEMHUB_SCHEMA_DBS`. That is a sensible L3-vs-L2
decision but it is config a BYOD customer should know exists.

### `dataset_onboarding/` is self-contained — verified

No import from `dataset_onboarding/**` reaches `semantic_hub_agent.py`, `agentcore/`, or `hub_core`
(grep returned nothing). The only backward reference is `onboard_runner.py:ask_l3` (around line 429)
reading `agentcore/agent_config.json` to invoke the deployed L3 runtime over boto3, with a
self-contained `ask_hub` SQL fallback when L3 is unreachable (`onboard_runner.py:447-451`). That is a
runtime/data integration, not code coupling — precisely what `dataset_onboarding/README.md` and
`docs/skill-design-roda-onboarding.md` claim. The external MCP discovery call
(`orchestration/roda_mcp.py`) wraps the AWS Labs RODA server over stdio and raises `RodaMCPError` so
callers fall back to the curated catalog — external boundary wrapped, failure doesn't vanish.

### The BYOD doc describes an architecture the code does not have

`docs/bring-your-own-data.md` is the one place where documented decoupling and shipped decoupling
diverge. It tells a customer the BYOD path is "config-only" by changing `NEPTUNE_ENDPOINT` / an Athena
DB env var on the **AWS Labs `amazon-neptune` and `aws-dataprocessing` MCP servers**, and that
"schema-discovery-first skills" call `get_graph_schema()` / `list-table-metadata`. None of those
names exist in the code:

- The shipped agent talks to Neptune/Athena with **direct boto3** via `hub_core/queries.py`, not the
  AWS Labs MCP servers.
- The schema tool is `get_hub_schema` (not `get_graph_schema` / `list-table-metadata`).
- Configuration is `SEMHUB_GRAPH_ID` / `SEMHUB_ATHENA_DB`, not `NEPTUNE_ENDPOINT`.
- There are no "skills" artifacts in this subproject; the Strands agent carries tools + a system
  prompt.

The underlying *claim* (point the same tools at your own resources via config) is true for the shipped
agent — but a customer engineer following this doc will look for MCP servers and skills that aren't
here and conclude the accelerator is incomplete. Either rewrite the doc against the shipped agent, or
state explicitly that the MCP-server/skill framing is a target state (it overlaps the design-only
`remote-mcp-server-design.md` and the Amazon Quick skill path), separate from what deploys today. Note
that `agentcore/README.md`'s own BYOD section is already correct (`SEMHUB_ATHENA_DB` / `SEMHUB_GRAPH_ID`
env swaps) — the two BYOD descriptions should be reconciled to that one.

### Teardown is absent — the one hard blocker

There is no teardown doc and no cleanup script (searched for cleanup/teardown/destroy across `*.md` and
the filesystem; the only hits are in archive/status docs and the venv). The deployed footprint that
costs money and must be destroyed by hand today: AgentCore runtimes (one per layer deployed) and their
per-runtime IAM roles + inline policies created by `deploy.py`, the Neptune Analytics graph (NCUs — the
dominant cost), the Glue databases/tables and Athena workgroup output, the
`bedrock-agentcore-code-<acct>-<region>` and data buckets, and the Bedrock Knowledge Base. For a public
accelerator aimed at customer engineers, "spin it up" without "tear it down" is the failure mode the
rubric calls out explicitly (orphaned infra costs money). `deploy.py` writes the runtime ARN and role
name into `agent_config*.json`, so a cleanup script has everything it needs to reverse itself — this is
very achievable, not just a doc gap.

### Error handling at external boundaries is mostly solid, with one asymmetry

External calls are wrapped and return safe messages rather than throwing into the agent loop:
`ontology_lookup` and `web_search` catch and return `"... failed: {e}"`; `knowledge_search` catches
retrieval errors; `get_hub_schema` degrades to a static snapshot; `chat_ui.invoke_runtime` retries with
backoff and returns a user-facing `⚠️` message after exhausting retries; `onboard_runner.ask_l3` falls
back to SQL. Async failures don't vanish — token-usage capture is best-effort with a logged warning
(`semantic_hub_agent.py:invoke`). The one asymmetry: `query_knowledge_graph` / `query_patient_data` /
`query_variant_annotation` call straight into `hub_core/queries.py` with **no try/except**, so a Neptune
or Athena client error (bad graph id, missing LF grant, malformed Cypher) propagates as a raw exception
rather than the safe, useful tool-error string the other tools return. `run_athena_sql` already returns
a readable string on query FAILED/CANCELLED, but connection/permission errors still raise. Wrapping
these three tools the way `knowledge_search` is wrapped would make the agent's behavior uniform and the
error messages customer-friendly. (should-fix, confirmed.)

### Cost and ADRs — rubric items with no artifact

The cost rubric wants pilot / production / 2x-10x scale, per-service drivers, documented assumptions,
and scale trade-offs. The repo has one number: "~$70/month steady-state" in `docs/bring-your-own-data.md`
and `docs/whitepaper-section-4.1-draft.md:194` (Neptune 32 m-NCU ≈ $65 + Athena pay-per-query). That is
a fine pilot anchor but not an analysis — notably it says nothing about the per-token Bedrock cost of
the agent itself (Claude Sonnet 4.5 across KB recall + multi-hop tool calls), which is the cost that
actually scales with usage, nor about AgentCore runtime, KB storage/queries, or S3/Glue at 10x. The
"why" rationale (graph vs flat, Neptune Analytics choice, schema-discovery design, additive-staging
onboarding, in-process tools vs remote MCP) is genuinely present and well-argued across
`remote-mcp-server-design.md`, `skill-design-roda-onboarding.md`, `phase3-*`, and the whitepaper draft —
it just isn't in decision-record form. Promoting ~5 ADRs would satisfy rubric item 7 cheaply from
material that already exists.

### Readability and tests

Readability is high: the agent and `hub_core` modules have purpose-stating docstrings, the env-var
contract is documented in `agentcore/README.md` and `.env.example`, and `scripts/README.md` resolves
the "file numbers ≠ run order" trap with an orchestrator. Tests run clean under the stated harness:
`hub_core/tests` (21), `dataset_onboarding/tests` (55 across files), and top-level `tests` (26) all pass
with `python -m unittest`. `dataset_onboarding` notably unit-tests the generated-sandbox-script safety
(injection via `repr()`), which is the right thing to test for an LLM-authored-ETL feature. Not tested
(acceptable, but worth noting): no test asserts the agent's env-gated tool list per layer, and the
hardcoded-region scripts have no portability test — a single test that imports a script module under a
non-default `SEMHUB_REGION` and asserts the client region would catch issue #3 and prevent regressions.

</details>

<details>
<summary>File map</summary>

- `README.md` — entry point; good purpose/results/structure, but Deploy section skips `SEMHUB_*` setup + pipeline prerequisite (issue #7).
- `agentcore/semantic_hub_agent.py` — env-gated L0–L3 agent; schema-discovery-first; generic tools. Three data tools lack try/except (error-handling asymmetry).
- `agentcore/deploy.py` — account via STS, region via arg/session, injects env into runtime, requires `SEMHUB_GRAPH_ID` for L3, writes gitignored config. Clean.
- `agentcore/chat_ui.py` — reads gitignored configs; retry/backoff + safe `⚠️` messages; region from config.
- `agentcore/README.md` — correct `SEMHUB_*` env table + BYOD env-swap steps (reconcile the BYOD doc to this).
- `hub_core/schema.py`, `hub_core/queries.py` — live introspection + single shared query core; env-driven.
- `scripts/_config.py` — single env-driven config source, fails loudly. Model component.
- `scripts/{05,06,09,10,11,12,14}_*.py`, `scripts/build_l2_raw_lake.py`, `scripts/roda/{load_civic,load_genoxus,graph_extension}.py` — hardcode `REGION="us-west-2"` despite importing `_config` (issue #3); `09_validate.py` also hardcodes `GLUE_DB` (issue #6).
- `dataset_onboarding/` — self-contained; no import coupling; runtime-only L3 integration via `agent_config.json`; live RODA MCP discovery with fallback.
- `docs/bring-your-own-data.md` — architecture mismatch vs shipped code (issue #2).
- `docs/remote-mcp-server-design.md` — design-only, correctly labeled PLAN; not in code (no mismatch).
- `docs/skill-design-roda-onboarding.md` — generic-wrapper principle upheld in code.
- `docs/README.md` — 15-doc index; no cost doc, no ADR dir listed (issues #4, #5).
- Missing: teardown runbook/script (issue #1, blocker), `docs/COST_ANALYSIS.md` (#4), `docs/adr/` (#5).

Full diff: whole untracked subproject (`git add -n .` lists 183 committable files); review was against
the working tree.

</details>
