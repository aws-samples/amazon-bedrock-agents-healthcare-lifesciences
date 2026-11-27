# Pre-PR Review — Testing & Evaluation Framework

**Scope:** `oncology_semantic_hub/` only (one subproject of the `amazon-bedrock-agents-healthcare-lifesciences` monorepo).
**Type:** Read-only review. No source files were modified. Test suites were executed; no live AWS calls or deploys were made.
**Audience context:** public `aws-samples` solution accelerator for external customer engineers.
**Reviewer environment:** repo `.venv`, Python 3.13.3, **no `pytest` installed** (confirmed) — all runs via `python -m unittest`.

---

## TL;DR Verdict

**Credible, with fixable gaps — not a blocker, but three things should be fixed before the public PR.**

The eval framework is the strong part and is genuinely well-designed: it correctly treats the LLM behavior as an *eval set with graders and aggregate assertions* rather than unit-testing model output, it separates deterministic scoring from AWS I/O so scoring is unit-testable offline, and it has both validation paths the review asked about (pre-deploy comparison + continuous batch with CloudWatch emission). The deterministic scorers and the read-only SQL/Cypher guards have real edge/error/security coverage, and the XXE fix is locked in by regression tests.

The **main liabilities are discoverability and framework hygiene**, not test quality:
1. The highest-value scorer suite (`evaluation/test_scoring.py`, ~45 assertions) is **invisible to the test runner** — it is written as plain functions with a `main()`, so `unittest` collects **0 tests** from it.
2. The 26-test `tests/test_benchmark_framework.py` suite is **not found by default `unittest discover`** from the repo root (no `tests/__init__.py`); you must pass `-s tests`. A CI job running the obvious command silently tests only 21 of ~47+ cases.
3. No integration test asserts the **env-gated tool list matches the layer** (the core L0–L3 mechanism), and there is **no system/smoke test** of a deployed runtime.

None of these require rewriting; they are packaging/wiring fixes.

---

## Empirical test-run results

| Invocation | Result | Notes |
|---|---|---|
| `python -m unittest discover` (repo root, default) | **21 passed** | Finds **only** `hub_core/tests/*` (that package has `__init__.py`). Does **not** discover top-level `tests/`. |
| `python -m unittest discover -s tests -v` | **26 passed** | `tests/test_benchmark_framework.py`. Only runs when `tests/` is named explicitly. |
| `python -m unittest discover -s hub_core -v` | **21 passed** | guards 8, queries 5, schema 8. |
| `python -m unittest evaluation.test_scoring` | **0 tests ran** | File has no `TestCase`; function-style script. |
| `python -m evaluation.test_scoring` (as the file documents) | **PASS (all)** | ~45 `check(...)`/`assert` scorer assertions pass when run directly. |

**Orchestrator's expectation (~26 top-level + ~21 hub_core) is confirmed** — but with the critical caveat that the "26" are **not reachable by the default discover command**, and a *third* strong suite (`test_scoring.py`, ~45 assertions) is not counted by `unittest` at all. Corrected total that an auditor actually gets from the documented commands: **47 unittest cases across two different invocations**, plus one script that must be run a third way.

**Offline import check (no AWS):** all of the following import cleanly without credentials —
`evaluation/scoring.py`, `evaluation/provenance_faithfulness.py`, `agentcore/run_v2_benchmark.py`,
`agentcore/realtime_metrics.py`, `evaluation/judge.py`, `agentcore/run_agentcore_eval.py`, `evaluation/run_evaluation.py`.
Scoring logic is cleanly separated from AWS calls:
- `run_v2_benchmark.score_correct` (`agentcore/run_v2_benchmark.py:48`) is a pure function; AWS lives in `invoke()` (`:40`) and `main()`.
- `evaluation/scoring.py` has **no boto3 import** at all — fully offline.
- `judge.py` constructs a `bedrock-runtime` client at module load (`evaluation/judge.py:20`) but that does not require credentials, so import still succeeds; the network call is confined to `judge_absence()`.

---

