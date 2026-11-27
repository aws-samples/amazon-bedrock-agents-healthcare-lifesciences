#!/usr/bin/env python3
"""Step 07: Create the Athena tables by (re)running the Glue crawler over the S3 lake.

This was previously a MANUAL step ("run the crawler in the console"). It is now scripted and
idempotent: it ensures the Glue database exists, creates the crawler if missing (pointed at
`lake/`), starts it, waits for it to finish, and lists the resulting tables.

Reads:  s3://<bucket>/lake/  (Parquet written by steps 04/05/10)
Writes: Glue database `oncology_semantic_hub` + Athena tables (tcga_mutations, tcga_expression, CNA)

Usage:
    python 07_create_athena_tables.py --dry-run     # show plan, touch nothing
    python 07_create_athena_tables.py               # create/run crawler, wait, list tables

Requires SEMHUB_GLUE_ROLE_ARN (an IAM role Glue can assume with S3 read + Glue catalog write)
only when the crawler does not already exist.
"""
import argparse
import time

import boto3

import _config as C

POLL_SECONDS = 15
MAX_WAIT_SECONDS = 1800


def fix_duplicate_partition_columns(glue):
    """Idempotent fix for a Glue crawler artifact: the crawler lists partition columns (e.g. project_id,
    source) as BOTH data columns and partition keys, which makes Athena reject the table with
    'Table descriptor contains duplicate columns' (breaks tcga_expression + source_cbioportal). Remove any
    data column that is also a partition key. Requires Lake Formation ALTER on the tables (LF-governed)."""
    fixed = []
    for t in glue.get_tables(DatabaseName=C.ATHENA_DB)["TableList"]:
        part = {c["Name"] for c in t.get("PartitionKeys", [])}
        cols = t["StorageDescriptor"]["Columns"]
        if part and any(c["Name"] in part for c in cols):
            sd = dict(t["StorageDescriptor"])
            sd["Columns"] = [c for c in cols if c["Name"] not in part]
            ti = {k: t[k] for k in ("Name", "Owner", "Retention", "StorageDescriptor", "PartitionKeys",
                                    "TableType", "Parameters", "Description") if k in t}
            ti["StorageDescriptor"] = sd
            try:
                glue.update_table(DatabaseName=C.ATHENA_DB, TableInput=ti)
                fixed.append(t["Name"])
            except Exception as e:  # noqa: BLE001
                print(f"  WARN: could not fix {t['Name']} ({e}); needs Lake Formation ALTER on the table")
    print(f"  fixed duplicate partition/columns on: {fixed}" if fixed else "  no duplicate-column tables")
    return fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the plan without calling AWS mutations")
    args = ap.parse_args()

    print("=== Step 07: Athena tables via Glue crawler ===")
    print(C.summary())

    glue = boto3.client("glue", region_name=C.REGION)

    # 1. Ensure the Glue database exists.
    try:
        glue.get_database(Name=C.ATHENA_DB)
        db_exists = True
    except glue.exceptions.EntityNotFoundException:
        db_exists = False

    # 2. Does the crawler already exist?
    try:
        crawler = glue.get_crawler(Name=C.CRAWLER_NAME)["Crawler"]
        crawler_exists = True
        targets = [t.get("Path") for t in crawler.get("Targets", {}).get("S3Targets", [])]
    except glue.exceptions.EntityNotFoundException:
        crawler_exists = False
        targets = []

    print(f"\nPlan:")
    print(f"  glue database '{C.ATHENA_DB}': {'exists' if db_exists else 'CREATE'}")
    print(f"  crawler '{C.CRAWLER_NAME}': {'exists (targets=' + str(targets) + ')' if crawler_exists else 'CREATE over ' + C.LAKE_S3}")
    print(f"  then: StartCrawler → poll to READY → list tables")

    if args.dry_run:
        print("\n[dry-run] no changes made.")
        return

    if not db_exists:
        glue.create_database(DatabaseInput={"Name": C.ATHENA_DB})
        print(f"  created database {C.ATHENA_DB}")

    if not crawler_exists:
        if not C.GLUE_ROLE_ARN:
            raise SystemExit(
                "Crawler does not exist and SEMHUB_GLUE_ROLE_ARN is unset. Set it to an IAM role "
                "Glue can assume (S3 read on the bucket + AWSGlueServiceRole) and re-run.")
        glue.create_crawler(
            Name=C.CRAWLER_NAME,
            Role=C.GLUE_ROLE_ARN,
            DatabaseName=C.ATHENA_DB,
            Targets={"S3Targets": [{"Path": C.LAKE_S3}]},
            SchemaChangePolicy={"UpdateBehavior": "UPDATE_IN_DATABASE", "DeleteBehavior": "LOG"},
        )
        print(f"  created crawler {C.CRAWLER_NAME} over {C.LAKE_S3}")

    # 3. Start + wait.
    try:
        glue.start_crawler(Name=C.CRAWLER_NAME)
        print(f"  started crawler {C.CRAWLER_NAME}")
    except glue.exceptions.CrawlerRunningException:
        print("  crawler already running; waiting for it to finish")

    t0 = time.time()
    while time.time() - t0 < MAX_WAIT_SECONDS:
        state = glue.get_crawler(Name=C.CRAWLER_NAME)["Crawler"]["State"]
        print(f"  [{time.time()-t0:>4.0f}s] crawler state: {state}")
        if state == "READY":
            break
        time.sleep(POLL_SECONDS)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    else:
        raise SystemExit("Crawler did not return to READY within the timeout.")

    # 3b. Fix the crawler's duplicate partition-column artifact so tcga_expression / source_cbioportal
    #     (and any partitioned table) are queryable in Athena.
    fix_duplicate_partition_columns(glue)

    # 4. List resulting tables.
    tables = [t["Name"] for t in glue.get_tables(DatabaseName=C.ATHENA_DB)["TableList"]]
    print(f"\nAthena tables in {C.ATHENA_DB} ({len(tables)}): {tables}")
    print("NOTE: multi-source lake — tcga_mutations (GDC, 33 cancer types), tcga_expression (source="
          "cbioportal), source_cbioportal (cBioPortal CNA, 10 cohorts). CNA also lands as per-project "
          "tables (project_id_tcga_*) — a known crawler artifact (see docs/data-pipeline-rebuild.md §4.1).")
    print("=== Step 07 complete ===")


if __name__ == "__main__":
    main()
