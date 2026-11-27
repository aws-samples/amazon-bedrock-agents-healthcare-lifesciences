#!/usr/bin/env python3
"""Task 9: Validate the Oncology Semantic Hub end-to-end."""
import json, time, boto3

import _config as C
REGION = C.REGION
C.require("GRAPH_ID", "BUCKET")
GRAPH_ID = C.GRAPH_ID
GLUE_DB = C.ATHENA_DB
S3_BUCKET = C.BUCKET

neptune = boto3.client('neptune-graph', region_name=REGION)
athena = boto3.client('athena', region_name=REGION)

results = []

def query_neptune(cypher):
    resp = neptune.execute_query(
        graphIdentifier=GRAPH_ID,
        queryString=cypher,
        language='OPEN_CYPHER'
    )
    return json.loads(resp['payload'].read())['results']

def check(name, fn):
    print(f"\n{'='*60}\n  CHECK: {name}\n{'='*60}")
    try:
        passed, detail = fn()
        status = 'PASS' if passed else 'FAIL'
    except Exception as e:
        status, detail = 'FAIL', str(e)
    print(f"  Result: {status} — {detail}")
    results.append((name, status, detail))

# 1. Node counts
def check_node_counts():
    rows = query_neptune('MATCH (n) RETURN labels(n) AS type, count(n) AS count ORDER BY count DESC')
    total = sum(r['count'] for r in rows)
    for r in rows:
        print(f"    {r['type']}: {r['count']:,}")
    print(f"    TOTAL: {total:,} nodes across {len(rows)} types")
    return len(rows) >= 10 and total >= 100_000, f"{len(rows)} types, {total:,} nodes"

# 2. Edge counts
def check_edge_counts():
    rows = query_neptune('MATCH ()-[r]->() RETURN type(r) AS relation, count(r) AS count ORDER BY count DESC')
    total = sum(r['count'] for r in rows)
    for r in rows:
        print(f"    {r['relation']}: {r['count']:,}")
    print(f"    TOTAL: {total:,} edges across {len(rows)} types")
    return len(rows) >= 20 and total >= 1_000_000, f"{len(rows)} types, {total:,} edges"

# 3. Gene-disease query
def check_gene_disease():
    rows = query_neptune(
        "MATCH (d:disease)-[:disease_protein]->(g:gene_protein) "
        "WHERE d.name CONTAINS 'breast' RETURN g.name LIMIT 10"
    )
    for r in rows:
        print(f"    Gene: {r['g.name']}")
    return len(rows) > 0, f"{len(rows)} genes for breast carcinoma"

# 4. Drug-target query (edge direction in PrimeKG is gene→drug)
def check_drug_target():
    rows = query_neptune(
        "MATCH (g:gene_protein)-[:drug_protein]->(dr:drug) "
        "WHERE g.name = 'TP53' RETURN dr.name LIMIT 10"
    )
    for r in rows:
        print(f"    Drug: {r['dr.name']}")
    return len(rows) > 0, f"{len(rows)} drugs targeting TP53"

# 5. TCGA case counts
def check_tcga_cases():
    rows = query_neptune(
        "MATCH (c:case)-[:case_has_diagnosis]->(d:disease) "
        "RETURN d.name, count(c) AS cases ORDER BY cases DESC LIMIT 10"
    )
    for r in rows:
        print(f"    {r['d.name']}: {r['cases']:,} cases")
    return len(rows) > 0, f"{len(rows)} diseases with cases"

# 6. End-to-end traversal
def check_e2e_traversal():
    rows = query_neptune(
        "MATCH (c:case)-[:case_has_diagnosis]->(d:disease)"
        "-[:disease_protein]->(g:gene_protein)<-[:drug_protein]-(dr:drug) "
        "WHERE c.project_id = 'TCGA-BRCA' "
        "RETURN DISTINCT dr.name AS drug, g.name AS gene LIMIT 20"
    )
    for r in rows:
        print(f"    {r['drug']} → {r['gene']}")
    return len(rows) > 0, f"{len(rows)} drug-gene pairs for TCGA-BRCA"