## Per-rubric assessment

### 1. Right test type for each bug class (unit / integration / system / eval)

| Category | What exists | Evidence | Verdict |
|---|---|---|---|
| **Unit (logic)** | Read-only guards; benchmark scorer; provenance scorer; golden-schema; deterministic scorers | `hub_core/tests/test_guards.py`, `hub_core/tests/test_queries.py`, `hub_core/tests/test_schema.py`, `tests/test_benchmark_framework.py` (`TestProvenanceFaithfulness`, `TestCustomScorer`), `evaluation/test_scoring.py` | **Strong** (but see #2 discoverability) |
| **Integration (wiring)** | `TestConfig` checks path resolution only; `queries`/`schema` tests mock boto3 clients | `tests/test_benchmark_framework.py:150` (`TestConfig`), `hub_core/tests/test_queries.py` | **Partial gap** |
| **System (deployment)** | None automated. Deploy + eval runners exist but require live AWS | `agentcore/deploy.py`, `agentcore/run_agentcore_eval.py` | **Gap** |
| **Eval (LLM behavior)** | Two full paths (see #6) | `agentcore/run_v2_benchmark.py`, `agentcore/run_agentcore_eval.py`, `evaluation/run_evaluation.py` | **Strong** |

**Named gaps:**
- **No integration test that the env-gated tool list matches the layer.** The layer→tools contract is defined in two places — `evaluation/config.py:118` (`LAYERS` / `LAYERS_FUTURE`, e.g. L3 tools = `query_knowledge_graph, query_patient_data, get_hub_schema, ontology_lookup`) and the runtime agent `agentcore/semantic_hub_agent.py` (env-gated). Nothing asserts these agree. This is the accelerator's central mechanism (L0–L3) and is currently unprotected by a test. The provenance scorer's `VALID` tag inventory per layer (`evaluation/provenance_faithfulness.py:17`) is a *third* copy of the same layer→capability map, also untested for drift.
- **No system/smoke test of a deployed runtime** — not even a cheap "invoke returns a well-formed `{answer, usage}` envelope" check against a mock of `invoke_agent_runtime`. `run_v2_benchmark.invoke` (`:40`) parses the runtime envelope with real branching (structured vs plain-string back-compat) that has no test.
- **Scorers ARE unit-tested** (good) — the concern is only that one suite is undiscoverable.

### 2. Community-standard framework

The repo uses stdlib `unittest` + a custom benchmark runner.

- **The custom benchmark runner is justified as an eval harness, not an unjustified test runner.** `run_v2_benchmark.py` and `run_agentcore_eval.py` orchestrate live agent invocations, N-run reproducibility, CloudWatch metric emission, and (for the native path) AgentCore's built-in evaluators. That is eval-harness work — correctly *not* something pytest should own. The deterministic *logic* underneath (`score_correct`, `scoring.py`) is appropriately factored out as pure functions.
- **Not using pytest is a real but moderate liability for a public accelerator.** Two concrete harms already manifest: (a) `evaluation/test_scoring.py` is written in a function+`assert` style that *looks* like pytest but silently collects **0** under `unittest` — pytest would have run its ~45 assertions for free; (b) default `unittest discover` misses `tests/`. Both are symptoms of fighting `unittest`'s discovery rules. For external CEs who will copy the pattern, pytest (with `parametrize`) is the ecosystem default and would remove these foot-guns. **Recommendation:** either add `pytest` to `requirements`/dev-deps and a `pytest.ini` with `testpaths`, or (if staying stdlib) fix discovery (see Findings). Staying on `unittest` is defensible **only if** discovery is made reliable.

### 3. Coverage necessary-not-sufficient — would an auditor believe it?

Breadth is good where it exists:

| Category | Present? | Evidence |
|---|---|---|
| Core / happy path | Yes | all suites |
| Edge | Yes | `test_scoring.py` — prose tokenization, hyphen-range vs minus, JSON-string expected, `k=0` top-k, N=0 reproducibility (`evaluation/test_scoring.py:68–101`) |
| Boundary | Yes | within/outside 10% numeric tolerance (`:19–21`); F1 band thresholds (`:27`) |
| Error | Partial | `score_correct` "unrecognized ideal returns None, not crash" (`tests/test_benchmark_framework.py:143`); `require_select` empty/stacked (`hub_core/tests/test_guards.py`) |
| Security | Yes (notable) | SQL stacked-statement injection, comment-hiding writes, `replace()` false-positive (`hub_core/tests/test_guards.py:46,60`); XXE payload rejected (`tests/test_benchmark_framework.py:200`) |

**Highest-value logic is well covered on edge/error** — the scorers in `evaluation/test_scoring.py` go well past happy-path (composite gene+count partial-credit, negative-control refusal, reproducibility "consistent-but-wrong" disambiguation at `:52`). **An auditor would believe the scorer and guard suites** — *if they could find and run them.* The believability risk is entirely the discoverability problem: a CI log showing "Ran 21 tests OK" materially understates coverage and would make an auditor think the scorers are untested.

**Query-builder gap:** the SQL/Cypher *builders* in `evaluation/generate_questions.py` and `ground_truth/gen_v2_questions.py` (f-string query construction, flagged `B608` in the security triage) have **no unit tests** on the generated SQL. These are both high-value and already security-flagged; a few table-driven tests asserting the emitted SQL shape would close the loop.

### 4. Tests fail for the right reason

Spot-check (names describe specific bugs; assertions are meaningful, not trivially true):

- `test_comment_hiding_write_is_rejected` (`hub_core/tests/test_guards.py:60`) — asserts `/* SELECT */ DELETE FROM t` raises `ReadOnlyViolation`. Names a precise bypass; would fail iff comment-stripping regressed. **Meaningful.**
- `test_rejects_stacked_statements` (`:56`) — `SELECT 1; DROP TABLE t` must raise. Precise injection class. **Meaningful.**
- `test_l2_fabricated_graph` (`tests/test_benchmark_framework.py:40`) — L2 emitting `[Graph]` must score `< 1.0` and list `graph` in `fabricated`. Directly ties to the "fabricated grounding" definition. **Meaningful.**
- `test_no_tags_unauditable` (`:62`) — untagged answer → `None`, **not** `0.0`. Guards a subtle semantic (absence of evidence ≠ dishonesty) that is easy to get wrong. **Strong, non-trivial.**
- `reproducibility` "consistent-but-wrong" (`evaluation/test_scoring.py:52`) — three identical refusals → `self_consistency == 1.0` **and** `reproducible_correct is False`. Catches the exact failure mode the metric exists to prevent. **Strong.**

One soft spot: `test_unrecognized_ideal_returns_none` (`:143`) asserts `result is None or result == 0.0 or isinstance(result, float)` — that disjunction is **nearly always true** and would not catch much. It documents "doesn't crash" intent but is weak as an assertion.

### 5. parametrize / fixtures / `pytest.raises` equivalents

- `setUp` fixtures: `tests/test_benchmark_framework.py:28,86`; `setUpClass` for the XXE module load (`:184`).
- `assertRaises`: used throughout the guards suite (`hub_core/tests/test_guards.py:27,51,57,63`). Good `pytest.raises` equivalent.
- **`subTest`: not used anywhere.** Several tests loop over cases with a bare `for` (e.g. `test_rejects_writes`, `test_allows_read`) — a failure reports only the first failing item and hides the rest. These are exactly the table-driven cases that should use `with self.subTest(q=q):` (or pytest `parametrize`). **Recommend** adding `subTest` to the guard loops and the refusal/entity-list tables in `test_scoring.py`.

### 6. Eval LLM endpoints, don't unit-test them  *(core of the review)*

**Confirmed: the LLM parts are evaluated as an eval set with graders and aggregate accuracy, not per-case unit asserts on model output.** Both requested paths exist:

**(a) Pre-deploy / agent-comparison path** — `evaluation/run_evaluation.py` + `agentcore/run_v2_benchmark.py`
- Eval set: `ground_truth/golden_v2.json` (**84 questions**, 12 categories — verified by count).
- Aggregate assertions, not per-case: `run_evaluation._summarize` (`evaluation/run_evaluation.py:181`) reports `correctness_pct`, `reproducibility_pct`, `mean_correctness` per layer; `run_v2_benchmark.main` aggregates by `requires` × layer and prints TOTAL rows (`agentcore/run_v2_benchmark.py` aggregate block). No assertion is made on an individual model string.
- Graders used (identified):
  - **Deterministic / code graders** (authoritative for quantitative, list, ontology, regex): `evaluation/scoring.py` — exact-number with 10% tolerance (`score_exact_number:131`), entity **F1 / recall substring** (`f1_entities:158`, `score_entity_list:198`), top-k ranked recall (`score_ranked_list:213`), regex (`score_regex:227`), composite **all-assertions-must-hold** (`score_assertions:245`).
  - **Behavioral grader**: refusal/abstention detection via regex pattern bank (`detect_refusal:60`) — used for negative controls.
  - **LLM-as-judge**: `evaluation/judge.py` `judge_absence()` — grades absence/negative questions (temp 0, JSON score) because pattern-matching can't distinguish a *grounded* "not in the graph" from a fabrication. Correctly scoped to the one case deterministic grading is brittle on.
  - **Native AgentCore built-ins** (second, independent path): `Builtin.Correctness`, `Builtin.Faithfulness`, `Builtin.ToolSelectionAccuracy`, `Builtin.GoalSuccessRate`, `Builtin.TrajectoryAnyOrderMatch` (`agentcore/run_agentcore_eval.py:38`).
  - **Novel faithfulness grader**: `provenance_faithfulness.score_provenance` (`evaluation/provenance_faithfulness.py:46`) — layer-aware fabricated-grounding detector, complements `Builtin.Faithfulness` (which is vacuous with no retrieved context).
- Reproducibility treated as a first-class non-determinism metric: `scoring.reproducibility` (`:357`) separates `self_consistency` (value stability) from `reproducible_correct` (all-N correct **and** stable), with a value-anchored `_answer_signature` (`:310`) so wording variance isn't mistaken for non-determinism. This is the right way to assert on aggregate behavior of a stochastic endpoint.

**(b) Continuous batch path** — `agentcore/run_v2_benchmark.py --emit-metrics` + `agentcore/realtime_metrics.py`
- Batch job computes per-layer aggregates and **emits to CloudWatch** with a batch-job timestamp and `Mode=batch` dimension (`run_v2_benchmark.py` emit block; `realtime_metrics.emit_cloudwatch:170`). The same canonical scorer backs both real-time and batch so numbers match (`realtime_metrics.py` imports `evaluation.provenance_faithfulness`). Two emission transports (PutMetricData and EMF) are provided (`emit_cloudwatch`, `emit_emf`). This is a legitimate continuous-eval design.

**Assessment:** this rubric item is the framework's strongest dimension and is implemented to a high standard. The only improvement worth noting: there is **no committed accuracy threshold/gate** (e.g. "fail CI if L3 correctness < X") — the batch path *emits* metrics but nothing *asserts* a floor, so regressions are observable but not blocking. For a continuous process that's a reasonable choice; worth stating explicitly in docs.

### 7. Eval set grows from production failures

- **Generation mechanism exists:** `evaluation/generate_questions.py` builds questions from live entity pools via parameterized templates + deterministic verification (Athena/Cypher/OLS4), including `gen_negative` and `gen_misalignment` (production-failure-shaped categories — ontology misalignment, unmatched genes). `ground_truth/gen_v2_questions.py` is the v2 generator.
- **Regression-from-failure mechanism exists in practice but is informal:** the clearest example is `evaluation/test_scoring.py::test_regression_bugfixes` (`:68`) — "Regression tests for issues found by independent QA/review agents" — and `TestXmlSafety` locking the XXE fix. So failures *do* become permanent cases.
- **Gap:** there is **no documented path** for "a wrong production answer → a new golden case." Generation is from *live data*, not from *observed failures*, and nothing maps a bad runtime answer back into `golden_v2.json` with its verified truth. For an accelerator teaching this methodology, a short doc + a template entry (`id`, `input`, `expectedResponse`, `category`, `verify`) for "add a regression question from a failure" would complete the story. **Recommend** adding it.

---

## Prioritized findings

### Blockers (fix before the public PR)
1. **`tests/` is not discovered by default `unittest discover`.** Add `tests/__init__.py` (or a documented `discover -s`/`pytest.ini testpaths`) so the obvious CI command runs all suites. Today "Ran 21 tests OK" hides 26+ cases. — *packaging fix, not a test rewrite.*
2. **`evaluation/test_scoring.py` collects 0 tests under `unittest`.** ~45 high-value scorer assertions are invisible to the runner. Either convert to `unittest.TestCase` (or pytest functions) **or** add it to a documented runner. As-is, a reader reasonably believes the scorers are tested by the standard command when they are not.
3. **README path/API inaccuracies that will break copy-paste** (see README section below) — for a public accelerator these are release blockers because external CEs will hit them immediately.

### Should-fix
4. **Add an integration test for the layer→tool contract.** Assert `config.LAYERS[L].tools`, the runtime agent's env-gated tool set, and `provenance_faithfulness.VALID[L]` are mutually consistent per layer. This protects the L0–L3 core claim against silent drift across its three definitions.
5. **Add a smoke test for the runtime-response envelope** — mock `invoke_agent_runtime` and assert `run_v2_benchmark.invoke` handles both the structured `{answer, usage}` and plain-string back-compat branches (`agentcore/run_v2_benchmark.py:40`).
6. **Unit-test the SQL/Cypher query builders** (`generate_questions.py`, `gen_v2_questions.py`) — these are `B608`-flagged f-string builders; assert emitted SQL for a few inputs. Closes a security-adjacent, untested gap.
7. **Document (and optionally enforce) an accuracy floor** for the continuous batch path so regressions are gating, not just observable.

### Nice-to-have
8. Use `subTest` (or move to pytest `parametrize`) for the looping guard/refusal/entity tables so all cases report independently.
9. Strengthen `test_unrecognized_ideal_returns_none` — the current disjunction is nearly always true.
10. Add a short "turn a production failure into an eval case" doc + template to complete rubric #7.
11. Close the `ResourceWarning: unclosed file` in `TestGoldenDataset.setUp` (`tests/test_benchmark_framework.py:156` opens `golden_v2.json` without closing).
12. Decide on `pytest` for the public release; if adopted, these foot-guns disappear and the suite matches the Python-community default the rubric calls for.

---

## README accuracy (requested)

**Verified inaccuracies — recommend fixing before the PR:**

1. **Wrong golden-dataset path (both READMEs).** `README.md:30` and the `evaluation/README.md` file table list the dataset at `evaluation/golden_v2.json`. The file is actually at **`ground_truth/golden_v2.json`** (confirmed: `evaluation/golden_v2.json` does not exist; `config.GOLDEN_DATASET = ROOT/"ground_truth"/"golden_v2.json"`, `evaluation/config.py:92`). The main-README directory tree also omits `ground_truth/` and `hub_core/` entirely.
2. **Stale symbol name in `evaluation/README.md` Step 2.** It instructs editing `provenance_faithfulness.py → VALID_TAGS_PER_LAYER`; the actual variable is **`VALID`** (`evaluation/provenance_faithfulness.py:17`). Copy-paste guidance points at a non-existent name.
3. **Category list mismatch (`evaluation/README.md`).** The "Categories" list shows 7 generic names (`lake, graph_1hop, graph_multihop, reconciliation, ontology, multi_source, negative`). The actual `golden_v2.json` has **12** categories (verified): adds `cross_system, quantitative_precision, drug_gene_relationships, evidence, actionability` and drops none that matter. The main README's "12 categories" claim **is** correct — the two docs disagree with each other.
4. **No Testing section at all.** Neither README documents how to run the tests. Given findings #1–#2, the README must state the exact commands and that **`pytest` is not used** (`python -m unittest discover -s tests`, `python -m unittest discover -s hub_core`, and `python -m evaluation.test_scoring`). Without this, a user cannot reproduce the suite.

**Verified-accurate claims (no change needed):**
- "84-question benchmark" — correct (84).
- "12 categories" (main README) — correct.
- Results table and the 13%/10% deltas are consistent with `agentcore/v2_benchmark_results.json` provenance (not re-run here — requires live AWS).
- Prereq Python 3.13 matches the `.venv`.

*Note:* `README.md:5` has a sentence missing its terminating period ("...on hard oncology questions") — cosmetic.

---

## Security-scan review (requested)

Reviewed `docs/holmes-scan-findings-2026-08-14.md` and `docs/security-scan-triage.md`. Both are **thorough, well-triaged, and honest about residual uncertainty** — good artifacts for a public PR. Observations relevant to this testing review:

- **The XXE remediation is backed by tests**, not just claimed: `TestXmlSafety` (`tests/test_benchmark_framework.py:181`) asserts the parser is `defusedxml`, normal XML still parses, and an XXE payload raises `EntitiesForbidden`. This is the right way to lock a security fix — a genuine regression test, matching the triage doc's "Fixed + tested" disposition.
- **Both scan docs correctly note `pytest` is absent** and give the `unittest` command — consistent with my findings.
- **Recommendations I endorse as still-open and relevant to shipping:**
  - Holmes **#1 (secrets scrub)** and the decision to exclude internal-only docs (`SESSION-HANDOFF`, positioning, `docs/archive/`) from the public commit — this also clears most of theme D/E. This is a genuine blocker for the public push.
  - Holmes **#4 responsible-AI / not-for-clinical-use disclaimer** in `evaluation/system_prompts/full_hub.txt` **and** a top-level data-use disclaimer in the README — currently the README has **no** such disclaimer, which for a public *oncology* accelerator is a real gap (and resolves theme E in one move).
  - Holmes **#5 `B608`** overlaps directly with my Finding #6: the f-string SQL builders are both security-flagged **and** untested — fixing them with validated-identifier allowlists *and* adding builder unit tests addresses both reviews at once.
- **Caveat carried from the triage doc:** gitleaks/semgrep/bandit were **not installed locally**, so suppressions were not empirically re-scanned; the docs flag this honestly. I did not re-run them either (out of scope / not installed).
- **No new security issues found in the test/eval code itself.** The guards suite is a positive security signal (injection, stacked-statement, comment-bypass coverage).

## Did you run the Slingshot security tool? (requested)

**No — there is no evidence that Slingshot was run against this repo.**
- Repo-wide search for "slingshot" returns **only** gene-symbol hits in `data/mappings/hugo_to_entrez.csv` (`SSH1/2/3 = "slingshot protein phosphatase"`) — a biological term, not the tool.
- No Slingshot config, dotfile, report, or `.slingshot*` artifact exists anywhere in the subproject; no git-history mention.
- The security tooling that **was** run (per the two docs and the `.holmes/` directory): **Holmes** Content Security Review (`.holmes/project.json`, `docs/holmes-scan-findings-2026-08-14.md`) and a probe scan combining **gitleaks + bandit + semgrep** (`docs/security-scan-triage.md`), with repo-local `.gitleaks.toml` / `.gitleaksignore`. If a Slingshot scan is required for the PR, it has not been done yet.

---

## Bottom line

The **evaluation half is well-engineered** and correctly implements the two-path (pre-deploy + continuous batch) quality gate with proper graders and aggregate assertions — this is the product's core claim and it holds up. The **traditional-test half is good in content but mis-packaged**: the best suites are not discoverable by the standard command, and the README points at wrong paths/symbols. Fix the three blockers (test discovery, `test_scoring.py` collection, README paths), add the layer→tool integration test, and this is a credible public-accelerator PR.
