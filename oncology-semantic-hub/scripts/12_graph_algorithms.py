#!/usr/bin/env python3
"""Task 12: Run graph algorithms on the Neptune Analytics knowledge graph."""
import boto3, json, csv, os, time

import _config as C
REGION = C.REGION
C.require("GRAPH_ID")
GRAPH_ID = C.GRAPH_ID
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'analytics')
os.makedirs(OUT_DIR, exist_ok=True)

client = boto3.client('neptune-graph', region_name=REGION)

def run_query(cypher, timeout=60):
    resp = client.execute_query(
        graphIdentifier=GRAPH_ID, queryString=cypher, language='OPEN_CYPHER'
    )
    return json.loads(resp['payload'].read().decode()).get('results', [])

def save_csv(rows, filename):
    if not rows:
        print(f"  No results to save for {filename}")
        return
    path = os.path.join(OUT_DIR, filename)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"  Saved {len(rows)} rows → {path}")

def run_analysis(name, queries, filename):
    """Try each query in order; use first that succeeds."""
    print(f"\n{'='*60}\n  {name}\n{'='*60}")
    for i, (desc, cypher) in enumerate(queries):
        try:
            print(f"  Attempt {i+1}: {desc}")
            t0 = time.time()
            rows = run_query(cypher)
            elapsed = time.time() - t0
            print(f"  ✓ Success in {elapsed:.1f}s — {len(rows)} results")
            for r in rows[:5]:
                print(f"    {r}")
            if len(rows) > 5:
                print(f"    ... and {len(rows)-5} more")
            save_csv(rows, filename)
            return rows
        except Exception as e:
            err = str(e)
            if 'timeout' in err.lower() or 'timed out' in err.lower():
                print(f"  ✗ Timeout after 60s, skipping")
                return []
            print(f"  ✗ Error: {err[:200]}")
    print(f"  All attempts failed for {name}")
    return []

# ── 1. PAGERANK / DEGREE CENTRALITY on PPI network ──
run_analysis(
    "1. PAGERANK — Most Important Genes in PPI Network",
    [
        ("Neptune algo pageRank with edgeLabels",
         "CALL neptune.algo.pageRank({edgeLabels:['protein_protein']}) "
         "YIELD node, score WHERE 'gene_protein' IN labels(node) "
         "RETURN node.name AS gene, score AS rank ORDER BY rank DESC LIMIT 20"),
        ("Neptune algo pageRank (no params)",
         "CALL neptune.algo.pageRank() "
         "YIELD node, score WHERE 'gene_protein' IN labels(node) "
         "RETURN node.name AS gene, score AS rank ORDER BY rank DESC LIMIT 20"),
        ("Fallback: degree centrality on PPI",
         "MATCH (g:gene_protein)-[r:protein_protein]-() "
         "RETURN g.name AS gene, count(r) AS rank ORDER BY rank DESC LIMIT 20"),
    ],
    "pagerank_top_genes.csv"
)

# ── 2. COMMUNITY DETECTION — Gene Clusters ──
run_analysis(
    "2. COMMUNITY DETECTION — Gene Clusters",
    [
        ("Neptune algo WCC",
         "CALL neptune.algo.wcc({edgeLabels:['protein_protein']}) "
         "YIELD node, community WHERE 'gene_protein' IN labels(node) "
         "RETURN community, count(node) AS size, collect(node.name)[..5] AS sample_genes "
         "ORDER BY size DESC LIMIT 20"),
        ("Neptune algo WCC (no params)",
         "CALL neptune.algo.wcc() "
         "YIELD node, community WHERE 'gene_protein' IN labels(node) "
         "RETURN community, count(node) AS size, collect(node.name)[..5] AS sample_genes "
         "ORDER BY size DESC LIMIT 20"),
        ("Fallback: manual connected-component proxy via shared interactions",
         "MATCH (g1:gene_protein)-[:protein_protein]-(g2:gene_protein) "
         "WITH g1, collect(DISTINCT g2.name)[..5] AS neighbors, count(DISTINCT g2) AS cluster_size "
         "RETURN g1.name AS gene, cluster_size, neighbors "
         "ORDER BY cluster_size DESC LIMIT 20"),
    ],
    "community_detection.csv"
)

# ── 3. DEGREE CENTRALITY — Most Connected Nodes ──
run_analysis(
    "3. DEGREE CENTRALITY — Most Connected Nodes (all types)",
    [
        ("Degree centrality across all node/edge types",
         "MATCH (n)-[r]-() "
         "RETURN labels(n) AS type, n.name AS name, count(r) AS connections "
         "ORDER BY connections DESC LIMIT 20"),
    ],
    "degree_centrality.csv"
)

# ── 4. DISEASE SIMILARITY — Diseases Sharing Most Genes ──
run_analysis(
    "4. DISEASE SIMILARITY — Diseases Sharing the Most Genes",
    [
        ("Shared gene count between disease pairs",
         "MATCH (d1:disease)-[:disease_protein]->(g:gene_protein)<-[:disease_protein]-(d2:disease) "
         "WHERE id(d1) < id(d2) "
         "RETURN d1.name AS disease1, d2.name AS disease2, count(DISTINCT g) AS shared_genes "
         "ORDER BY shared_genes DESC LIMIT 15"),
    ],
    "disease_similarity.csv"
)

print(f"\n{'='*60}")
print(f"  All analyses complete. Results in: {os.path.abspath(OUT_DIR)}")
print(f"{'='*60}")
