#!/usr/bin/env python
"""
Build the L2 raw data lake: expose raw PrimeKG (kg_giant.csv) as FLAT Athena tables
so the L2 agent can self-join relationships WITHOUT the Neptune graph or OLS.

This is the data-prep half of the L2 (raw-data) layer used for the apples-to-apples
L2-vs-L3 comparison (L2 = all raw data + KB; L3 = same facts + semantic hub graph+ontology).

What it creates (additive; new DB, easy rollback = drop the DB):
  - Glue DB  : oncology_semantic_hub_raw
  - Table    : primekg_edges  (Parquet, PARTITIONED BY relation)  <- from data/primekg/kg_giant.csv
  - Table    : primekg_nodes  (Parquet)                            <- from data/primekg/all_nodes.csv
  S3 layout  : s3://<bucket>/raw/primekg/primekg_edges/relation=<r>/*.parquet
               s3://<bucket>/raw/primekg/primekg_nodes/*.parquet

PARITY: kg_giant.csv is the same source PrimeKG that was loaded into the Neptune graph
(scripts/06_primekg_to_neptune.py), so L2's flat facts == L3's graph facts.

Usage:
  python scripts/build_l2_raw_lake.py                 # dry-run: print the plan only
  python scripts/build_l2_raw_lake.py --apply         # convert + upload + register
  python scripts/build_l2_raw_lake.py --apply --skip-convert   # re-register only (parquet already in S3)
  python scripts/build_l2_raw_lake.py --validate      # run a sample Athena query (drug_protein->EGFR)
"""
import argparse, os, sys, glob, time, tempfile, shutil
import boto3

import _config as C
REGION = C.REGION
C.require("BUCKET")
BUCKET = C.BUCKET
DB = "oncology_semantic_hub_raw"
S3_PREFIX = "raw/primekg"
ATHENA_OUT = f"s3://{BUCKET}/athena-results/"
WG = "primary"

HERE = os.path.dirname(os.path.abspath(__file__))
EDGES_CSV = os.path.join(HERE, "..", "data", "primekg", "kg_giant.csv")
NODES_CSV = os.path.join(HERE, "..", "data", "primekg", "all_nodes.csv")

EDGE_COLS = [  # non-partition columns (relation is the partition key)
    ("display_relation", "string"), ("x_index", "bigint"), ("x_id", "string"),
    ("x_type", "string"), ("x_name", "string"), ("x_source", "string"),
    ("y_index", "bigint"), ("y_id", "string"), ("y_type", "string"),
    ("y_name", "string"), ("y_source", "string"),
]
NODE_COLS = [("index", "bigint"), ("id", "string"), ("type", "string"),
             ("name", "string"), ("source", "string")]


def _plan():
    import pandas as pd
    e_sz = os.path.getsize(EDGES_CSV) / 1e6 if os.path.exists(EDGES_CSV) else 0
    n_sz = os.path.getsize(NODES_CSV) / 1e6 if os.path.exists(NODES_CSV) else 0
    rels = pd.read_csv(EDGES_CSV, usecols=["relation"])["relation"].value_counts()
    print("=== L2 RAW-LAKE BUILD PLAN (dry-run) ===")
    print(f"  edges src : {EDGES_CSV}  ({e_sz:.0f} MB)  present={os.path.exists(EDGES_CSV)}")
    print(f"  nodes src : {NODES_CSV}  ({n_sz:.0f} MB)  present={os.path.exists(NODES_CSV)}")
    print(f"  edges rows: {int(rels.sum()):,}   distinct relations (partitions): {len(rels)}")
    print(f"  target    : glue db '{DB}'  ->  primekg_edges (part by relation) + primekg_nodes")
    print(f"  s3        : s3://{BUCKET}/{S3_PREFIX}/")
    print("  top relations:")
    for r, c in rels.head(8).items():
        print(f"    {r:28} {c:>10,}")
    print("\n  (run with --apply to convert->upload->register)")


