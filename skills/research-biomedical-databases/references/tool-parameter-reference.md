# Tool Parameter Reference

Complete parameter schemas for all 28 Biomni Gateway tools. Most tools accept a natural language `prompt` (required) plus optional parameters for direct API access.

## Common Pattern

Most tools follow this pattern:
- `prompt` (string, required): Natural language query
- `endpoint` (string, optional): Direct API URL for precise queries
- `max_results` (integer, optional): Limit number of results
- `verbose` (boolean, optional): Return detailed response information

Exceptions to this pattern are noted below.

---

## Protein & Structure Tools

### query_uniprot
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query (e.g., "Find human insulin receptor protein") |
| endpoint | string | no | Direct UniProt API URL (e.g., "https://rest.uniprot.org/uniprotkb/P01308") |
| max_results | integer | no | Maximum results to return |

### query_alphafold
**IMPORTANT: Does NOT accept `prompt`. Requires `uniprot_id`.**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| uniprot_id | string | YES | UniProt accession ID (e.g., "P01308") |
| endpoint | string | no | "prediction", "summary", or "annotations" |
| residue_range | string | no | Residue range "start-end" (e.g., "1-100") |
| download | boolean | no | Download structure files |
| output_dir | string | no | Directory to save downloaded files (use with download: true) |
| file_format | string | no | "pdb" or "cif" |
| model_version | string | no | "v4" (latest), "v3", "v2", "v1" |
| model_number | integer | no | 1-5 (1 = highest confidence) |

### query_interpro
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about protein domains/families |
| endpoint | string | no | Direct path (e.g., "/entry/interpro/IPR023411") |
| max_results | integer | no | Results per page |

### query_pdb
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about protein structures |
| query | object | no | Direct structured query in RCSB Search API format (overrides prompt) |
| max_results | integer | no | Maximum results |

### query_pdb_identifiers
**IMPORTANT: Does NOT accept `prompt`. Requires `identifiers` array.**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| identifiers | array[string] | YES | List of PDB IDs (e.g., ["1ZNI", "4HHB"]) |
| return_type | string | no | "entry", "assembly", "polymer_entity", etc. |
| download | boolean | no | Download PDB structure files |
| attributes | array[string] | no | Specific attributes to retrieve |

### query_stringdb
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about protein interactions |
| endpoint | string | no | Full URL (overrides prompt) |
| download_image | boolean | no | Download network image |
| output_dir | string | no | Save directory |
| verbose | boolean | no | Detailed response |

### query_emdb
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about EM structures |
| endpoint | string | no | Full API endpoint |
| verbose | boolean | no | Detailed results |

### query_pride
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about proteomics data |
| endpoint | string | no | Full endpoint URL |
| max_results | integer | no | Maximum results |
| verbose | boolean | no | Detailed results |

---

## Genomic Variant Tools

### query_clinvar
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query (e.g., "Find pathogenic BRCA1 variants") |
| search_term | string | no | Direct ClinVar search term |
| max_results | integer | no | Maximum results |

### query_gnomad
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about genetic variants |
| gene_symbol | string | no | Direct gene symbol (e.g., "BRCA1") — faster than prompt |
| verbose | boolean | no | Detailed results |

### query_dbsnp
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about SNPs |
| search_term | string | no | Direct dbSNP syntax search |
| max_results | integer | no | Maximum results |

### query_ensembl
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about genomic data |
| endpoint | string | no | Direct API endpoint (e.g., "lookup/symbol/human/BRCA2") |
| verbose | boolean | no | Detailed results |

### query_ucsc
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about genomic data |
| endpoint | string | no | Full URL or endpoint with parameters |
| verbose | boolean | no | Detailed results |

### query_gwas_catalog
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about GWAS data |
| endpoint | string | no | Full API endpoint URL |
| max_results | integer | no | Maximum results |

### query_regulomedb
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about regulatory elements |
| endpoint | string | no | Direct API endpoint |
| verbose | boolean | no | Detailed results |

---

## Pathway & Target Tools

### query_reactome
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about biological pathways |
| endpoint | string | no | Direct endpoint or full URL |
| download | boolean | no | Download pathway diagram |
| output_dir | string | no | Save directory |
| verbose | boolean | no | Detailed results |

### query_opentarget
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about targets/diseases |
| query | string | no | Direct GraphQL query string (more precise) |
| variables | object | no | Variables for GraphQL query |
| verbose | boolean | no | Detailed results |

### query_monarch
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about phenotypes/diseases |
| endpoint | string | no | Direct API endpoint |
| max_results | integer | no | Maximum results |
| verbose | boolean | no | Detailed results |

### query_gtopdb
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about drug targets/ligands |
| endpoint | string | no | Full API endpoint URL |
| verbose | boolean | no | Detailed results |

### query_openfda
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about FDA data |
| endpoint | string | no | Direct endpoint |
| max_results | integer | no | Maximum results |
| search_params | object | no | Search parameter mapping |
| sort_params | object | no | Sort parameter mapping |
| count_params | string | no | Field to count |
| skip_results | integer | no | Pagination skip |
| verbose | boolean | no | Detailed results |

### query_clinicaltrials
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about clinical trials |
| endpoint | string | no | Direct ClinicalTrials.gov endpoint |
| max_results | integer | no | Page size |
| verbose | boolean | no | Detailed results |

---

## Cancer & Expression Tools

### query_cbioportal
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about cancer genomics |
| endpoint | string | no | API endpoint path (e.g., "/studies/brca_tcga/patients") |
| verbose | boolean | no | Detailed results |

### query_geo
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about expression data |
| search_term | string | no | Direct GEO syntax search |
| max_results | integer | no | Maximum results |
| verbose | boolean | no | Detailed results |

---

## Specialized Tools

### query_jaspar
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about TF binding profiles |
| endpoint | string | no | API path (e.g., "/matrix/MA0002.2/") |
| verbose | boolean | no | Detailed results |

### query_mpd
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about mouse phenotypes |
| endpoint | string | no | Full API endpoint |
| verbose | boolean | no | Detailed results |

### query_synapse
**NOTE: Results may show `access_restricted: true` — these require Synapse web approval.**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about biomedical datasets |
| query_term | string | no | Specific search terms |
| return_fields | array[string] | no | Fields to return |
| max_results | integer | no | Max results (default 20, max 50) |
| query_type | string | no | Entity type: "file", "project", "folder" |
| verbose | boolean | no | Detailed results |

### query_worms
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about marine species |
| endpoint | string | no | Full URL or endpoint |
| verbose | boolean | no | Detailed results |

### query_paleobiology
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| prompt | string | YES | Natural language query about fossil records |
| endpoint | string | no | API endpoint or full URL |
| verbose | boolean | no | Detailed results |
