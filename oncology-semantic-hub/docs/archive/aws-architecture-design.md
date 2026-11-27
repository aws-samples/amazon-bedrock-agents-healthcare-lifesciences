# Oncology Biomarker Semantic Hub — AWS Architecture Design

**Status:** Design Phase  
**Date:** 2026-04-30  
**Depends on:** `oncology-semantic-hub-requirements.md`

---

## 1. Architecture Pattern: Virtual Knowledge Graph

Based on the [AWS Neptune + S3 Virtual Knowledge Graph pattern](https://aws.amazon.com/blogs/database/create-a-virtual-knowledge-graph-with-amazon-neptune-and-an-amazon-s3-data-lake/), we split data by its nature:

- **Neptune (property graph):** Highly connected knowledge — entities, relationships, ontology structure. Queried via openCypher. This is the biomarker knowledge graph (genes, diseases, drugs, pathways, phenotypes, and their relationships).
- **S3 data lake (Parquet/CSV):** High-volume tabular data — patient-level observations (mutations, expression, CNA). Queried via Athena SQL. This is the TCGA/cBioPortal multi-modal dataset.
- **Federation:** A single query can traverse the graph in Neptune and join with patient-level data in S3 via Athena, without duplicating data.
- **Hybrid search (semantic recall):** a customer-managed **Amazon Bedrock Knowledge Base on Amazon S3 Vectors** (Titan Text Embeddings v2, 1024-dim cosine) over TCGA study descriptions + curated PubMed abstracts. The L3 agent calls it via `bedrock-agent-runtime:Retrieve` (the `knowledge_search` tool) to get passages + citations, then pivots via OLS to Neptune/Athena for precision — i.e. **Vector recall → OLS → Graph + SQL → cited answer**. Serverless (no OpenSearch); `kb_id` in SSM. See [`hybrid-search-design.md`](hybrid-search-design.md).

```
┌─────────────────────────────────────────────────────────────────┐
│                    Oncology Semantic Hub                         │
│                                                                 │
│  ┌──────────────────────┐     ┌──────────────────────────────┐  │
│  │  Neptune Analytics    │     │  S3 Data Lake (Parquet)      │  │
│  │  (32 m-NCU)          │     │                              │  │
│  │                       │     │  tcga_mutations/             │  │
│  │  Nodes:               │     │  tcga_expression/            │  │
│  │   gene, disease, drug │     │  tcga_cna/                   │  │
│  │   pathway, phenotype  │     │  tcga_clinical/              │  │
│  │   anatomy, exposure   │     │                              │  │
│  │   project, case,      │     │  Partitioned by:             │  │
│  │   sample              │     │   project_id / data_type     │  │
│  │                       │     │                              │  │
│  │  Built-in algorithms: │     ├──────────────────────────────┤  │
│  │   PageRank, Louvain,  │     │  AWS Glue Data Catalog       │  │
│  │   shortest path,      │     │  (schema over Parquet)       │  │
│  │   vector search       │     ├──────────────────────────────┤  │
│  │                       │     │  Amazon Athena               │  │
│  │  Query: openCypher    │     │  (SQL query engine)          │  │
│  │  Auth: IAM SigV4      │     │  Query: SQL                  │  │
│  │  No VPC required      │     │                              │  │
│  └──────────┬───────────┘     └──────────────┬───────────────┘  │
│             │                                 │                  │
│             │    ┌────────────────────┐        │                  │
│             └────┤  Application-Layer  ├────────┘                  │
│                  │  Join (Lambda/API)  │                           │
│                  │  Neptune + Athena   │                           │
│                  │  merged in Python   │                           │
│                  └────────┬───────────┘                           │
│                           │                                      │
│             ┌─────────────┴──────────────┐                       │
│             │  API Layer (FastAPI/Lambda) │                       │
│             │  + Strands Agent Tools      │                       │
│             └─────────────┬──────────────┘                       │
│                           │                                      │
│             ┌─────────────┴──────────────┐                       │
│             │  Streamlit UI / AgentCore  │                       │
│             └────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

### Why this split?

| Data | Store | Reason |
|------|-------|--------|
| Gene-disease associations (84K edges) | Neptune | Highly connected, traversal queries |
| Drug-target interactions (26K edges) | Neptune | Graph traversal for drug repurposing |
| PPI network (642K edges) | Neptune | Network analysis, shortest paths |
| Pathway membership (85K edges) | Neptune | Enrichment analysis |
| Disease ontology hierarchy (64K edges) | Neptune | Subsumption queries |
| Patient cases + samples (~34K nodes) | Neptune | Connected to disease/project nodes |
| Somatic mutations (~4M rows) | S3/Athena | High volume, columnar scans |
| Gene expression (~200M rows) | S3/Athena | Very high volume, aggregation queries |
| Copy number (~500K rows) | S3/Athena | Tabular, filter/aggregate |
| Methylation (~5B values) | S3/Athena | Massive, columnar access |


---

## 2. Neptune Graph Database Design

### 2.1 Neptune Analytics (chosen over Neptune Database)

See `neptune-db-vs-analytics.md` for the full evaluation. Neptune Analytics wins on cost (3-8×), built-in graph algorithms, and operational simplicity (no VPC).

| Feature | Neptune Analytics |
|---------|------------------|
| **Query language** | openCypher |
| **Bulk load** | `CreateGraphUsingImportTask` from S3 (CSV or Parquet) |
| **Incremental load** | `neptune.load()` procedure or `StartImportTask` API |
| **Graph algorithms** | 25+ built-in: PageRank, Louvain, WCC, shortest path, closeness centrality, vector search |
| **S3 integration** | `neptune.read()` for single-file reads |
| **VPC** | Not required — public endpoint with IAM SigV4 auth |
| **Pause/resume** | Yes — pay ~10% while paused |
| **Sizing** | Memory-based (m-NCU). 32 m-NCU = 32 GiB, fits our ~8GB graph 4× over |
| **Cost** | ~$60-70/month always-on, ~$25-35/month with pause during off-hours |

### 2.2 openCypher Data Model for Neptune

Neptune's openCypher bulk loader expects CSV files in S3 with specific headers.

**Node files** (one per node type):

```csv
# nodes_gene.csv
:ID,entrez_id:Int,hugo_symbol:String,gene_type:String,:LABEL
gene_7157,7157,TP53,protein-coding,gene_protein
gene_672,672,BRCA1,protein-coding,gene_protein
```

```csv
# nodes_disease.csv
:ID,mondo_id:String,disease_name:String,:LABEL
disease_MONDO_0007254,MONDO:0007254,breast carcinoma,disease
disease_MONDO_0005012,MONDO:0005012,ovarian cancer,disease
```

```csv
# nodes_drug.csv
:ID,drugbank_id:String,drug_name:String,drug_group:String,:LABEL
drug_DB00773,DB00773,Etoposide,approved,drug
```

```csv
# nodes_case.csv
:ID,case_id:String,tcga_barcode:String,gender:String,race:String,vital_status:String,:LABEL
case_abc123,abc123,TCGA-A2-A04P,female,white,alive,case
```

```csv
# nodes_sample.csv
:ID,sample_id:String,sample_type:String,tumor_stage:String,:LABEL
sample_def456,def456,Primary Tumor,stage iia,sample
```

**Edge files** (one per relationship type):

```csv
# edges_disease_protein.csv  (no :ID column — Neptune Analytics auto-generates edge IDs)
:START_ID,:END_ID,:TYPE,source:String,score:Double
disease_MONDO_0007254,gene_7157,disease_protein,DisGeNET,0.95
```

```csv
# edges_drug_protein.csv
:START_ID,:END_ID,:TYPE,action:String
drug_DB00773,gene_7153,drug_target,inhibitor
```

```csv
# edges_sample_from_case.csv
:START_ID,:END_ID,:TYPE
sample_def456,case_abc123,sample_from_case
```

```csv
# edges_case_has_diagnosis.csv
:START_ID,:END_ID,:TYPE,primary_diagnosis:String
case_abc123,disease_MONDO_0007254,case_has_diagnosis,Infiltrating duct carcinoma NOS
```

### 2.3 Bulk Loading into Neptune Analytics

**Option A: Create graph with data in one step (recommended for Sprint 1)**

```bash
# Create graph and import data from S3 in a single API call
aws neptune-graph create-graph-using-import-task \
  --graph-name oncology-semantic-hub \
  --role-arn arn:aws:iam::<account>:role/NeptuneAnalyticsLoadRole \
  --source "s3://oncology-semantic-hub-data-<account>-us-west-2/neptune/" \
  --format OPEN_CYPHER \
  --min-provisioned-memory 32 \
  --max-provisioned-memory 32 \
  --public-connectivity \
  --no-deletion-protection \
  --replica-count 0 \
  --region us-east-1

# Check import status
aws neptune-graph get-import-task --task-identifier <task-id>
```

> **Flags explained:**
> - `--replica-count 0` — no standby replicas (saves cost for dev/research)
> - `--no-deletion-protection` — allows graph deletion without extra step (dev only)
> - `--public-connectivity` — public endpoint with IAM SigV4 auth (no VPC needed)
> - `32 m-NCU` — 32 GiB memory, fits our ~8GB graph with room for query working memory

**Option B: Load into existing graph**

```bash
# Start import into an existing empty graph
aws neptune-graph start-import-task \
  --graph-identifier <graph-id> \
  --role-arn arn:aws:iam::<account>:role/NeptuneAnalyticsLoadRole \
  --source "s3://oncology-semantic-hub-data-<account>-us-west-2/neptune/" \
  --format OPEN_CYPHER
```

**Option C: Incremental load via openCypher procedure**

```cypher
// Load additional CSV files after initial import
CALL neptune.load({
  source: "s3://oncology-semantic-hub-data/neptune/nodes_case.csv",
  format: "csv",
  region: "us-west-2"
})
```

**Expected load time:** ~2-5 minutes for ~4M edges at 32 m-NCU.

### 2.4 Incremental Enrichment via neptune.read()

After initial import, use `neptune.read()` to add data without full re-import (Sprint 2: ClinVar, COSMIC, PharmGKB):

```cypher
// Read a single CSV from S3 and MERGE new edges into the graph
CALL neptune.read({
    source: "s3://oncology-semantic-hub-data-<account>-us-west-2/enrichment/clinvar_gene_disease.csv",
    format: "CSV"
})
YIELD row
MATCH (g:gene_protein {entrez_id: toInteger(row.entrez_id)})
MATCH (d:disease {mondo_id: row.mondo_id})
MERGE (g)-[:clinvar_association {clinical_significance: row.significance, review_status: row.review_status}]->(d)
```

> **Note:** `neptune.read()` requires a single S3 object URI (not a prefix). Each file should be <20MB for reliable performance.

### 2.5 Export for Downstream ML

Export the enriched graph to S3 as Parquet for graph embedding pipelines:

```bash
aws neptune-graph start-export-task \
  --graph-identifier <graph-id> \
  --role-arn arn:aws:iam::<account>:role/NeptuneAnalyticsLoadRole \
  --format PARQUET \
  --parquet-type COLUMNAR \
  --destination s3://oncology-semantic-hub-data-<account>-us-west-2/export/ \
  --region us-west-2
```

### 2.4 Example openCypher Queries

```cypher
// Find all genes associated with breast cancer
MATCH (d:disease {mondo_id: 'MONDO:0007254'})-[:disease_protein]->(g:gene_protein)
RETURN g.hugo_symbol, g.entrez_id
ORDER BY g.hugo_symbol

// Find drugs that target BRCA1-associated genes
MATCH (d:disease {disease_name: 'breast carcinoma'})-[:disease_protein]->(g:gene_protein)<-[:drug_target]-(dr:drug)
RETURN dr.drug_name, g.hugo_symbol, dr.drug_group

// Shortest path between a drug and a disease through the PPI network
MATCH path = shortestPath(
  (dr:drug {drug_name: 'Olaparib'})-[*..5]-(d:disease {disease_name: 'ovarian cancer'})
)
RETURN path

// Find all TCGA-BRCA cases with their diagnoses
MATCH (p:project {project_id: 'TCGA-BRCA'})<-[:case_in_project]-(c:case)-[:case_has_diagnosis]->(d:disease)
RETURN c.tcga_barcode, d.disease_name, c.vital_status

// Cross-reference: genes associated with a disease + TCGA mutation counts
// Uses APPLICATION-LAYER JOIN pattern (see §2.5 below)
//
// Step 1 (Neptune): Get disease-associated genes
MATCH (d:disease {disease_name: 'breast carcinoma'})-[:disease_protein]->(g:gene_protein)
RETURN g.hugo_symbol AS gene, g.entrez_id AS entrez_id
//
// Step 2 (Athena): Get mutation counts for those genes
// SELECT hugo_symbol, COUNT(*) AS mutation_count
// FROM oncology_semantic_hub.tcga_mutations
// WHERE project_id='TCGA-BRCA' AND hugo_symbol IN ('TP53','PIK3CA',...)
// GROUP BY hugo_symbol ORDER BY mutation_count DESC
//
// Step 3 (Python/Lambda): Join the two result sets
```

### 2.5 Federation: Application-Layer Joins

The original design proposed `neptune.read()` for in-graph S3 federation. Per the design review, this has critical limitations (single-file URIs only, memory-intensive, cross-product with MATCH). **The revised approach uses application-layer joins:**

```python
# Lambda/FastAPI: query Neptune + Athena separately, merge in Python
def cross_reference(disease_name, project_id):
    # Step 1: Neptune openCypher — graph traversal
    genes = neptune_query(f"""
        MATCH (d:disease {{disease_name:'{disease_name}'}})-[:disease_protein]->(g:gene_protein)
        RETURN g.hugo_symbol AS gene
    """)
    # Step 2: Athena SQL — columnar scan with partition pruning
    gene_csv = ",".join(f"'{g}'" for g in genes)
    mutations = athena_query(f"""
        SELECT hugo_symbol, COUNT(*) AS mutations, COUNT(DISTINCT case_id) AS cases
        FROM tcga_mutations WHERE project_id='{project_id}' AND hugo_symbol IN ({gene_csv})
        GROUP BY hugo_symbol
    """)
    # Step 3: Merge in Python
    return merge(genes, mutations, on='hugo_symbol')
```

Each query runs in its optimal engine. No memory pressure on Neptune. Works with partitioned Parquet.

### 2.7 Query Patterns at Scale

The semantic hub supports three query tiers, from simple lookups to cross-system analytics:

**Tier 1 — Pure graph queries (Neptune Analytics, sub-second):**
```cypher
// Biomarker discovery: genes → pathways → drugs for a disease
MATCH (d:disease {disease_name:'breast carcinoma'})-[:disease_protein]->(g:gene_protein)
      -[:protein_pathway]->(p:pathway)<-[:protein_pathway]-(g2:gene_protein)
      <-[:drug_target]-(dr:drug)
WHERE dr.drug_group = 'approved'
RETURN DISTINCT dr.drug_name, g.hugo_symbol, p.name AS pathway
LIMIT 50

// Graph algorithm: rank genes by centrality in the PPI network
CALL neptune.algo.pageRank({edgeLabels: ['protein_protein']})
YIELD node, rank
WHERE 'gene_protein' IN labels(node)
RETURN node.hugo_symbol AS gene, rank ORDER BY rank DESC LIMIT 20

// Community detection: find gene clusters
CALL neptune.algo.louvain({edgeLabels: ['protein_protein','disease_protein']})
YIELD node, community
WHERE 'gene_protein' IN labels(node)
RETURN community, collect(node.hugo_symbol) AS genes, count(*) AS size
ORDER BY size DESC LIMIT 10
```

**Tier 2 — Pure data lake queries (Athena, seconds):**
```sql
-- Mutation landscape across cancer types
SELECT project_id, hugo_symbol,
       COUNT(*) AS mutations,
       COUNT(DISTINCT case_id) AS affected_cases
FROM oncology_semantic_hub.tcga_mutations
WHERE variant_classification IN ('Missense_Mutation','Nonsense_Mutation')
GROUP BY project_id, hugo_symbol
ORDER BY affected_cases DESC LIMIT 100;
```

**Tier 3 — Cross-system analytics (application-layer join, seconds):**
```python
# "Which approved drugs target the top 10 most mutated genes in TCGA-BRCA?"
# Step 1: Athena — top mutated genes
top_genes = athena_query("""
    SELECT hugo_symbol, COUNT(DISTINCT case_id) AS cases
    FROM tcga_mutations WHERE project_id='TCGA-BRCA'
    GROUP BY hugo_symbol ORDER BY cases DESC LIMIT 10
""")
# Step 2: Neptune — drugs targeting those genes
gene_list = [r['hugo_symbol'] for r in top_genes]
drugs = neptune_query(f"""
    MATCH (g:gene_protein)<-[:drug_target]-(dr:drug)
    WHERE g.hugo_symbol IN {gene_list} AND dr.drug_group = 'approved'
    RETURN g.hugo_symbol AS gene, collect(dr.drug_name) AS drugs
""")
# Step 3: Merge
return merge(top_genes, drugs, on='hugo_symbol')
```


---

## 3. S3 Data Lake Design

### 3.1 Bucket Structure

```
s3://oncology-semantic-hub-data/
├── neptune/                          # Neptune bulk load CSVs
│   ├── nodes_gene.csv
│   ├── nodes_disease.csv
│   ├── nodes_drug.csv
│   ├── nodes_case.csv
│   ├── nodes_sample.csv
│   ├── edges_disease_protein.csv
│   ├── edges_drug_protein.csv
│   ├── edges_ppi.csv
│   ├── edges_pathway.csv
│   └── ...
│
├── lake/                             # Parquet data lake (Athena-queryable)
│   ├── tcga_mutations/               # Somatic mutations (MAF-derived)
│   │   ├── project_id=TCGA-BRCA/
│   │   │   └── mutations.parquet
│   │   ├── project_id=TCGA-LUAD/
│   │   └── ...
│   │
│   ├── tcga_expression/              # Gene expression (STAR counts)
│   │   ├── project_id=TCGA-BRCA/
│   │   └── ...
│   │
│   ├── tcga_cna/                     # Copy number segments
│   │   ├── project_id=TCGA-BRCA/
│   │   └── ...
│   │
│   ├── tcga_clinical/                # Clinical data (flattened)
│   │   ├── project_id=TCGA-BRCA/
│   │   └── ...
│   │
│   └── tcga_methylation/             # Methylation beta values
│       ├── project_id=TCGA-BRCA/
│       └── ...
│
├── ontologies/                       # OWL/OBO ontology files
│   ├── mondo.obo
│   ├── go-basic.obo
│   ├── hp.obo
│   └── ncit.obo
│
└── primekg/                          # PrimeKG source data
    ├── kg_giant.csv
    ├── drug_features.csv
    └── disease_features.csv
```

### 3.2 Parquet Schemas

**tcga_mutations** (derived from GDC MAF files):

| Column | Type | Source |
|--------|------|--------|
| `case_id` | STRING | GDC case UUID |
| `sample_id` | STRING | GDC sample UUID |
| `project_id` | STRING | e.g., TCGA-BRCA (partition key) |
| `hugo_symbol` | STRING | Gene name |
| `entrez_gene_id` | INT | For joining to Neptune gene nodes |
| `chromosome` | STRING | e.g., chr17 |
| `start_position` | BIGINT | Genomic coordinate |
| `end_position` | BIGINT | |
| `reference_allele` | STRING | |
| `tumor_seq_allele2` | STRING | Variant allele |
| `variant_classification` | STRING | e.g., Missense_Mutation |
| `variant_type` | STRING | SNP, DNP, INS, DEL |
| `hgvsp_short` | STRING | e.g., p.V600E |
| `t_alt_count` | INT | Variant allele count |
| `t_ref_count` | INT | Reference allele count |

**tcga_expression** (derived from GDC STAR counts):

| Column | Type | Source |
|--------|------|--------|
| `case_id` | STRING | |
| `sample_id` | STRING | |
| `project_id` | STRING | Partition key |
| `entrez_gene_id` | INT | |
| `hugo_symbol` | STRING | |
| `tpm_unstranded` | FLOAT | Transcripts per million |
| `fpkm_unstranded` | FLOAT | |
| `stranded_first` | INT | Raw count |

**tcga_cna** (derived from cBioPortal discrete CNA):

| Column | Type | Source |
|--------|------|--------|
| `case_id` | STRING | |
| `sample_id` | STRING | |
| `project_id` | STRING | Partition key |
| `hugo_symbol` | STRING | |
| `entrez_gene_id` | INT | |
| `cna_value` | INT | -2, -1, 0, 1, 2 |

### 3.3 Glue Catalog and Athena

```bash
# Create Glue database
aws glue create-database --database-input '{"Name": "oncology_semantic_hub"}'

# Run crawler to auto-detect Parquet schemas
aws glue create-crawler \
  --name oncology-hub-crawler \
  --role arn:aws:iam::<account>:role/GlueServiceRole \
  --database-name oncology_semantic_hub \
  --targets '{"S3Targets": [{"Path": "s3://oncology-semantic-hub-data/lake/"}]}'

aws glue start-crawler --name oncology-hub-crawler
```

**Example Athena queries:**

```sql
-- Top mutated genes in TCGA-BRCA
SELECT hugo_symbol, COUNT(*) as mutation_count,
       COUNT(DISTINCT case_id) as affected_cases
FROM oncology_semantic_hub.tcga_mutations
WHERE project_id = 'TCGA-BRCA'
  AND variant_classification IN ('Missense_Mutation','Nonsense_Mutation','Frame_Shift_Del','Frame_Shift_Ins')
GROUP BY hugo_symbol
ORDER BY affected_cases DESC
LIMIT 20;

-- Expression of TP53 across cancer types
SELECT project_id, AVG(tpm_unstranded) as avg_tpm,
       STDDEV(tpm_unstranded) as std_tpm
FROM oncology_semantic_hub.tcga_expression
WHERE hugo_symbol = 'TP53'
GROUP BY project_id
ORDER BY avg_tpm DESC;
```


---

## 4. ETL Pipeline

### 4.1 Pipeline Steps

```
Step 1: Download PrimeKG
  └── Harvard Dataverse → S3 (primekg/kg_giant.csv)

Step 2: Transform PrimeKG → Neptune CSV
  └── Python script: parse kg_giant.csv → separate node/edge CSVs
  └── Map node types to ~label, generate ~id from node_index
  └── Output: s3://oncology-semantic-hub-data/neptune/

Step 3: Download GDC clinical metadata
  └── GDC API /cases endpoint → JSON → flatten to case/sample nodes
  └── Map TCGA project → MONDO disease ID (33-entry lookup table)
  └── Output: nodes_case.csv, nodes_sample.csv, edges_case_*.csv

Step 4: Download GDC molecular data
  └── GDC API /files + gdc-client → MAF, expression, CNA files
  └── Transform to Parquet, partition by project_id
  └── Output: s3://oncology-semantic-hub-data/lake/tcga_*/

Step 5: Download cBioPortal supplementary data
  └── cBioPortal API → mutations, CNA for non-TCGA studies (MSK-IMPACT, GENIE)
  └── Merge with GDC data in lake

Step 6: Bulk load Neptune
  └── Neptune loader: S3 CSVs → Neptune graph

Step 7: Crawl S3 lake
  └── Glue crawler → Athena tables

Step 8: Validate
  └── Run test queries on Neptune (openCypher) and Athena (SQL)
  └── Verify cross-references (gene IDs match, disease IDs match)
```

### 4.2 ETL Technology

| Step | Tool | Trigger |
|------|------|---------|
| Download PrimeKG | Python (requests) | Manual / Step Functions |
| Transform PrimeKG | Python (pandas) | Lambda or Glue ETL job |
| GDC API extraction | Python (requests) | Lambda or Glue ETL job |
| GDC file download | gdc-client CLI | EC2 or Fargate task |
| Parquet conversion | Python (pyarrow) | Glue ETL job |
| Neptune bulk load | Neptune Loader API | Step Functions |
| Glue crawl | Glue Crawler | Step Functions |

**Orchestration:** AWS Step Functions state machine that runs the full pipeline end-to-end.

---

## 5. Infrastructure (CloudFormation / CDK)

### 5.1 Core Resources

```yaml
Resources:
  # --- S3 Bucket ---
  DataBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub oncology-semantic-hub-data-${AWS::AccountId}-${AWS::Region}
      VersioningConfiguration:
        Status: Enabled

  # --- Neptune Analytics Graph ---
  # NOTE: Neptune Analytics graphs are created via API/CLI, not CloudFormation
  # (as of 2026, no native CFn resource type). Use a Custom Resource or CLI:
  #
  #   aws neptune-graph create-graph \
  #     --graph-name oncology-semantic-hub \
  #     --min-provisioned-memory 32 \
  #     --max-provisioned-memory 32 \
  #     --public-connectivity \
  #     --region us-west-2
  #
  # Or create-graph-using-import-task to create + load in one step.

  # --- IAM Role for Neptune Analytics S3 access ---
  NeptuneAnalyticsLoadRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: NeptuneAnalyticsLoadRole
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: neptune-graph.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: S3AndKmsAccess
          PolicyDocument:
            Statement:
              - Effect: Allow
                Action: [s3:GetObject, s3:PutObject, s3:ListBucket]
                Resource:
                  - !GetAtt DataBucket.Arn
                  - !Sub ${DataBucket.Arn}/*
              - Effect: Allow
                Action: [kms:DescribeKey, kms:Decrypt, kms:GenerateDataKey]
                Resource: !Sub arn:aws:kms:${AWS::Region}:${AWS::AccountId}:key/*
                Condition:
                  ForAllValues:StringEquals:
                    kms:EncryptionContextKeys:
                      - aws:neptune-graph:graphId
                      - aws:neptune-graph:graphExportId

  # --- Glue Data Catalog ---
  GlueDatabase:
    Type: AWS::Glue::Database
    Properties:
      CatalogId: !Ref AWS::AccountId
      DatabaseInput:
        Name: oncology_semantic_hub

  GlueCrawler:
    Type: AWS::Glue::Crawler
    Properties:
      Name: oncology-hub-crawler
      Role: !GetAtt GlueRole.Arn
      DatabaseName: oncology_semantic_hub
      Targets:
        S3Targets:
          - Path: !Sub s3://${DataBucket}/lake/

  GlueRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: glue.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole
      Policies:
        - PolicyName: S3ReadForCrawler
          PolicyDocument:
            Statement:
              - Effect: Allow
                Action: [s3:GetObject, s3:ListBucket]
                Resource:
                  - !GetAtt DataBucket.Arn
                  - !Sub ${DataBucket.Arn}/lake/*

  # --- Athena Workgroup (cost control) ---
  AthenaWorkgroup:
    Type: AWS::Athena::WorkGroup
    Properties:
      Name: oncology-semantic-hub
      WorkGroupConfiguration:
        ResultConfiguration:
          OutputLocation: !Sub s3://${DataBucket}/athena-results/
        BytesScannedCutoffPerQuery: 1073741824  # 1 GB limit per query
```

**No VPC required.** Neptune Analytics supports public endpoints with IAM SigV4 authentication. Lambda and Fargate tasks access Neptune Analytics and external APIs (GDC, cBioPortal) over the public internet — no NAT Gateway, no subnets, no security groups.

**Neptune Notebook for interactive exploration:**

```bash
# Deploy a Neptune Analytics notebook via CloudFormation
# See: https://docs.aws.amazon.com/neptune-analytics/latest/userguide/create-notebook-cfn.html
aws cloudformation deploy \
  --template-file https://aws-neptune-customer-samples.s3.amazonaws.com/neptune-analytics/notebooks/neptune-analytics-notebook.yaml \
  --stack-name oncology-hub-notebook \
  --parameter-overrides GraphId=<graph-id> \
  --capabilities CAPABILITY_IAM \
  --region us-west-2
```

### 5.2 Estimated Costs (us-west-2)

| Resource | Configuration | Monthly Cost |
|----------|--------------|-------------|
| Neptune Analytics | 32 m-NCU, always-on | ~$65 |
| Neptune Analytics (with pause) | Paused 12h/day (nights/weekends) | ~$35 |
| S3 | ~10GB Parquet + CSVs | ~$0.25 |
| Athena | ~50 queries/day, 1GB limit/query | ~$25 |
| Glue Crawler | 1 run/week, 5 min | ~$2 |
| Lambda (ETL) | Occasional runs | ~$5 |
| **Total (always-on)** | | **~$97/month** |
| **Total (with pause)** | | **~$67/month** |

> No VPC, NAT Gateway, or Neptune DB instances needed. Neptune Analytics supports
> public endpoints with IAM SigV4 auth. Pause/resume saves ~50% during off-hours.

---

## 6. Agent Integration

### 6.1 Strands Agent Tools

The Strands agent gets three tools to query the semantic hub:

```python
@tool
def query_knowledge_graph(cypher_query: str) -> str:
    """Execute an openCypher query against the Neptune knowledge graph.
    Use for: gene-disease associations, drug targets, pathway analysis,
    PPI network traversal, patient case lookups."""
    # Neptune openCypher endpoint via boto3 neptune-data client
    ...

@tool
def query_patient_data(sql_query: str) -> str:
    """Execute a SQL query against the TCGA patient data lake via Athena.
    Use for: mutation frequencies, expression levels, CNA events,
    clinical data aggregations across cancer types."""
    # Athena via boto3 athena client
    ...

@tool
def get_graph_schema() -> str:
    """Return the knowledge graph schema: node types, edge types,
    key properties, and example queries."""
    # Static schema description for LLM context
    ...
```

### 6.2 Example Agent Interactions

```
User: "What genes are most frequently mutated in breast cancer and also
       targeted by approved drugs?"

Agent plan:
  1. query_knowledge_graph: Find genes associated with breast cancer
     MATCH (d:disease {disease_name:'breast carcinoma'})-[:disease_protein]->(g:gene_protein)
     RETURN g.hugo_symbol, g.entrez_id

  2. query_patient_data: Get mutation frequencies for those genes
     SELECT hugo_symbol, COUNT(DISTINCT case_id) as mutated_cases
     FROM tcga_mutations WHERE project_id='TCGA-BRCA'
     AND hugo_symbol IN ('TP53','PIK3CA','CDH1',...)
     GROUP BY hugo_symbol ORDER BY mutated_cases DESC

  3. query_knowledge_graph: Find drugs targeting the top mutated genes
     MATCH (g:gene_protein)<-[:drug_target]-(dr:drug)
     WHERE g.hugo_symbol IN ['TP53','PIK3CA','CDH1']
     AND dr.drug_group = 'approved'
     RETURN g.hugo_symbol, dr.drug_name
```

---

## 7. Implementation Plan

| Phase | Week | Deliverable |
|-------|------|-------------|
| **Phase 1: Data Prep** | 1 | Download PrimeKG, GDC clinical data, cBioPortal mutations. Transform PrimeKG to Neptune CSV format. Convert TCGA MAFs to Parquet. |
| **Phase 2: Infrastructure** | 2 | Deploy Neptune Serverless + S3 bucket + Glue catalog via CloudFormation. Bulk load PrimeKG into Neptune. Crawl Parquet lake. |
| **Phase 3: Integration** | 3 | Add TCGA case/sample nodes to Neptune. Create cross-reference edges (case→disease, variant→gene). Validate with test queries. |
| **Phase 4: Agent** | 4 | Build Strands agent with Neptune + Athena tools. Deploy on AgentCore. Streamlit UI. |
| **Phase 5: Enrichment** | 5-6 | Add ClinVar, COSMIC, PharmGKB edges. Literature NER pipeline. Neptune Analytics for graph ML. |

---

## 8. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Graph query language | **openCypher** | More intuitive than SPARQL for property graphs. Better LLM query generation. |
| Graph database | **Neptune Analytics (32 m-NCU)** | 3-8× cheaper than Neptune Database Serverless. Built-in graph algorithms (PageRank, Louvain, shortest path, vector search). No VPC required. Pause/resume for cost savings. See `neptune-db-vs-analytics.md`. |
| Patient data store | **S3 Parquet + Athena** | Mutations/expression are tabular, high-volume. Parquet gives columnar compression. Athena is serverless SQL. Avoids bloating the graph. |
| Federation | **Application-layer joins** | Query Neptune (openCypher) and Athena (SQL) separately, merge in Python/Lambda. More reliable than `neptune.read()` which requires single-file URIs and is memory-intensive. |
| Starting KG | **PrimeKG** | Best documented, most comprehensive (129K nodes, 4M edges, 20 sources). Single CSV download. Harvard-maintained with update scripts. |
| ID scheme | **Entrez Gene + MONDO + DrugBank** | Matches PrimeKG's existing identifiers. Avoids re-mapping. |
| VPC | **None** | Neptune Analytics supports public endpoints with IAM SigV4 auth. Eliminates NAT Gateway (~$35/month) and VPC complexity. |
