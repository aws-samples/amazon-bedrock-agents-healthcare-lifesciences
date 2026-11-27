# Oncology Biomarker Semantic Hub — Requirements Document

**Status:** Exploration Phase  
**Date:** 2026-04-30  
**Repository:** amazon-bedrock-agents-healthcare-lifesciences

---

## 1. Objective

Build a semantic hub that provides a knowledge graph representation of multi-modal cancer biomarker datasets and their associated ontologies. The hub will integrate clinical, genomic, proteomic, and pharmacological data from public portals (GDC/TCGA, cBioPortal) with curated biomedical knowledge bases, enabling:

- Unified querying across heterogeneous cancer data sources
- Biomarker discovery through graph traversal and link prediction
- Drug-target-disease relationship exploration
- AI/ML-ready graph embeddings for downstream precision oncology tasks

---

## 2. Primary Data Sources

### 2.1 NCI Genomic Data Commons (GDC) — TCGA and Beyond

**What it is:** The authoritative repository for NCI cancer genomics programs (TCGA, TARGET, CPTAC, FM). Property graph data model with ~86,000 cases across 78 projects.

**API:** `https://api.gdc.cancer.gov`

| Endpoint | URL | What to extract |
|----------|-----|-----------------|
| `projects` | `/projects` | Project metadata, disease types, program names |
| `cases` | `/cases` | Patient demographics, diagnoses, exposures, family history, follow-ups, treatments |
| `files` | `/files` | File metadata (MAF, VCF, expression, methylation, CNV) |
| `annotations` | `/annotations` | Data quality annotations |
| `data` | `/data/{uuid}` | Download actual data files by UUID |
| `manifest` | `/manifest` | Bulk download manifests for GDC Data Transfer Tool |

**Key data to download (open access):**

| Data Type | GDC Data Type | Format | Typical Size |
|-----------|--------------|--------|-------------|
| Somatic mutations | Masked Somatic Mutation | MAF | ~50MB per project |
| Gene expression | Gene Expression Quantification | TSV (STAR counts) | ~2GB per project |
| Copy number | Copy Number Segment | SEG | ~500MB per project |
| Methylation | Methylation Beta Value | TSV | ~5GB per project |
| Clinical | Clinical Supplement | BCR XML/TSV | ~100MB per project |
| Protein expression | Protein Expression Quantification | TSV (RPPA) | ~50MB per project |

**How to download:**
```bash
# Clinical + biospecimen metadata via API (JSON)
curl 'https://api.gdc.cancer.gov/cases?filters={"op":"=","content":{"field":"project.program.name","value":"TCGA"}}&fields=diagnoses.primary_diagnosis,demographic.gender,demographic.race&size=5000&format=json'

# Bulk file download via manifest + GDC Data Transfer Tool
curl 'https://api.gdc.cancer.gov/manifest?filters={"op":"and","content":[{"op":"=","content":{"field":"cases.project.project_id","value":"TCGA-BRCA"}},{"op":"=","content":{"field":"data_type","value":"Masked Somatic Mutation"}}]}' > manifest.txt
gdc-client download -m manifest.txt
```

**GraphQL endpoint:** `https://api.gdc.cancer.gov/v0/graphql` — supports complex nested queries across the data model.

**Data dictionary:** `https://github.com/NCI-GDC/gdcdictionary` — JSON Schema YAML files defining all entities, properties, links, and validation rules.

### 2.2 cBioPortal

**What it is:** Study-centric portal for cancer genomics visualization and analysis. Hosts 400+ cancer studies including all TCGA datasets, MSK-IMPACT, GENIE, and institutional cohorts.

**API:** `https://www.cbioportal.org/api` (Swagger/OpenAPI at `/api/v3/api-docs`)

| Endpoint Group | Key Endpoints | What to extract |
|---------------|--------------|-----------------|
| Studies | `GET /studies` | Study metadata, cancer types, citations |
| Patients | `GET /studies/{id}/patients` | Patient IDs, clinical attributes |
| Samples | `GET /studies/{id}/samples` | Sample IDs, sample types, patient mapping |
| Clinical Data | `GET /studies/{id}/clinical-data` | All clinical attributes (patient + sample level) |
| Mutations | `GET /molecular-profiles/{id}/mutations` | Somatic mutations with Hugo Symbol, HGVSp, variant classification |
| CNA | `GET /molecular-profiles/{id}/discrete-copy-number` | Discrete CNA values (-2 to +2) per gene |
| Expression | `GET /molecular-profiles/{id}/molecular-data` | mRNA expression, z-scores |
| Structural Variants | `GET /structural-variants/fetch` | Fusions, translocations |
| Gene Panels | `GET /gene-panels/{id}` | Panel gene lists (e.g., MSK-IMPACT468) |
| Genes | `GET /genes/{entrezGeneId}` | Gene metadata, aliases |

