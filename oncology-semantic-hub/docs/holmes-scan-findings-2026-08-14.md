# Holmes Scan — Findings & Proposed Fixes (2026-08-14)

**Status: BACKLOG (triage complete, no fixes applied yet).** Summary of the Holmes automated scan for later action.

## Scan metadata
- **Scan ID:** `38345e95-25dc-459c-b10d-02292cb03962`
- **Project:** `oncology-semantic-hub-trial` (Project ID `8d9706e8-8d0e-4f87-9fc2-b4add2130d87`)
- **Rubric:** Content Security Review (CSR) · **Baseline:** HolmesContentSecurityReviewBaselinePolicy v3
- **Scope:** `oncology_semantic_hub/` (378 files; `.gitignore` applied, `.venv`/`__pycache__` skipped)
- **Purpose:** trial run before planning a formal OSS content security review
- **Portal:** https://portal.prod.holmes.aws.dev/projects/8d9706e8-8d0e-4f87-9fc2-b4add2130d87/scans/38345e95-25dc-459c-b10d-02292cb03962?region=us-east-1

## Overview
- **78 findings: 32 HIGH · 43 MEDIUM · 3 LOW**
- **Status: 74 active · 4 suppressed**
- **Scanners:** AI rubric (48) · Bandit (23) · Semgrep OSS (6; 4 suppressed) · ACAT (1)

## Cross-check vs our earlier probe-scan remediation
- ✅ **XXE fix confirmed** — `agentcore/kb/build_corpus.py` has no XML/XXE code finding.
- ✅ **Subprocess `# nosemgrep` honored** — the 4 suppressed findings are the `deploy.py` / `run_pipeline.py` subprocess calls.
- ℹ️ **`arbitrary-sleep` absent** — Holmes' "Semgrep OSS" ruleset (AppSec-calibrated) doesn't include that rule, so the earlier sleep suppressions are neither needed nor harmful here.

## Important triage filter — findings in files that WON'T ship
Holmes scanned the working tree, including **gitignored** files. These findings are moot for a public release:
- `data/golden_dataset.json`, `data/BENCHMARK_REPORT.md` (gitignored `data/`)
- `output/v2_benchmark_results.json` (gitignored `output/`)
- `agentcore/agent_config*.json` (gitignored; live account IDs — already excluded from commit)
Also most legal/messaging findings are in `docs/archive/` (historical) and internal-only docs already excluded from the commit.

---

## Findings by theme + proposed fixes

### A. Must-fix before any public push
| # | Finding | Sev | File(s) | Proposed fix |
|---|---|---|---|---|
| 1 | **Real AWS account ID + internal GitLab URL (with username)** in a doc targeting a public repo | HIGH | `docs/SESSION-HANDOFF-2026-08-12.md` (lines 4, 60) | Scrub the account ID → `<ACCOUNT_ID>` and remove/redact the internal `gitlab.aws.dev/hpoonawa/...` URL. Re-check the other new docs (`security-scan-triage.md`, `phase3-*`, positioning) for the same. Better: keep internal handoff docs OUT of the public commit entirely. |

