# Neptune Database (Serverless) vs Neptune Analytics — Evaluation for Oncology Biomarker Semantic Hub

**Status:** Evaluation Complete — Recommendation: Neptune Analytics  
**Date:** 2026-04-30  
**Author:** AWS Solutions Architecture Review  
**Depends on:** `aws-architecture-design.md`

---

## Executive Summary

After evaluating both services against the Oncology Semantic Hub's specific workload characteristics (~170K nodes, ~4M edges, read-heavy, bulk-load-once, openCypher-only, <$300/month budget, graph algorithms required in Sprint 2), **Neptune Analytics is the recommended choice**. It delivers built-in graph algorithms, simpler operations, lower cost for this graph size, and a better fit for the analytical/exploratory nature of biomarker discovery queries.

---

## 1. Feature Comparison

| Feature | Neptune Database (Serverless) | Neptune Analytics |
|---------|-------------------------------|-------------------|
| **Query languages** | openCypher, Gremlin, SPARQL | openCypher only |
| **Storage model** | Disk-based with buffer cache | Fully in-memory |
| **Graph algorithms** | None built-in (requires Neptune ML + SageMaker) | 25+ built-in: PageRank, Louvain, WCC, SCC, LPA, BFS, shortest path, closeness centrality, Jaccard similarity, etc. |
| **Vector search** | Not supported | Built-in HNSW-based ANN vector similarity search |
| **Bulk load from S3** | Neptune Loader API (CSV in Gremlin/openCypher/SPARQL format) | `CreateGraphUsingImportTask` API (CSV, Parquet, ntriples) |
| **Incremental updates** | Full ACID transactions via openCypher MERGE/CREATE | Batch load from S3 + openCypher MERGE/CREATE (ACID) |
| **Parquet support** | No (CSV only for bulk load) | Yes (bulk import supports Parquet) |
| **ACID transactions** | Full read-write ACID | Full read-write ACID |
| **High availability** | Multi-AZ with up to 15 read replicas | 0–2 replicas across AZs |
| **Scaling** | Auto-scales NCUs (1–128 NCU, 2 GiB/NCU) | Fixed m-NCU provisioning (32–4096 m-NCU, 1 GiB/m-NCU), resizable without downtime |
| **Pause/resume** | Cannot pause (minimum NCU always runs) | Can pause graph (pay 10% of compute while paused) |
| **VPC requirement** | **Required** — must run inside a VPC | **Optional** — supports public endpoints with IAM auth |
| **Authentication** | IAM or VPC-based | IAM (Sig4) always |
| **CloudFormation/CDK** | Full support | Full support |
| **`neptune.read()` S3 federation** | Supported (openCypher) | Supported (openCypher) |
| **Max graph size** | 128 TiB (disk) | Limited by m-NCU memory provisioned |
| **Backup/snapshots** | Automated continuous backups, point-in-time restore | Manual snapshots; restore from snapshot |

### What Neptune Database has that Analytics doesn't

- Gremlin and SPARQL query language support (not needed for this workload)
- Multi-AZ with up to 15 read replicas for extreme read scaling (not needed at our scale)
- Continuous automated backups with point-in-time restore
- Neptune Streams for change data capture
- Neptune ML integration with SageMaker (separate from built-in algorithms)

### What Neptune Analytics has that Database doesn't

- **25+ built-in graph algorithms** callable via `CALL neptune.algo.*` in openCypher
- **Built-in vector similarity search** (HNSW) for node embeddings
- **Pause/resume** — pay 10% while paused
- **Public endpoint option** — no VPC required
- **Parquet bulk import** — load directly from Parquet files in S3
- **Simpler operational model** — no cluster/instance management

---

## 2. Cost Comparison for This Workload

### Workload sizing

- ~170K nodes, ~4M edges ≈ **1–2 GB in-memory graph** (estimated from PrimeKG ~8 GB at 129K nodes/4M edges with all properties; our subset with TCGA overlay is comparable)
- Read-heavy: ~50–200 queries/day from agent + interactive users
- Write pattern: bulk load once, then occasional incremental updates
- No need for Multi-AZ HA (research/discovery workload, not production OLTP)

### Neptune Database (Serverless) — estimated monthly cost

