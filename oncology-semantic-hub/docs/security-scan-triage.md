# Security Scan Triage — Probe Scan 2026-08-12

**Scan:** `ProbeScanExport-ca11a18b-…-main-20260812.csv` (gitleaks + bandit + semgrep) on `oncology_semantic_hub`.
**Scope of this doc:** all **ERROR-severity ("critical")** findings, each with a disposition. Notable
WARNING/INFO items are listed at the end as hardening backlog (not blocking).

## Summary
| Finding class | Tool(s) | Severity | Disposition |
|---|---|---|---|
| `square-access-token` in `data/gdc/tcga_cases_raw.json` | gitleaks | ERROR | **False positive + never shipped** |
| `dangerous-subprocess-use` (deploy.py:110, run_pipeline.py:96) | semgrep | ERROR | **False positive — audited + annotated** |
| XML XXE in `agentcore/kb/build_corpus.py` (30/193) | bandit B314/B405, semgrep use-defused-xml | ERROR/WARN | **Fixed (defusedxml) + tested** |
| `arbitrary-sleep` (time.sleep across pipeline/deploy/agent) | semgrep | ERROR | **Accepted — intentional** |
| `insecure-document-method` innerHTML (`docs/archive/*.html:330`) | semgrep | ERROR | **Accepted — archived static artifact** |

---

## 1. gitleaks — `square-access-token` @ `data/gdc/tcga_cases_raw.json:1`  → FALSE POSITIVE
- **Verified not a real secret.** No literal Square token prefix (`sq0atp-` / `sq0csp-` / `EAAA…`) exists in the
  file. It is a 12.7 MB TCGA GDC **case-data** JSON (case UUIDs, `TCGA-BRCA`, `submitter_id`s). gitleaks matched a
  generic high-entropy substring.
- **Never ships.** The file is **not git-tracked** (`git ls-files` empty) and `data/` is **gitignored**
  (`.gitignore:8`). The entire `data/` tree is untracked.
- **Action:** none (no code change). Double mitigation: not a secret **and** not committed.

## 2. semgrep — `dangerous-subprocess-use` (deploy.py:110, run_pipeline.py:96)  → FALSE POSITIVE (audited)
- **deploy.py:110** — a **fully static** argument vector (`[sys.executable, "-m", "pip", "install", <hardcoded
  package names>, …]`). No shell, no external/tainted input.
- **run_pipeline.py:96** — `subprocess.run([python, <script>], cwd=…)` where `<script>` comes only from the
  **static `STAGES` allowlist** (argparse `choices` restrict selection to fixed step numbers; never from free-form
  argv). No shell.
- **Action:** neither is command-injectable. Both annotated inline with `# nosec B603` + a one-line rationale so the
  audit is self-documenting. No behavioral change.

## 3. XML XXE — `agentcore/kb/build_corpus.py`  → FIXED
- `ET.fromstring()` parsed the PubMed eutils XML response. Source is the trusted NCBI API, but XXE hardening is
  cheap and correct.
- **Fix:** parse via `defusedxml.ElementTree.fromstring` (aliased `_safe_fromstring`); kept the stdlib `ET` import
  for element-traversal types (`# noqa: F401`). Added `defusedxml>=0.7` to `agentcore/requirements.txt`.
- **Tested:** normal XML still parses (`PubmedArticleSet` root); an XXE payload
  (`<!ENTITY e SYSTEM "file:///etc/passwd">`) now raises `EntitiesForbidden`.

## 4. semgrep — `arbitrary-sleep` (many sites)  → ACCEPTED / INTENTIONAL
- Every `time.sleep()` is deliberate: **external-API rate-limiting** (GDC, cBioPortal, NCBI eutils in the
  `scripts/` extract stages) or **polling loops for async AWS operations** (Neptune bulk-import status,
  AgentCore runtime-ready in `deploy.py`, KB ingestion in `kb/`).
- `arbitrary-sleep` is a **code-smell rule** ("did you mean to leave this in?"), not a vulnerability. Removing the
  sleeps would break rate-limit compliance and polling. **No change.**

## 5. semgrep — `insecure-document-method` innerHTML @ `docs/archive/…-interactive.html:330`  → ACCEPTED
- An **archived static visualization** kept under `docs/archive/` for history. It is **not served as a live app**
  and takes **no user input**; the `innerHTML` assignment is on static, in-file content.
- No XSS reachability. **No change** (would only revisit if the artifact is ever promoted to a served surface).

---

## Notable non-critical (WARNING/INFO) — hardening backlog (not blocking)
- **HTTP requests without timeout** (B113 / `use-timeout`): `scripts/01,02,03,04`. *Recommend:* add
  `timeout=` to `requests` calls to avoid hangs. Low risk (dev-time pipeline).
- **`B608` SQL-string construction**: Athena/graph query builders in `evaluation/`, `ground_truth/`,
  `scripts/09,build_l2_raw_lake`. Inputs are **internal, controlled** identifiers (table/column/study names), not
  end-user input. *Recommend:* review + parameterize/validate identifiers where practical.
- **`B310` urllib scheme audit**: fixed `https://` API endpoints (GDC/eutils/OLS). Low risk; *recommend* migrating
  to `requests` opportunistically.
- **`_config.py:60` `globals()` index** (`dangerous-globals-use`): used for internal config resolution, not
  attacker-controlled. *Recommend:* refactor to an explicit dict lookup to satisfy the rule.
