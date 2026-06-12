# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2025-06-03

### 0.1.0 Added

- Initial development release

### 0.1.0 Changed

- Updated all Lambda function runtimes to Python 3.12 (except for PyTorch-based containers)

### 0.1.1 Changed

- Updated solution to use existing networking infrastructure if available

### 0.1.2 Added

- Added `open-life-sciences-tool` MCP server integration with 155 tools across 24 modular life sciences database servers
  - Proteomics: UniProt, InterPro, Pfam, STRING, PRIDE, neXtProt (8 tools)
  - Structural Biology: PDB, AlphaFold DB, CATH, SCOP (6 tools)
  - Genomics: NCBI, Ensembl, ClinVar, gnomAD, dbSNP, GEO, SRA, COSMIC, 1000 Genomes, DDBJ, ENCODE (18 tools)
  - Pathways: KEGG, Reactome, BioCyc, WikiPathways, IntAct, PathBank, Pathway Commons (7 tools)
  - Clinical: OMIM, DrugBank, ChEMBL, PharmGKB, OpenTargets, ClinicalTrials.gov, FDA, BindingDB (10 tools)
  - Cheminformatics: PubChem, ChemSpider, ZINC, RDKit, SwissDock, ADMET (8 tools)
  - Plus 18 additional specialized domains: ontologies, model organisms, microbiology, immunology, metabolomics, epigenomics, neuroscience, imaging, ecology, agriculture, cell biology, healthcare, biobanking, pipelines, data standards, cloud platforms, and AI/ML resources
- Deployed via AgentCore Gateway with OAuth2 authentication following established CloudFormation patterns
- Includes comprehensive documentation, deployment scripts, integration tests, and client configuration examples