| Component | Configuration | Monthly Cost |
|-----------|--------------|-------------|
| Compute (NCU) | Min 2.5 NCU (5 GiB) always-on, 24/7 × 730 hrs × ~$0.1098/NCU-hr | **~$200** |
| Storage | ~2 GB graph data × $0.10/GB-month | ~$0.20 |
| I/O (Standard) | ~50M I/Os/month × $0.20/million | ~$10 |
| Backup storage | Included up to 100% of DB size | $0 |
| NAT Gateway | Required for VPC internet access | **~$35** |
| S3 VPC Endpoint | Required for bulk load | $0 (Gateway endpoint) |
| **Subtotal** | | **~$245/month** |

> **Critical constraint:** Neptune Serverless does NOT scale to zero. The minimum 1.0 NCU runs 24/7. At 2.5 NCU minimum (needed for openCypher DFE statistics), the compute floor is ~$200/month regardless of query activity. This consumes most of the $300 budget before any other services.

### Neptune Analytics — estimated monthly cost

| Component | Configuration | Monthly Cost |
|-----------|--------------|-------------|
| Compute (m-NCU) | 32 m-NCU (32 GiB) — smallest available, 24/7 | **~$58–70** |
| Compute (paused) | If paused 16 hrs/day: 8 hrs full + 16 hrs × 10% | **~$25–35** |
| Replicas | 0 replicas (not needed for research workload) | $0 |
| Backup/snapshots | Manual snapshots as needed | ~$1 |
| NAT Gateway | Not needed (public endpoint available) | **$0** |
| **Subtotal (always-on)** | | **~$60–70/month** |
| **Subtotal (with pause)** | | **~$25–35/month** |

> **Key advantage:** Neptune Analytics supports 32 m-NCU (the smallest tier, introduced July 2024), which is more than sufficient for a ~2 GB graph. The pause/resume feature means you can pay only 10% during off-hours. No VPC or NAT Gateway required with public endpoints.

### Cost comparison summary

| Scenario | Neptune DB Serverless | Neptune Analytics (always-on) | Neptune Analytics (pause 16h/day) |
|----------|----------------------|-------------------------------|-----------------------------------|
| Graph compute | ~$200 | ~$60–70 | ~$25–35 |
| VPC/NAT overhead | ~$35 | $0 | $0 |
| Storage/I/O | ~$10 | ~$1 | ~$1 |
| **Total** | **~$245** | **~$60–70** | **~$25–35** |
| Budget headroom for Athena, S3, Lambda | ~$55 | ~$230–240 | ~$265–275 |

Neptune Analytics is **3–8× cheaper** for this workload, leaving substantial budget for the S3 data lake, Athena queries, and Lambda functions.

---

## 3. Bulk Loading Differences

| Aspect | Neptune Database | Neptune Analytics |
|--------|-----------------|-------------------|
| **API** | POST to `/loader` endpoint | `CreateGraphUsingImportTask` or `StartImportTask` API |
| **Formats** | CSV (openCypher/Gremlin format), ntriples, nquads | CSV, Parquet, ntriples |
| **S3 requirement** | S3 bucket + VPC S3 Gateway Endpoint + IAM role on `rds.amazonaws.com` | S3 bucket + IAM role on `neptune-graph.amazonaws.com` |
| **Load into existing graph** | Yes (append) | Bulk import requires empty graph; use batch load or openCypher for incremental |
| **Parallelism** | Configurable (LOW/MEDIUM/HIGH) | Managed automatically |
| **Parquet support** | No | Yes |
| **Create graph + load in one step** | No (create cluster first, then load) | Yes (`CreateGraphUsingImportTask`) |

### Impact on this workload

The existing CSV files designed for Neptune Database bulk load (with `:ID`, `:LABEL`, `:START_ID`, `:END_ID`, `:TYPE` headers) are **compatible with Neptune Analytics** — both use the same openCypher CSV format. No reformatting is needed. Neptune Analytics additionally supports Parquet, which could simplify future data pipelines.

The one operational difference: Neptune Analytics bulk import (`StartImportTask`) requires an **empty graph**. For incremental updates (adding ClinVar edges, new TCGA cases), use the **batch load** API (for S3-staged data <50 GB) or openCypher `MERGE` statements. This matches the workload pattern: bulk load PrimeKG + TCGA once, then small incremental additions.