**Python access:**
```python
from bravado.client import SwaggerClient
cbioportal = SwaggerClient.from_url(
    'https://www.cbioportal.org/api/v3/api-docs',
    config={"validate_requests": False, "validate_responses": False, "validate_swagger_spec": False}
)
# Get all TCGA studies
studies = cbioportal.Studies.getAllStudiesUsingGET(keyword="tcga").result()
# Get mutations for TCGA-BRCA
muts = cbioportal.Mutations.getMutationsInMolecularProfileBySampleListIdUsingGET(
    molecularProfileId="brca_tcga_mutations",
    sampleListId="brca_tcga_all",
    projection="DETAILED"
).result()
```

**R access:** `cBioPortalData` (Bioconductor) or `cbioportalR` (tidyverse-compatible).

**Datahub:** `https://github.com/cBioPortal/datahub` — all public study data files in cBioPortal's TSV format, downloadable directly.


---

## 3. Existing Open-Source Knowledge Graphs (Starting Points)

### 3.1 PrimeKG — Recommended Primary Starting Point

**Paper:** Chandak et al., "Building a knowledge graph to enable precision medicine" (Scientific Data, 2023, 453 citations)

**Scale:** 129,375 nodes, 4,050,249 edges, 10 node types, 30 edge types

**Node types:** gene/protein, disease, drug, biological_process, molecular_function, cellular_component, anatomy, pathway, effect/phenotype, exposure

**20 integrated data sources:** MONDO, DisGeNET, DrugBank, Drug Central, Gene Ontology, HPO, Reactome, UBERON, CTD, SIDER, Bgee, STRING, BioGRID, HuRI, UMLS, Entrez Gene, HGNC, Mayo Clinic, Orphanet, Disease Ontology

**Download:**
```bash
# Single CSV file from Harvard Dataverse (~200MB)
wget https://dataverse.harvard.edu/api/access/datafile/6180620 -O primekg.csv
# Or via Python
pip install pyDataverse
```
**Direct URL:** `https://doi.org/10.7910/DVN/IXA7BM`

**GitHub:** `https://github.com/mims-harvard/PrimeKG` — includes build scripts, tutorials, and instructions for updating with new data.

**Why start here:** Covers 17,080 diseases with drug indications/contraindications/off-label edges. Multimodal (graph + text clinical features). Easy to load (<5 seconds). Well-documented update process. Harvard-maintained.

**Gap for our use case:** No patient-level data (no TCGA cases/samples). No somatic mutation data. No gene expression matrices. This is the knowledge backbone — we need to overlay TCGA/cBioPortal patient data on top.

### 3.2 Clinical Knowledge Graph (CKG)

**Paper:** Santos et al., Nature Biotechnology 2022

**Scale:** 16M+ nodes, 220M+ relationships

**Tech stack:** Neo4j graph database, Python, Dash dashboards

**GitHub:** `https://github.com/MannLabs/CKG` (520 stars)

**Docs:** `https://ckg.readthedocs.io`

**Setup:**
```bash
git clone https://github.com/MannLabs/CKG.git
cd CKG && conda activate ckgenv && python setup.py install
# Requires Neo4j Community Edition installed locally
```

**What it provides:** Full Neo4j database with automated import from 25+ biomedical databases (UniProt, STRING, STITCH, DrugBank, DisGeNET, Reactome, KEGG, PharmGKB, SIDER, OncoKB, etc.). Automated analytics pipelines. Proteomics-focused.

**Gap:** Heavy setup (Neo4j + multiple database downloads). Proteomics-centric, less genomics/mutation coverage. Not cancer-specific.

### 3.3 DRKG (Drug Repurposing Knowledge Graph)

**GitHub:** `https://github.com/gnn4dr/DRKG`

**Scale:** 97,238 entities, 5,874,261 triplets, 107 relation types

**Sources:** DrugBank, Hetionet, GNBR, String, IntAct, DGIdb