def _convert(tmp):
    import pandas as pd
    import pyarrow as pa, pyarrow.parquet as pq
    edges_dir = os.path.join(tmp, "primekg_edges")
    nodes_dir = os.path.join(tmp, "primekg_nodes")
    print("  reading nodes...")
    ndf = pd.read_csv(NODES_CSV, dtype={"id": "string", "type": "string", "name": "string", "source": "string"})
    ndf["index"] = ndf["index"].astype("int64")
    os.makedirs(nodes_dir, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(ndf, preserve_index=False), os.path.join(nodes_dir, "nodes.parquet"))
    print(f"  wrote nodes parquet ({len(ndf):,} rows)")
    print("  reading edges (chunked, partitioning by relation)...")
    total = 0
    for i, chunk in enumerate(pd.read_csv(EDGES_CSV, chunksize=1_000_000, dtype=str)):
        chunk["x_index"] = chunk["x_index"].astype("int64")
        chunk["y_index"] = chunk["y_index"].astype("int64")
        tbl = pa.Table.from_pandas(chunk, preserve_index=False)
        pq.write_to_dataset(tbl, root_path=edges_dir, partition_cols=["relation"],
                            basename_template=f"part-{i}-{{i}}.parquet",
                            existing_data_behavior="overwrite_or_ignore")
        total += len(chunk)
        print(f"    chunk {i}: {total:,} rows")
    print(f"  wrote edges parquet ({total:,} rows, partitioned by relation)")
    return edges_dir, nodes_dir


def _upload(s3, local_dir, s3_sub):
    n = 0
    for path in glob.glob(os.path.join(local_dir, "**", "*.parquet"), recursive=True):
        rel = os.path.relpath(path, local_dir)
        key = f"{S3_PREFIX}/{s3_sub}/{rel}"
        s3.upload_file(path, BUCKET, key)
        n += 1
    print(f"  uploaded {n} parquet files -> s3://{BUCKET}/{S3_PREFIX}/{s3_sub}/")


def _cols_ddl(cols):
    return ", ".join(f"`{c}` {t}" for c, t in cols)


def _register(glue, athena):
    try:
        glue.create_database(DatabaseInput={"Name": DB, "Description": "L2 raw data lake (flat PrimeKG etc.) — no graph/OLS"})
        print(f"  created glue db {DB}")
    except glue.exceptions.AlreadyExistsException:
        print(f"  glue db {DB} exists")

    def _drop(t):
        try:
            glue.delete_table(DatabaseName=DB, Name=t)
        except glue.exceptions.EntityNotFoundException:
            pass

    parquet_ser = {
        "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
        "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
        "SerdeInfo": {"SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"},
    }
    # edges (partitioned by relation)
    _drop("primekg_edges")
    glue.create_table(DatabaseName=DB, TableInput={
        "Name": "primekg_edges",
        "TableType": "EXTERNAL_TABLE",
        "Parameters": {"classification": "parquet", "EXTERNAL": "TRUE"},
        "PartitionKeys": [{"Name": "relation", "Type": "string"}],
        "StorageDescriptor": {
            "Columns": [{"Name": c, "Type": t} for c, t in EDGE_COLS],
            "Location": f"s3://{BUCKET}/{S3_PREFIX}/primekg_edges/",
            **parquet_ser,
        },
    })
    print("  created table primekg_edges (partitioned by relation)")
    _drop("primekg_nodes")
    glue.create_table(DatabaseName=DB, TableInput={
        "Name": "primekg_nodes",
        "TableType": "EXTERNAL_TABLE",
        "Parameters": {"classification": "parquet", "EXTERNAL": "TRUE"},
        "StorageDescriptor": {
            "Columns": [{"Name": c, "Type": t} for c, t in NODE_COLS],
            "Location": f"s3://{BUCKET}/{S3_PREFIX}/primekg_nodes/",
            **parquet_ser,
        },
    })
    print("  created table primekg_nodes")
    # discover partitions
    qid = athena.start_query_execution(
        QueryString=f"MSCK REPAIR TABLE `{DB}`.`primekg_edges`",
        ResultConfiguration={"OutputLocation": ATHENA_OUT}, WorkGroup=WG)["QueryExecutionId"]
    _wait(athena, qid)
    print("  MSCK REPAIR (partitions discovered)")
    _fix_encoded_partitions(boto3.client("s3", region_name=REGION), athena)


