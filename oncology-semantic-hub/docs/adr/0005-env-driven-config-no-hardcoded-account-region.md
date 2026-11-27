# ADR 0005 — Env-driven config; never hardcode account/region

**Status:** Accepted

## Context

This is a public `aws-samples` accelerator meant to be redeployed in any account/region. Hardcoded
account IDs, graph IDs, bucket names, or ARNs in committed source would (a) leak internal identifiers
into a public repo and (b) force code edits to redeploy — breaking portability. The accelerator also
has a bring-your-own-data path where a customer points the same code at their own resources.

## Decision

Externalize everything that changes between environments through `SEMHUB_*` environment variables, with
a single config module (`scripts/_config.py`) as the source of truth. `require()` fails loudly with
setup guidance when a needed value is unset, so a misconfigured run never silently targets the wrong
account. `deploy.py` derives the account from `sts:GetCallerIdentity` and the region from the CLI arg /
session (never a literal), requires `SEMHUB_GRAPH_ID` for graph layers, and injects config into the
runtime environment. Account-specific deploy artifacts (`agent_config*.json`, `.env`, `data/`,
`output/`) are gitignored.

## Consequences

- **Positive:** redeploy in a new account/region needs no code edit; no account-specific values in the
  committable set (verified by grep for the reference account ID, ARNs, graph IDs, and account-scoped
  bucket names — all absent from committed files).
- **Negative / known gap:** ~10 `scripts/` steps still set `REGION = "us-west-2"` as a module constant
  despite importing `_config`, so `SEMHUB_REGION` does not actually move those steps off us-west-2.
  This is a tracked should-fix (use `C.REGION`); it does not affect the deployed agent, which is fully
  env-driven. (`scripts/{05,06,09,10,11,12,14}_*.py`, `build_l2_raw_lake.py`,
  `roda/{load_civic,load_genoxus,graph_extension}.py`.)
- **Operational:** internal-only status/handoff docs that embed real identifiers must be excluded from
  the public commit — the config discipline covers *code*, not prose (see the security review).

## Source rationale

`scripts/_config.py` (env-driven, fail-loud `require()`); `scripts/README.md` (Configuration section);
`docs/backlog.md` (de-accounting / portability as a release gate).