**Download:** TSV triplets file directly from GitHub releases (~100MB)

**Format:** Simple `(head, relation, tail)` triplets — easy to load into any graph framework.

**Gap:** Drug-repurposing focused. No patient data. No cancer-specific biomarker annotations.

### 3.4 Hetionet / SPOKE

**Hetionet:** 47K nodes, 2.25M edges, 11 node types, 24 edge types. Available as Neo4j dump or TSV. `https://github.com/hetio/hetionet`

**SPOKE:** Extension of Hetionet with 27 node types, 53 edge types. Limited to 137 diseases but demonstrated patient-level overlay. `https://spoke.ucsf.edu`

### 3.5 PheKnowLator

**Paper:** Callahan et al., "An open source knowledge graph ecosystem for the life sciences" (Scientific Data, 2024)

**GitHub:** `https://github.com/callahantiff/PheKnowLator`

**What it provides:** Fully automated FAIR KG construction from OWL ontologies. Customizable knowledge representation (instance-based or subclass-based). SPARQL endpoint. Pre-built KGs available.

**Best for:** If you want to build a KG from scratch using formal OWL ontologies with reasoning support.

### 3.6 kgw Python Package

**GitHub:** `https://github.com/robert-haas/kgw`

**What it does:** Downloads and converts multiple biomedical KGs (PrimeKG, CKG, HALD, Oregano, Monarch) into SQLite, CSV, JSONL, or GraphML formats. Provides schema visualization and statistics.

**Use case:** Quick evaluation and comparison of existing KGs before committing to one.

```bash
pip install kgw
# Download and convert PrimeKG to SQLite
kgw fetch primekg
kgw convert primekg --format sqlite
```


---

## 4. Additional Data Sources for Enrichment

### 4.1 Gene-Disease Associations

| Source | What | Download | License |
|--------|------|----------|---------|
| **DisGeNET** | 84K curated gene-disease associations | `https://www.disgenet.org/downloads` (TSV, requires free account) | CC BY-NC-SA 4.0 |
| **ClinVar** | Variant-disease clinical significance | `https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz` | Public domain |
| **COSMIC** | Somatic mutation catalogue (cancer-specific) | `https://cancer.sanger.ac.uk/cosmic/download` (requires registration) | Academic free |
| **OncoKB** | Precision oncology gene annotations | `https://www.oncokb.org/apiAccess` (API, requires license) | Academic free |
| **IntOGen** | Cancer driver genes and mutations | `https://www.intogen.org/download` (TSV) | CC0 |

### 4.2 Drug-Target-Disease

| Source | What | Download | License |
|--------|------|----------|---------|
| **DrugBank** | 14K+ drugs with targets, pathways, interactions | `https://go.drugbank.com/releases` (XML, requires academic license) | Academic free |
| **Drug Central** | Drug-disease indications/contraindications/off-label | `https://drugcentral.org/ActiveDownload` (SQL dump) | CC BY-SA 4.0 |
| **PharmGKB** | Pharmacogenomics relationships | `https://api.pharmgkb.org/v1/download/file/data/` (TSV) | CC BY-SA 4.0 |
| **ChEMBL** | Bioactivity data for drug-like molecules | `https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/` (SQL/SDF) | CC BY-SA 3.0 |
| **DGIdb** | Drug-gene interactions | `https://www.dgidb.org/downloads` (TSV) | MIT |

### 4.3 Pathways and Functional Annotations

| Source | What | Download | License |
|--------|------|----------|---------|
| **Reactome** | Curated biological pathways | `https://reactome.org/download/current/` (BioPAX, TSV) | CC0 |
| **KEGG** | Metabolic and signaling pathways | `https://rest.kegg.jp/` (REST API, restricted redistribution) | Academic free |
| **Gene Ontology** | Molecular function, biological process, cellular component | `http://purl.obolibrary.org/obo/go/go-basic.obo` | CC BY 4.0 |
| **MSigDB** | Gene sets (hallmarks, curated, GO, oncogenic) | `https://www.gsea-msigdb.org/gsea/downloads.jsp` (GMT) | CC BY 4.0 |

### 4.4 Protein-Protein Interactions