- **`unspecified-open-encoding`** (many): add `encoding="utf-8"` to `open()` calls for cross-platform safety.

## Verification
- `python -m unittest tests.test_benchmark_framework -v` → **26/26 pass** (adds `TestXmlSafety`: parser-is-defusedxml,
  normal-XML-parses, XXE-payload-rejected). *(Note: this venv has no `pytest`; use `unittest`.)*
- `build_corpus.py` imports cleanly; XXE parse test passes (payload → `EntitiesForbidden`).
- **Caveat:** gitleaks / semgrep / bandit are **not installed in this environment**, so the probe itself was
  **not re-run locally**. Suppressions below use each tool's documented mechanism but were **not empirically
  re-scanned** — confirm on the next probe run (or with the probe owner, if it uses a centralized config).

## Will the next scan be clean? (suppression status)
| Finding | Mechanism added | Re-trigger risk |
|---|---|---|
| gitleaks secret (`data/…`) | `.gitleaks.toml` path allowlist `^data/` **+** `.gitleaksignore` fingerprint | Clean **if** the probe honors repo-local gitleaks config / ignore file. If it uses a central config, apply the allowlist there. |
| semgrep subprocess (deploy.py, run_pipeline.py) | `# nosemgrep` on both lines (plus `# nosec B603` for bandit) | Clean (inline ignore is the documented mechanism). |
| bandit subprocess (B603) | `# nosec B603` | Clean. |
| XML XXE | Code fixed (defusedxml) — the finding is genuinely resolved, not suppressed | Clean. |
| `arbitrary-sleep` (accepted) | **None** — intentional, left as-is | **Will still appear** unless we also add `# nosemgrep`. Decision: keep visible (they are legitimate). |
| archived-HTML innerHTML (accepted) | **None** | **Will still appear** (archived artifact). |

## Files changed
- `agentcore/kb/build_corpus.py` — defusedxml XXE-safe parse.
- `agentcore/requirements.txt` — add `defusedxml>=0.7`.
- `agentcore/deploy.py`, `scripts/run_pipeline.py` — `# nosec B603  # nosemgrep` + audit rationale on static/allowlisted subprocess calls.
- `.gitleaks.toml`, `.gitleaksignore` — allowlist the generated/gitignored `data/` false positive.
- `tests/test_benchmark_framework.py` — `TestXmlSafety` (3 XXE regression tests).

---

# Update — Re-scan 2026-08-13 (`f8220ebc-…`): remaining 23 criticals

The first pass resolved **6** criticals (gitleaks secret + 4 subprocess ERRORs via `# nosemgrep` — **confirmed
cleared** in this re-scan, proving the probe honors inline `# nosemgrep`). **23** semgrep-ERROR findings remained;
this pass addresses **all** of them:

| Remaining finding | Count | Resolution |
|---|---|---|
| `use-defused-xml` / B405 — `build_corpus.py:30` | 1 | **Root-cause fixed.** The prior pass added defusedxml but *left the `import xml.etree.ElementTree` in place*, so the scanner still flagged the import. Now the stdlib XML import is **removed entirely** (it was unused — all parsing goes through `defusedxml`). |
| `arbitrary-sleep` | 21 | **Suppressed** with inline `# nosemgrep` + rationale on every `time.sleep()` (intentional external-API rate-limit/backoff and async-AWS polling — legitimate, not a vulnerability). |
| `insecure-document-method` (innerHTML, archived HTML) | 1 | **Suppressed** with inline `// nosemgrep` on the innerHTML lines (archived static visualization; static in-file content, no user input). |

**Thoroughness sweep (beyond the report):** suppressed **all** `time.sleep()` repo-wide (25 total = 21 reported + 2
adjacent retry sleeps + 2 in `hybrid_check.py`/`chat_ui.py` not in this report) and **both** `innerHTML` lines
(351 + 419; the report cited a stale line 330) — so future scans stay clean, not just this one.

### Verification (this pass)
- `py_compile` on all 16 touched `.py` files → **OK**.
- `python -m unittest tests.test_benchmark_framework` → **26/26 pass** (incl. XXE regression tests).
- `build_corpus.py` imports; parser is `defusedxml`; no stdlib `import xml` remains.
- Repo-wide grep confirms **no un-suppressed `time.sleep` or `innerHTML`** remain.

### Residual uncertainty (flagged for the next scan)
- **Scanners are not installed locally** → I could not empirically re-run semgrep. Confidence is high because the
  **same `# nosemgrep` mechanism was proven to work** on the subprocess findings in this very re-scan.
- **One lower-confidence item:** the archived-HTML suppression uses the JS comment form `// nosemgrep`. Only the
  Python `#` form is independently proven against this probe. If the HTML finding persists next scan, the fallback
  is to **exclude `docs/archive/` from scanning** (`.semgrepignore`) or **remove the archived artifact** (it is not
  product code). Flagged to decide together if it recurs.

### Expected next scan
All 29 criticals cleared (6 prior + 23 this pass). Bandit WARNING/INFO items (SQL-string `B608`, request timeouts
`B113`, `B310` urllib, `globals()` `_config.py:60`, `open()` encodings) remain as the documented **non-critical
hardening backlog** — not addressed here since they are not ERROR-severity.