---

## 4. Graph Algorithm Support

This is the **decisive differentiator** for the Oncology Semantic Hub.

### Neptune Analytics — built-in algorithms (Sprint 2 requirements)

| Algorithm Category | Algorithms Available | Hub Use Case |
|-------------------|---------------------|--------------|
| **Centrality** | PageRank, Degree, Closeness Centrality | Rank gene importance in disease networks; identify hub genes in PPI |
| **Community Detection** | Louvain, Label Propagation, WCC, SCC | Discover functional gene modules; identify disease clusters |
| **Pathfinding** | BFS, Single-Source Shortest Path, Top-K Shortest Path, Source-Target Shortest Path, EgoNet | Drug-disease path analysis; biomarker pathway traversal |
| **Similarity** | Common Neighbors, Total Neighbors, Jaccard, Overlap | Link prediction for novel gene-disease associations |
| **Vector Search** | HNSW-based Top-K, Distance | Node embedding similarity for downstream ML |

Example query — PageRank on the PPI network to find hub genes:
```cypher
MATCH (g:gene_protein)
CALL neptune.algo.pageRank(g, {edgeLabels: ['ppi'], numOfIterations: 20})
YIELD rank
RETURN g.hugo_symbol, rank
ORDER BY rank DESC LIMIT 20
```

Example query — Louvain community detection on gene-disease network:
```cypher
MATCH (n) WHERE n:gene_protein OR n:disease
CALL neptune.algo.louvain(n, {edgeLabels: ['disease_protein', 'ppi']})
YIELD community
RETURN n.hugo_symbol, community
ORDER BY community
```

Example query — Shortest path from drug to disease:
```cypher
MATCH (dr:drug {drug_name: 'Olaparib'}), (d:disease {disease_name: 'ovarian cancer'})
CALL neptune.algo.shortestPath(dr, d, {edgeLabels: ['drug_target', 'ppi', 'disease_protein']})
YIELD path, distance
RETURN path, distance
```

### Neptune Database — no built-in algorithms

Neptune Database has **no built-in graph algorithms**. To run PageRank or community detection, you would need:

1. **Neptune ML** — requires SageMaker integration, training jobs, and inference endpoints. This is designed for ML model training (link prediction, node classification), not for running standard graph algorithms like PageRank or Louvain.
2. **Export + external processing** — export the graph to a framework like Apache Spark (GraphX), NetworkX, or DGL, run algorithms externally, and import results back. This adds significant pipeline complexity and cost.
3. **Custom openCypher** — implement algorithms manually in openCypher queries. Possible for simple cases (degree centrality) but impractical for iterative algorithms like PageRank or Louvain.

For Sprint 2's requirements (PageRank, community detection, link prediction, node embeddings), Neptune Database would require building and maintaining a separate analytics pipeline — exactly the complexity Neptune Analytics was designed to eliminate.

---

## 5. VPC and Networking Requirements

| Aspect | Neptune Database | Neptune Analytics |
|--------|-----------------|-------------------|
| **VPC** | **Required** — must deploy in VPC with private subnets | **Optional** — supports public endpoints |
| **NAT Gateway** | Required if Lambda/Fargate needs internet access | Not needed with public endpoint |
| **VPC Endpoints** | S3 Gateway Endpoint required for bulk load | Not needed |
| **Security Groups** | Required — configure ingress on port 8182 | Not needed with public endpoint (IAM auth enforced) |
| **Subnet Groups** | Required — at least 2 AZs | Not needed |
| **Private connectivity** | Default (VPC-only) | Optional via VPC endpoint |
| **Monthly networking cost** | ~$35 (NAT Gateway) + complexity | $0 |

### Impact on this workload

Neptune Analytics with a **public endpoint** dramatically simplifies the architecture:
- No VPC, subnets, NAT Gateway, or security groups needed for Neptune
- Lambda functions can call Neptune Analytics directly via HTTPS + IAM Sig4
- Saves ~$35/month on NAT Gateway alone
- Reduces CloudFormation template complexity by ~40%

Note: The S3 data lake and Athena don't require a VPC either. The only VPC requirement in the original architecture was driven by Neptune Database. With Neptune Analytics, the entire stack can run without a VPC (Lambda, API Gateway, Neptune Analytics, S3, Athena, Glue).