| Source | What | Download | License |
|--------|------|----------|---------|
| **STRING** | Functional protein associations (scored) | `https://string-db.org/cgi/download` (TSV, 9606 = human) | CC BY 4.0 |
| **BioGRID** | Curated physical + genetic interactions | `https://downloads.thebiogrid.org/BioGRID` (TAB3) | MIT |
| **IntAct** | Molecular interaction data | `https://ftp.ebi.ac.uk/pub/databases/intact/current/` (MI-TAB) | CC BY 4.0 |
| **HuRI** | Human reference interactome (binary PPIs) | `http://www.interactome-atlas.org/download` (TSV) | CC BY 4.0 |

### 4.5 Ontologies (Schema Layer)

| Ontology | Purpose | Download | ID Format |
|----------|---------|----------|-----------|
| **NCIt** | Cancer terminology backbone | `http://purl.obolibrary.org/obo/ncit.obo` | NCIT:C##### |
| **MONDO** | Disease harmonization across ontologies | `http://purl.obolibrary.org/obo/MONDO.obo` | MONDO:####### |
| **HPO** | Phenotype abnormalities | `http://purl.obolibrary.org/obo/hp.obo` | HP:####### |
| **GO** | Gene function | `http://purl.obolibrary.org/obo/go/go-basic.obo` | GO:####### |
| **Disease Ontology** | Disease classification | `http://purl.obolibrary.org/obo/doid.obo` | DOID:##### |
| **Sequence Ontology** | Variant types | `http://purl.obolibrary.org/obo/so.obo` | SO:####### |
| **UBERON** | Anatomy | `http://purl.obolibrary.org/obo/uberon/ext.obo` | UBERON:####### |
| **ChEBI** | Chemical entities | `http://purl.obolibrary.org/obo/chebi.obo` | CHEBI:##### |


---

## 5. Design Specifications

### 5.1 Recommended Approach: PrimeKG + Cancer Data Overlay

Rather than building from scratch, extend PrimeKG (the best-documented, most comprehensive open-source biomedical KG) with cancer-specific patient-level data from GDC/cBioPortal:

```
Layer 1: PrimeKG (knowledge backbone)
  └── 129K nodes: diseases, genes, drugs, pathways, phenotypes, anatomy
  └── 4M edges: gene-disease, drug-disease, PPI, pathway membership, etc.

Layer 2: Cancer biomarker overlay (new)
  └── TCGA/cBioPortal patient cases, samples, somatic mutations, CNA, expression
  └── Links patient-level observations to PrimeKG gene/disease/drug nodes

Layer 3: Literature enrichment (new)
  └── NER-extracted gene-disease-drug triples from PubMed abstracts
  └── LLM-validated relationships (per OncoNet Ontology approach)
```

### 5.2 Graph Schema