def _athena(athena, q):
    qid = athena.start_query_execution(QueryString=q, ResultConfiguration={"OutputLocation": ATHENA_OUT}, WorkGroup=WG)["QueryExecutionId"]
    return _wait(athena, qid)


def _fix_encoded_partitions(s3, athena):
    """MSCK can't read partition dirs whose value was URL-encoded by pyarrow (e.g. a space -> %20,
    'off-label use'). Copy those to a space-free path and repoint the partition to the literal value."""
    import urllib.parse
    base = f"{S3_PREFIX}/primekg_edges/"
    for cp in s3.list_objects_v2(Bucket=BUCKET, Prefix=base, Delimiter="/").get("CommonPrefixes", []):
        dirname = cp["Prefix"].rstrip("/").split("/")[-1]           # relation=off-label%20use
        if "%" not in dirname:
            continue
        enc = dirname.split("=", 1)[1]                              # off-label%20use
        lit = urllib.parse.unquote(enc)                            # off-label use
        clean = f"{base}relation={lit.replace(' ', '_')}/"         # .../relation=off_label_use/
        for o in s3.list_objects_v2(Bucket=BUCKET, Prefix=cp["Prefix"]).get("Contents", []):
            s3.copy_object(Bucket=BUCKET, CopySource={"Bucket": BUCKET, "Key": o["Key"]}, Key=clean + o["Key"].split("/")[-1])
        _athena(athena, f"ALTER TABLE `{DB}`.`primekg_edges` DROP IF EXISTS PARTITION (relation='{lit}')")
        _athena(athena, f"ALTER TABLE `{DB}`.`primekg_edges` ADD PARTITION (relation='{lit}') LOCATION 's3://{BUCKET}/{clean}'")
        print(f"  fixed URL-encoded partition '{lit}' -> s3://{BUCKET}/{clean}")


def _wait(athena, qid, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]["State"]
        if s in ("SUCCEEDED", "FAILED", "CANCELLED"):
            return s
        time.sleep(2)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    return "TIMEOUT"


def _validate(athena):
    q = (f"SELECT y_name AS drug, count(*) n FROM `{DB}`.`primekg_edges` "  # nosec B608 — DB is a module constant, not external input
         f"WHERE relation='drug_protein' AND x_name='EGFR' GROUP BY y_name ORDER BY n DESC LIMIT 5")
    print(f"  validate: {q}")
    qid = athena.start_query_execution(QueryString=q, ResultConfiguration={"OutputLocation": ATHENA_OUT}, WorkGroup=WG)["QueryExecutionId"]
    if _wait(athena, qid) != "SUCCEEDED":
        r = athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"]["Status"]
        print("  VALIDATE FAILED:", r.get("StateChangeReason")); return
    rows = athena.get_query_results(QueryExecutionId=qid)["ResultSet"]["Rows"]
    for row in rows:
        print("   ", [c.get("VarCharValue", "") for c in row["Data"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--skip-convert", action="store_true", help="re-register only (parquet already in S3)")
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()

    if not args.apply and not args.validate:
        _plan(); return

    s3 = boto3.client("s3", region_name=REGION)
    glue = boto3.client("glue", region_name=REGION)
    athena = boto3.client("athena", region_name=REGION)

    if args.apply:
        if not args.skip_convert:
            tmp = tempfile.mkdtemp(prefix="l2raw_")
            try:
                edges_dir, nodes_dir = _convert(tmp)
                _upload(s3, edges_dir, "primekg_edges")
                _upload(s3, nodes_dir, "primekg_nodes")
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        _register(glue, athena)
        print("APPLY complete.")
    if args.validate:
        _validate(athena)


if __name__ == "__main__":
    main()