> **Security note:** Neptune Analytics public endpoints are always authenticated via IAM Sig4. There is no unauthenticated access. This provides equivalent security to VPC-based access for this workload.

---

## 6. Operational Complexity

| Aspect | Neptune Database (Serverless) | Neptune Analytics |
|--------|-------------------------------|-------------------|
| **Provisioning** | Create cluster → create subnet group → create instance → configure security groups → attach IAM roles | `CreateGraphUsingImportTask` — one API call creates graph + loads data |
| **Scaling** | Automatic within NCU range (but never to zero) | Resize m-NCU via `UpdateGraph` (no downtime); pause/resume |
| **Monitoring** | CloudWatch: NCUUtilization, BufferCacheHitRatio, MainRequestQueuePendingRequests | CloudWatch: CPUUtilization, GraphStorageUsagePercent, NumOpenCypherRequestsPerSec |
| **Backups** | Automated continuous backups + point-in-time restore | Manual snapshots (create before changes, restore when needed) |
| **Maintenance windows** | Required for engine updates | No maintenance windows |
| **Engine versions** | Must track and apply engine updates | Managed by AWS |
| **Cost when idle** | Minimum NCU runs 24/7 (~$200/month floor) | Pause graph → 10% cost; or delete + restore from snapshot |
| **Infrastructure as Code** | ~100 lines CloudFormation (VPC, subnets, SGs, cluster, instance, roles) | ~20 lines CloudFormation (graph + IAM role) |

### Operational verdict

Neptune Analytics is significantly simpler to operate. The "graph as a service" model means no cluster management, no VPC networking, no maintenance windows, and the ability to pause when not in use. For a research/discovery workload with a small team, this operational simplicity is a major advantage.

---

## 7. Risk Assessment

| Risk | Neptune Database | Neptune Analytics |
|------|-----------------|-------------------|
| **Data durability** | 6 copies across 3 AZs, continuous backups | In-memory; relies on snapshots + S3 source data for recovery |
| **Recovery time** | Point-in-time restore (minutes) | Restore from snapshot or re-import from S3 (minutes for this graph size) |
| **Vendor lock-in** | openCypher is an open standard; data in standard CSV | Same — openCypher + CSV/Parquet in S3 |
| **Service maturity** | GA since 2017, well-established | GA since late 2023, newer but stable |
| **Incremental updates** | Full ACID, straightforward | Batch load or openCypher MERGE — slightly more constrained for bulk import |
| **Future growth** | Scales to 128 TiB, 100K QPS | Scales to 4096 m-NCU (4 TiB in-memory) |

### Mitigations for Neptune Analytics risks

1. **Data durability:** Source data (PrimeKG CSVs, TCGA data) lives in S3. The graph can be fully reconstructed from S3 at any time. Take snapshots before incremental updates.
2. **Service maturity:** Neptune Analytics has been GA for over 2 years with steady feature additions (Louvain, smaller m-NCU sizes, pause/resume). AWS Prescriptive Guidance has published a full Well-Architected Framework review for it.
3. **Incremental updates:** The batch load API handles S3-staged incremental data well. For small updates (adding a few edges), openCypher MERGE works identically to Neptune Database.

---

## 8. Recommendation

### Use Neptune Analytics as the primary graph store

**Rationale:**

1. **Built-in algorithms are a hard requirement.** Sprint 2 needs PageRank, community detection, and similarity algorithms. Neptune Analytics provides these natively via `CALL neptune.algo.*`. Neptune Database would require building a separate SageMaker/Spark pipeline — adding months of work and ongoing operational burden.

2. **3–8× lower cost.** Neptune Analytics at 32 m-NCU costs ~$60–70/month (or ~$25–35 with pause). Neptune Database Serverless has a ~$245/month floor. The savings leave budget for the rest of the stack.

3. **No VPC required.** Eliminates NAT Gateway cost (~$35/month), reduces CloudFormation complexity by ~40%, and simplifies Lambda connectivity.

4. **Pause/resume.** For a research workload that may be idle evenings and weekends, pause reduces compute cost by up to 70%.

5. **Simpler operations.** One API call to create + load. No cluster management, no maintenance windows, no subnet groups.