**Node types (extending PrimeKG's 10 types with 4 new cancer-specific types):**

```
EXISTING (from PrimeKG):
  gene_protein     — Entrez Gene ID (e.g., 7157 for TP53)
  disease          — MONDO ID (e.g., MONDO:0007254 for breast cancer)
  drug             — DrugBank ID (e.g., DB00773 for Etoposide)
  biological_process — GO ID (e.g., GO:0006915 for apoptotic process)
  molecular_function — GO ID
  cellular_component — GO ID
  pathway          — Reactome ID (e.g., R-HSA-69278)
  anatomy          — UBERON ID
  effect_phenotype — HPO ID
  exposure         — MeSH ID

NEW (cancer biomarker layer):
  project          — GDC project_id (e.g., TCGA-BRCA)
  case             — GDC case UUID or TCGA barcode
  sample           — GDC sample UUID, linked to case
  variant          — chrom:pos:ref:alt (genomic coordinate key)
```

**Edge types (extending PrimeKG's 30 types):**

```
EXISTING (from PrimeKG, key subset):
  protein_protein          — PPI (STRING, BioGRID, HuRI)
  disease_protein          — gene-disease association (DisGeNET)
  drug_protein             — drug target/enzyme/carrier/transporter (DrugBank)
  drug_disease             — indication / contraindication / off-label (Drug Central)
  disease_phenotype        — disease-phenotype association (HPO)
  protein_biological_process — gene function (GO via Entrez)
  protein_pathway          — pathway membership (Reactome)
  disease_disease          — disease hierarchy (MONDO)
  anatomy_protein          — tissue-specific expression (Bgee)
  drug_effect              — drug side effects (SIDER)

NEW (cancer biomarker layer):
  case_in_project          — case → project membership
  sample_from_case         — sample → case (one-to-many)
  sample_has_mutation      — sample → variant (from MAF files)
  variant_in_gene          — variant → gene_protein (Hugo Symbol mapping)
  sample_has_cna           — sample → gene_protein (with CNA value property)
  sample_has_expression    — sample → gene_protein (with expression value property)
  case_has_diagnosis       — case → disease (primary diagnosis → MONDO mapping)
  case_received_treatment  — case → drug (treatment → DrugBank mapping)
```

### 5.3 Technology Stack

| Component | Recommended | Alternative | Rationale |
|-----------|------------|-------------|-----------|
| **Graph database** | Amazon Neptune | Neo4j Community | Neptune for AWS-native; Neo4j if local dev preferred |
| **Graph query** | openCypher (Neptune) or Gremlin | SPARQL | openCypher is most intuitive for property graphs |
| **ETL / build** | Python (pandas, pyarrow, requests) | — | PrimeKG is already Python-based |
| **KG framework** | NetworkX + iGraph (analysis), DGL/PyG (ML) | — | PrimeKG loads into NetworkX in <5s |
| **Ontology management** | OWL via Protégé, pronto (Python) | — | For formal ontology editing and reasoning |
| **API layer** | FastAPI | — | Serve graph queries to agents |
| **Embedding** | PyTorch Geometric (PyG) or DGL | — | For KG embedding and link prediction |
| **Visualization** | Streamlit + pyvis or Gephi | — | Interactive graph exploration |

### 5.4 Implementation Phases

**Phase 1 — Bootstrap (Week 1-2):**
1. Download PrimeKG CSV from Harvard Dataverse
2. Load into NetworkX/iGraph, validate schema
3. Download GDC clinical metadata for all TCGA projects via API
4. Download cBioPortal mutation/CNA data for TCGA studies via API
5. Map TCGA disease types to MONDO IDs (PrimeKG's disease ontology)
6. Map Hugo Symbols to Entrez Gene IDs (PrimeKG's gene identifiers)

**Phase 2 — Integration (Week 3-4):**
7. Add case/sample/variant nodes to PrimeKG graph
8. Create edges: case→disease, sample→gene (mutations, CNA, expression)
9. Load into Neptune or Neo4j
10. Build Cypher/Gremlin query templates for common biomarker queries
11. Add ClinVar pathogenicity annotations to variant nodes
12. Add OncoKB/IntOGen cancer driver annotations to gene nodes

**Phase 3 — Enrichment (Week 5-6):**
13. Add PharmGKB pharmacogenomics edges
14. Add COSMIC mutation frequency data
15. Literature enrichment: BioBERT NER on cancer biomarker PubMed abstracts
16. Build Strands agent with graph query tools
17. Deploy on AgentCore with Streamlit UI

### 5.5 Data Volume Estimates

| Component | Nodes | Edges | Storage |
|-----------|-------|-------|---------|
| PrimeKG base | 129K | 4.0M | ~200MB CSV |
| TCGA cases (33 cancer types) | ~11K cases, ~23K samples | ~34K case/sample edges | ~50MB |
| Somatic mutations (TCGA) | ~3M unique variants | ~4M sample-variant edges | ~2GB |
| CNA events (TCGA) | reuses gene nodes | ~500K sample-gene-CNA edges | ~200MB |
| Expression (TCGA) | reuses gene nodes | ~200M sample-gene-expr edges (sparse) | ~5GB |
| ClinVar annotations | ~1M variant annotations | ~1M variant-disease edges | ~500MB |
| **Total estimated** | **~3.3M nodes** | **~210M edges** | **~8GB** |

### 5.6 Key ID Mappings Required

| From | To | Mapping Source |
|------|----|---------------|
| TCGA project (e.g., TCGA-BRCA) | MONDO disease ID | Manual mapping table (33 entries) |
| Hugo Symbol (e.g., TP53) | Entrez Gene ID (e.g., 7157) | HGNC (`https://www.genenames.org/download/custom/`) |
| DrugBank ID | Drug name | DrugBank vocabulary file |
| TCGA barcode | GDC UUID | GDC API case lookup |
| ICD-O-3 code | MONDO ID | MONDO cross-references |
| ClinVar variant ID | chrom:pos:ref:alt | ClinVar variant_summary.txt |


---

## 6. Related Work and References

### 6.1 Key Papers

| Paper | Year | Relevance |
|-------|------|-----------|
| Chandak et al., "Building a knowledge graph to enable precision medicine" (PrimeKG) | 2023 | **Primary starting point.** 129K nodes, 4M edges, 20 sources, Harvard Dataverse download. |
| Silva et al., "Ontologies and Knowledge Graphs in Oncology Research" | 2022 | Systematic review of 141 papers. Categorizes ontology/KG usage patterns. Identifies NCIt, GO, MONDO as key ontologies. |
| Karim et al., "From LLMs to KGs for Biomarker Discovery in Cancer" (OncoNet) | 2024 | OncoNet Ontology with Cancer/Biomarker/Feature classes. BioBERT+SciBERT NER pipeline. LLM-based KG enrichment. |
| Tripathi et al., "MINDS: Multimodal Integration of Oncology Data System" | 2023 | Metadata-centric approach: 41K cases from CRDC consolidated into 25MB. AWS lakehouse architecture. |
| Santos et al., "Clinical Knowledge Graph" (CKG) | 2022 | Neo4j-based, 16M nodes, 220M relationships. Automated import from 25+ databases. |
| Hasan et al., "Knowledge Graph-Enabled Cancer Data Analytics" | 2020 | Cancer registry KG prototype using Louisiana Tumor Registry data. |
| Callahan et al., "PheKnowLator: An open source KG ecosystem" | 2024 | FAIR KG construction from OWL ontologies with customizable representation. |

### 6.2 Curated Resource Lists

- **awesome-biomedical-knowledge-graphs:** `https://github.com/robert-haas/awesome-biomedical-knowledge-graphs` — comprehensive survey + `kgw` Python package for downloading/converting KGs
- **cBioPortal Datahub:** `https://github.com/cBioPortal/datahub` — all public study data files
- **GDC Data Dictionary:** `https://github.com/NCI-GDC/gdcdictionary` — JSON Schema definitions for all GDC entities

---

## 7. Open Questions for Design Phase

1. **Graph database choice:** Neptune (managed, AWS-native, scales) vs. Neo4j (richer ecosystem, Cypher, community tools, local dev friendly). Neptune supports both openCypher and SPARQL. Neo4j has better visualization tooling.

2. **Expression data granularity:** Including all sample×gene expression edges (~200M for TCGA) makes the graph very large. Options:
   - Store only differentially expressed genes per sample (reduces to ~5M edges)
   - Store expression as node properties on sample nodes (JSON blob)
   - Keep expression in a separate columnar store (S3 Tables/Athena) and reference from graph

3. **Variant representation:** Individual variant nodes (chrom:pos:ref:alt) vs. gene-level mutation summary. Individual variants enable ClinVar/COSMIC annotation but create millions of nodes.

4. **Scope of cancer types:** Start with a single cancer type (e.g., TCGA-BRCA, best characterized) or all 33 TCGA types from the start?

5. **Update cadence:** PrimeKG provides update scripts. GDC/cBioPortal data is relatively stable. How often should the hub be refreshed?

6. **Agent integration:** How should the Strands agent query the graph? Direct Cypher/Gremlin queries via tools? Or a pre-computed summary layer?

---

## 8. Recommended First Steps

```
1. pip install kgw && kgw fetch primekg && kgw convert primekg --format sqlite
   → Explore PrimeKG schema, validate node/edge types

2. python -c "
   from bravado.client import SwaggerClient
   cbio = SwaggerClient.from_url('https://www.cbioportal.org/api/v3/api-docs',
       config={'validate_requests':False,'validate_responses':False,'validate_swagger_spec':False})
   studies = cbio.Studies.getAllStudiesUsingGET(keyword='tcga').result()
   print(f'{len(studies)} TCGA studies found')
   "
   → Validate cBioPortal API access

3. curl 'https://api.gdc.cancer.gov/cases?filters=\{"op":"=","content":\{"field":"project.project_id","value":"TCGA-BRCA"\}\}&size=1&pretty=true'
   → Validate GDC API access

4. Build TCGA-project-to-MONDO mapping table (33 entries)
5. Build Hugo-Symbol-to-Entrez mapping from HGNC
6. Write ETL: GDC clinical → case/sample nodes → link to PrimeKG disease nodes
7. Write ETL: cBioPortal mutations → variant nodes → link to PrimeKG gene nodes
8. Load combined graph into Neo4j (local dev) or Neptune (deployment)
```