### B. Should-fix (real security posture — HIGH)
| # | Finding | Sev | File | Proposed fix |
|---|---|---|---|---|
| 2 | IAM identity policy uses `Resource: '*'` on write/invoke actions | HIGH | `agentcore/deploy.py:54` | Scope resources to specific ARNs (Neptune graph, S3 bucket, Bedrock model/agent) where practical; document any that must stay `*`. |
| 3 | Neptune Analytics graph created with **public connectivity** | HIGH | `scripts/08_neptune_bulk_import.py:66` | Set private connectivity (or document why public is required for the bulk-import demo + note it's a sample). |
| 4 | Clinical/oncology AI **system prompt lacks safety guardrails/disclaimers** | HIGH | `evaluation/system_prompts/full_hub.txt` | Add a not-for-clinical-use / research-only disclaimer + guardrail language to the system prompt (align with repo's legal note). |

### C. Code scanners — HIGH (overlap the probe; Bandit rates higher)
| # | Finding | Sev | Files | Proposed fix |
|---|---|---|---|---|
| 5 | `B608` SQL built via f-strings (×12) | HIGH | `ground_truth/verify_paper_questions.py`, `evaluation/generate_questions.py`, `ground_truth/gen_v2_questions.py`, `scripts/09_validate.py`, `scripts/build_l2_raw_lake.py` | Internal identifiers (table/column names), not end-user input → low real risk. Parameterize where feasible; otherwise add validated-identifier allowlist + `# nosec B608` with rationale. |
| 6 | `B310` urllib scheme audit (×4) | HIGH | `evaluation/generate_questions.py:76`, `agentcore/semantic_hub_agent.py:199,427`, `evaluation/ols_client.py:43`, `ground_truth/gen_v2_questions.py:30` | Fixed `https://` API endpoints. Add explicit scheme check (reject non-http(s)) or switch to `requests`; else `# nosec B310` + rationale. |

### D. AWS Legal / messaging (HIGH + MEDIUM — mostly archived PDFs/docs)
| # | Finding | Sev | Where | Proposed fix |
|---|---|---|---|---|
| 7 | Prohibited terms ("ensures", "platform" w/ AWS service as subject) | HIGH | `docs/archive/semantic_data_layer_research.pdf` | Archived artifact — lowest priority. If it ships, reword; otherwise exclude `docs/archive/` from the public release. |
| 8 | Unsourced superlatives / quantified claims (×~8) | MED | archived PDFs/HTML, `docs/bring-your-own-data.md`, `docs/roda_*` | Add citations/qualifiers to any doc that ships; drop or caveat "most comprehensive"/speedup claims. |

### E. Sensitive Data Handling (MEDIUM — pervasive, ~25 findings)
Rubric flags nearly every file touching TCGA patient-level fields (`vital_status`, `days_to_death`, `age_at_diagnosis`, etc.) across `scripts/`, `evaluation/`, `ground_truth/`, `agentcore/`, `docs/`.
- **Nature:** TCGA is public, de-identified data → largely a **messaging/compliance** signal for a public healthcare sample, not a leak.
- **Proposed fix:** address at the top level rather than per-file — add a prominent **data-use / not-for-clinical-use disclaimer** in the README + system prompt, state the data is public de-identified TCGA, and note customers bringing their own PHI are responsible for HIPAA/BAA. Then (optionally) suppress the per-file rubric noise.

### F. Supply chain (MEDIUM)
| # | Finding | Where | Proposed fix |
|---|---|---|---|
| 9 | Unpinned deps / `@latest` | `agentcore/requirements.txt`, `README.md`, archived docs | Pin versions (`==`/`>=,<`) per the repo golden rule of exact/pinned deps. Note: `security-scan-triage.md:39` flag is a false positive (it merely *cites* `defusedxml>=0.7`). |

### G. Lower priority
| # | Finding | Sev | File | Proposed fix |
|---|---|---|---|---|
| 10 | `globals()` dynamic index | MED | `scripts/_config.py:60` | Refactor to an explicit dict lookup to satisfy the rule (not attacker-controlled today). |
| 11 | `B603` subprocess (×2) + ACAT 3P-download | LOW | `scripts/11_add_clinvar.py`, `scripts/15_add_mondo.py` | Already-audited internal subprocess use → `# nosec B603` + rationale; ACAT download is a documented data-fetch step. |

---

## Suggested order when we tackle this
1. **#1 secrets scrub** in docs (fast, blocks public push) + decide which internal docs to exclude from the commit.
2. **#4 responsible-AI disclaimer** + top-level **data-use disclaimer** (also answers most of theme E in one move).
3. **#2 IAM scoping** and **#3 Neptune connectivity** (real infra posture).
4. **Batch #6 (B310) + #5 (B608) + #9 (pin deps)** — mechanical code hardening.
5. **#10, #11, archived-doc legal/messaging (#7/#8)** — defer / handle via `docs/archive/` exclusion.

## Notes / open decisions
- Confirm whether `docs/archive/` and internal-only docs (handoff, positioning, exec-summary) ship in the public repo — excluding them removes a large block of D/E/legal findings outright.
- Full raw report: `~/Downloads/scan-report.json`. Companion: `docs/security-scan-triage.md` (probe-scan CSV triage).
