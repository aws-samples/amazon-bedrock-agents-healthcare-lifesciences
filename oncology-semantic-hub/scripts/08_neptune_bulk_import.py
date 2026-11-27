#!/usr/bin/env python3
"""Step 08: Bulk-import the openCypher CSVs into Neptune Analytics.

This was previously a MANUAL step — step 06 only builds and uploads the CSVs to
`s3://<bucket>/neptune/`; the actual graph load was run by hand. It is now scripted.

Two modes:
  --into <graph_id>   StartImportTask into an EXISTING graph (default: SEMHUB_GRAPH_ID).
  --new "<graphName>" CreateGraphUsingImportTask — provisions a NEW graph and imports.
                      Prints the new graph id; export it as SEMHUB_GRAPH_ID for later steps.

Reads:  s3://<bucket>/neptune/  (openCypher node/edge CSVs from step 06)
Writes: the Neptune Analytics graph

Usage:
    python 08_neptune_bulk_import.py --dry-run
    python 08_neptune_bulk_import.py --into <your-graph-id>
    python 08_neptune_bulk_import.py --new oncology-semantic-hub --memory 32

Requires SEMHUB_IMPORT_ROLE_ARN (a role Neptune can assume with S3 read on the bucket +
neptune-graph write). Import format is OPEN_CYPHER.
"""
import argparse
import time

import boto3

import _config as C

POLL_SECONDS = 30
MAX_WAIT_SECONDS = 3600
FORMAT = "OPEN_CYPHER"


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--into", metavar="GRAPH_ID", help="import into an existing graph (default: SEMHUB_GRAPH_ID)")
    g.add_argument("--new", metavar="GRAPH_NAME", help="create a new graph and import into it")
    ap.add_argument("--memory", type=int, default=32, help="m-NCU provisioned memory for --new (default 32)")
    ap.add_argument("--public-connectivity", action="store_true",
                    help="create the new graph with PUBLIC connectivity (default: private). "
                         "Only enable if you must reach the graph from outside its VPC; a public "
                         "graph endpoint is a larger attack surface (Holmes CSR finding #3).")
    ap.add_argument("--no-wait", action="store_true", help="start the task and return immediately")
    ap.add_argument("--dry-run", action="store_true", help="print the plan without calling AWS")
    args = ap.parse_args()

    print("=== Step 08: Neptune Analytics bulk import ===")
    print(C.summary())

    mode = "new" if args.new else "into"
    target = args.new if args.new else (args.into or C.GRAPH_ID)
    print(f"\nPlan:")
    print(f"  mode:    {'CreateGraphUsingImportTask (NEW graph)' if mode=='new' else 'StartImportTask (existing graph)'}")
    print(f"  target:  {target}")
    print(f"  source:  {C.NEPTUNE_S3}  format={FORMAT}")
    print(f"  role:    {C.IMPORT_ROLE_ARN or '(unset)'}")

    if args.dry_run:
        print("\n[dry-run] no changes made.")
        return
    if not C.IMPORT_ROLE_ARN:
        raise SystemExit("SEMHUB_IMPORT_ROLE_ARN is unset. Set it to a role Neptune can assume "
                         "(S3 read on the bucket + neptune-graph write) and re-run.")

    ng = boto3.client("neptune-graph", region_name=C.REGION)

    if mode == "new":
        resp = ng.create_graph_using_import_task(
            graphName=args.new, source=C.NEPTUNE_S3, format=FORMAT, roleArn=C.IMPORT_ROLE_ARN,
            minProvisionedMemory=args.memory, maxProvisionedMemory=args.memory,
            publicConnectivity=args.public_connectivity, failOnError=False)
        graph_id = resp.get("graphId")
        conn = "PUBLIC" if args.public_connectivity else "private"
        print(f"  creating graph {graph_id} ({args.new}, {conn} connectivity); import task {resp['taskId']}")
    else:
        resp = ng.start_import_task(
            graphIdentifier=target, source=C.NEPTUNE_S3, format=FORMAT,
            roleArn=C.IMPORT_ROLE_ARN, failOnError=False)
        graph_id = target
        print(f"  started import task {resp['taskId']} into {graph_id}")

    task_id = resp["taskId"]
    if args.no_wait:
        print(f"  --no-wait set; poll with: aws neptune-graph get-import-task --task-identifier {task_id}")
        return

    t0 = time.time()
    while time.time() - t0 < MAX_WAIT_SECONDS:
        t = ng.get_import_task(taskIdentifier=task_id)
        status = t.get("status")
        print(f"  [{time.time()-t0:>5.0f}s] import status: {status}")
        if status in ("SUCCEEDED", "FAILED", "CANCELLED", "ROLLING_BACK", "CANCELLING"):
            break
        time.sleep(POLL_SECONDS)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    else:
        raise SystemExit("Import task did not complete within the timeout.")

    if status != "SUCCEEDED":
        raise SystemExit(f"Import ended in status {status}: {t.get('importOptions')} {t}")
    print(f"\nImport SUCCEEDED into graph {graph_id}.")
    if mode == "new":
        print(f"  → export SEMHUB_GRAPH_ID={graph_id}  (used by steps 09/11/12/14/15)")
    print("=== Step 08 complete ===")


if __name__ == "__main__":
    main()
