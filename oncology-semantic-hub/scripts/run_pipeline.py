#!/usr/bin/env python3
"""Orchestrator for the Oncology Semantic Hub data setup — runs every stage in the correct
EXECUTION order (which is NOT the file-number order).

The scripts are numbered by the order they were *written*, not the order they must *run*.
This orchestrator is the single, readable entry point that encodes the real dependency order
and runs each stage end-to-end, including the steps that used to be manual (Glue crawler = 07,
Neptune import = 08) and the re-authored MONDO enrichment (15).

Examples:
    python run_pipeline.py --list                 # show the ordered plan, run nothing
    python run_pipeline.py --dry-run              # print the exact commands, touch nothing
    python run_pipeline.py                        # run the whole pipeline in order
    python run_pipeline.py --from 07 --to 08      # run a contiguous range (by step number)
    python run_pipeline.py --only 15              # run a single stage
    python run_pipeline.py --verify               # just run the end-to-end validation (09)

Stage numbers below are EXECUTION-order step numbers (1..N); the "script" column is the file.
"""
import argparse
import subprocess
import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parent

# (step, script, group, description). Order = execution order.
STAGES = [
    ("01", "01_download_primekg.py",      "Extract",  "Download PrimeKG (KG backbone) from Harvard Dataverse"),
    ("02", "02_build_mappings.py",        "Extract",  "ID crosswalks: TCGA project→MONDO, HUGO→Entrez"),
    ("03", "03_extract_gdc_clinical.py",  "Extract",  "GDC clinical + biospecimen → data/gdc (become case/sample nodes)"),
    ("04", "04_extract_gdc_molecular.py", "Extract",  "GDC somatic mutations → S3 lake/ Parquet"),
    ("05", "05_extract_cbioportal.py",    "Extract",  "cBioPortal CNA + expression → S3 lake/ Parquet"),
    ("06", "10_complete_expression.py",   "Extract",  "Backfill expression for remaining TCGA studies → lake/"),
    ("07", "07_create_athena_tables.py",  "Athena",   "Run Glue crawler over lake/ → create Athena tables  [supports --dry-run]"),
    ("08", "06_primekg_to_neptune.py",    "Graph",    "Build openCypher node/edge CSVs from PrimeKG+TCGA → upload to S3"),
    ("09", "08_neptune_bulk_import.py",   "Graph",    "Bulk-import the CSVs into Neptune Analytics  [supports --dry-run]"),
    ("10", "11_add_clinvar.py",           "Enrich",   "Enrich gene nodes with ClinVar pathogenic counts"),
    ("11", "14_add_cosmic.py",            "Enrich",   "Enrich gene nodes with COSMIC CGC Tier-1 flags"),
    ("12", "15_add_mondo.py",             "Enrich",   "Enrich disease nodes with MONDO icd10/ncit/definition  [supports --dry-run]"),
    ("13", "12_graph_algorithms.py",      "Analytics","Optional: centrality/community/pagerank → data/analytics/"),
    ("14", "09_validate.py",              "Validate", "End-to-end validation (Neptune + Athena QA checks)"),
]
_DRY_RUN_AWARE = {"07_create_athena_tables.py", "08_neptune_bulk_import.py", "15_add_mondo.py"}
_STEPS = [s[0] for s in STAGES]


def print_plan():
    print(f"{'Step':<5}{'Script':<28}{'Group':<10}Description")
    print("-" * 100)
    last = None
    for step, script, group, desc in STAGES:
        g = group if group != last else ""
        print(f"{step:<5}{script:<28}{g:<10}{desc}")
        last = group


def select(args):
    if args.only:
        return [s for s in STAGES if s[0] == args.only]
    lo = _STEPS.index(args.from_) if args.from_ else 0
    hi = _STEPS.index(args.to) if args.to else len(STAGES) - 1
    return STAGES[lo:hi + 1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="print the ordered plan and exit")
    ap.add_argument("--dry-run", action="store_true", help="print the commands without running")
    ap.add_argument("--from", dest="from_", metavar="STEP", choices=_STEPS, help="start at this step number")
    ap.add_argument("--to", metavar="STEP", choices=_STEPS, help="stop after this step number")
    ap.add_argument("--only", metavar="STEP", choices=_STEPS, help="run only this step")
    ap.add_argument("--verify", action="store_true", help="run only the validation stage (09_validate.py)")
    ap.add_argument("--keep-going", action="store_true", help="continue if a stage fails")
    args = ap.parse_args()

    if args.list:
        print_plan()
        return

    if args.verify:
        stages = [s for s in STAGES if s[1] == "09_validate.py"]
    else:
        stages = select(args)

    print(f"Pipeline: {len(stages)} stage(s) — {'DRY RUN' if args.dry_run else 'EXECUTE'}\n")
    for step, script, group, desc in stages:
        cmd = [sys.executable, str(_DIR / script)]
        if args.dry_run and script in _DRY_RUN_AWARE:
            cmd.append("--dry-run")
        banner = f"[{step}/{_STEPS[-1]}] {group}: {script}"
        print(f"\n{'='*90}\n{banner}\n  {desc}\n  $ {' '.join(cmd)}\n{'='*90}")
        if args.dry_run and script not in _DRY_RUN_AWARE:
            print("  [dry-run] not executed (stage has no --dry-run mode).")
            continue
        # SECURITY (B603/semgrep dangerous-subprocess-use): no shell is used (list-form argv passed
        # directly to subprocess.run, shell=False) so this is not command-injectable regardless of
        # input. `cmd = [python, <script>]` where <script> is drawn only from the static STAGES
        # allowlist above (defined in this file, never from argv/user input). Not fixable by
        # shlex.quote() — that function is for building shell command STRINGS and would corrupt a
        # list-form argv element (e.g. mangling any path containing a space); it does not apply to
        # this call shape. ACCEPTED RESIDUAL FINDING: Slingshot has been confirmed (2026-10-08/09
        # scans) to re-flag this exact call shape regardless of # nosemgrep/# nosec annotations —
        # suppression comments do not clear it. No equivalent "run as a function instead of a
        # subprocess" exists for orchestrating 14 independent ETL scripts without a much larger,
        # riskier refactor (importing + exec'ing their top-level code in-process, with each
        # script's own sys.exit() calls then killing the orchestrator). Audited; no code change.
        rc = subprocess.run(cmd, cwd=_DIR).returncode  # nosec B603  # nosemgrep
        if rc != 0:
            print(f"  ✗ stage {step} ({script}) exited {rc}")
            if not args.keep_going:
                sys.exit(rc)
    print("\nDone.")


if __name__ == "__main__":
    main()