# 7. Graph schema
def check_schema():
    resp = neptune.execute_query(
        graphIdentifier=GRAPH_ID,
        queryString='CALL neptune.graph.pg_schema()',
        language='OPEN_CYPHER'
    )
    schema = json.loads(resp['payload'].read())
    node_labels = schema.get('results', [{}])[0] if schema.get('results') else schema
    print(f"    Schema keys: {list(schema.keys()) if isinstance(schema, dict) else type(schema)}")
    # Just verify we got a schema back
    return bool(schema), "Schema retrieved"

# 8. Athena query
def check_athena():
    # Fix duplicate column issue: project_id appears as both column and partition key
    glue = boto3.client('glue', region_name=REGION)
    try:
        t = glue.get_table(DatabaseName=GLUE_DB, Name='tcga_mutations')
        cols = t['Table']['StorageDescriptor']['Columns']
        part_names = {p['Name'] for p in t['Table'].get('PartitionKeys', [])}
        deduped = [c for c in cols if c['Name'] not in part_names]
        if len(deduped) < len(cols):
            print(f"    Fixing duplicate columns: removing {part_names & {c['Name'] for c in cols}} from columns")
            sd = t['Table']['StorageDescriptor'].copy()
            sd['Columns'] = deduped
            glue.update_table(DatabaseName=GLUE_DB, TableInput={
                'Name': 'tcga_mutations',
                'StorageDescriptor': sd,
                'PartitionKeys': t['Table'].get('PartitionKeys', []),
                'TableType': t['Table'].get('TableType', ''),
                'Parameters': t['Table'].get('Parameters', {}),
            })
    except Exception as e:
        print(f"    Warning: could not fix table schema: {e}")

    sql = (
        f"SELECT project_id, COUNT(*) as mutations "  # nosec B608 — GLUE_DB is a config constant (C.ATHENA_DB), not external input
        f"FROM {GLUE_DB}.tcga_mutations "
        f"GROUP BY project_id ORDER BY mutations DESC LIMIT 5"
    )
    start = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={'Database': GLUE_DB},
        ResultConfiguration={'OutputLocation': f's3://{S3_BUCKET}/athena-results/'}
    )
    qid = start['QueryExecutionId']
    # Poll for completion
    for _ in range(30):
        status = athena.get_query_execution(QueryExecutionId=qid)['QueryExecution']['Status']
        state = status['State']
        if state in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
            break
        time.sleep(2)  # nosemgrep  (intentional sleep: external-API rate-limit/backoff or async-AWS poll)
    if state != 'SUCCEEDED':
        return False, f"Athena query {state}: {status.get('StateChangeReason', '')}"
    rows = athena.get_query_results(QueryExecutionId=qid)['ResultSet']['Rows']
    for r in rows[1:]:  # skip header
        vals = [c.get('VarCharValue', '') for c in r['Data']]
        print(f"    {vals[0]}: {vals[1]} mutations")
    return len(rows) > 1, f"{len(rows)-1} projects with mutations"

# Run all checks
if __name__ == '__main__':
    print("Oncology Semantic Hub — End-to-End Validation")
    print("=" * 60)

    check("1. Neptune Node Counts", check_node_counts)
    check("2. Neptune Edge Counts", check_edge_counts)
    check("3. Gene-Disease Query (breast)", check_gene_disease)
    check("4. Drug-Target Query (TP53)", check_drug_target)
    check("5. TCGA Case Counts", check_tcga_cases)
    check("6. E2E Traversal (BRCA→drugs)", check_e2e_traversal)
    check("7. Graph Schema", check_schema)
    check("8. Athena Mutations Query", check_athena)

    # Summary
    print(f"\n{'='*60}")
    print("  VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"  {'Check':<35} {'Status':<6} Detail")
    print(f"  {'-'*35} {'-'*6} {'-'*30}")
    for name, status, detail in results:
        icon = '✅' if status == 'PASS' else '❌'
        print(f"  {icon} {name:<33} {status:<6} {detail}")

    passed = sum(1 for _, s, _ in results if s == 'PASS')
    total = len(results)
    print(f"\n  {passed}/{total} checks passed")
    if passed < total:
        print("  ⚠️  Some checks failed — review above for details")
    else:
        print("  🎉 All checks passed!")