6. **Vector search for Sprint 2 ML.** Built-in HNSW vector similarity enables node embedding search without external infrastructure.

7. **openCypher-only is fine.** The workload doesn't need Gremlin or SPARQL. Neptune Analytics' openCypher support covers all query patterns in the architecture design.

### What we give up (and why it's acceptable)

| Trade-off | Why acceptable |
|-----------|---------------|
| No continuous automated backups | Source data in S3; graph reconstructible in minutes. Manual snapshots before updates. |
| No Multi-AZ with 15 replicas | Research workload, not production OLTP. 0 replicas is fine. |
| No Gremlin/SPARQL | Not needed — architecture is openCypher-only by design. |
| No Neptune Streams (CDC) | Not needed — no downstream consumers of graph changes. |
| Newer service (GA 2023) | 2+ years GA, Well-Architected guidance published, steady feature releases. |

### Revised architecture cost estimate

| Resource | Configuration | Monthly Cost |
|----------|--------------|-------------|
| Neptune Analytics | 32 m-NCU, 0 replicas, pause 12h/day | ~$40–50 |
| S3 | ~10 GB Parquet + CSVs | ~$0.25 |
| Athena | ~50 queries/day, ~1 GB scanned/query | ~$25 |
| Glue Crawler | 1 run/week, 5 min | ~$2 |
| Lambda (API + ETL) | Occasional runs | ~$5 |
| **Total** | | **~$75–85/month** |

This is well under the $300/month budget, leaving room for growth (more data, more queries, additional services).

### Migration path if needs change

If the workload evolves to require high-concurrency OLTP (thousands of concurrent write transactions), Neptune Database can be adopted alongside Neptune Analytics:
- Keep Neptune Analytics for algorithms and analytical queries
- Add Neptune Database for transactional workloads
- Load data from Neptune Database snapshots into Analytics for periodic analysis

This is the pattern AWS recommends in their documentation: Neptune Database for OLTP, Neptune Analytics for OLAP/algorithms.

---

## 9. Required Changes to Architecture Design

The following sections of `aws-architecture-design.md` need updating:

1. **§2.1:** Change recommendation from "Neptune Database (Serverless)" to "Neptune Analytics (32 m-NCU)"
2. **§2.3:** Update bulk load commands from Neptune Loader API to `CreateGraphUsingImportTask` CLI
3. **§5.1:** Remove VPC, subnets, NAT Gateway, security groups, and Neptune cluster/instance resources. Replace with Neptune Analytics graph resource.
4. **§5.2:** Update cost estimate from ~$250–290 to ~$75–85/month
5. **§7 Phase 5:** Graph algorithms are now available immediately via Neptune Analytics (no separate Neptune ML setup needed). Move algorithm work from Phase 5 to Sprint 2.

---

## References

- [When to use Neptune Analytics vs Neptune Database](https://docs.aws.amazon.com/neptune-analytics/latest/userguide/neptune-analytics-vs-neptune-database.html)
- [Neptune Analytics algorithms](https://docs.aws.amazon.com/neptune-analytics/latest/userguide/algorithms.html)
- [Neptune Analytics bulk import from S3](https://docs.aws.amazon.com/neptune-analytics/latest/userguide/bulk-import-create-from-s3.html)
- [Neptune Analytics loading data](https://docs.aws.amazon.com/neptune-analytics/latest/userguide/loading-data.html)
- [Neptune Analytics cost optimization (Well-Architected)](https://docs.aws.amazon.com/prescriptive-guidance/latest/neptune-analytics-well-architected-framework/cost-optimization-pillar.html)
- [Neptune Database Serverless](https://docs.aws.amazon.com/neptune/latest/userguide/neptune-serverless.html)
- [Neptune Database Serverless capacity scaling](https://docs.aws.amazon.com/neptune/latest/userguide/neptune-serverless-capacity-scaling.html)
- [Amazon Neptune pricing](https://aws.amazon.com/neptune/pricing/)
- [Smaller capacity units for Neptune Analytics (AWS blog)](https://aws.amazon.com/blogs/database/introducing-smaller-capacity-units-for-amazon-neptune-analytics-up-to-75-cheaper-to-get-started-with-graph-analytics-workloads/)
