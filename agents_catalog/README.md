Select and customize from a library of specialized agents across the value chain. You can view examples of supervisor agents that combine some of these agents [here](../multi_agent_collaboration/)

Some of the categories of agents are listed below: 

## Multi-Modal Data Integration: 
Process and correlate various patient data modalities to provide a comprehensive research perspective.
- Biomarker Database Analyst Agent: Analyzes structured clinical and RNA-seq data
- Variant Interpreter Agent: Interprets genetic variant annotations
- Medical Imaging Agent: Processes CT scans using asynchronous workflows
- Pathology Agent: Analyzes Whole Slide Images (WSIs) for pathology interpretation
- Radiology Report Agent: Validates Chest X-ray findings based on ACR guidelines

## Data Enrichment: 
Link data entities to external biological knowledge bases.
- Biological Pathways Agent: Explores disease mechanisms via the Reactome graph
- Omics Signature Agent: Enriches entities using databases like OMIM, ENSEMBL, and UniProt

## Evidence Research: 
Retrieve and summarize insights from scientific literature.
- Clinical Evidence Researcher Agent: Searches PubMed and internal knowledge bases
- Wiley Online Library Agent: Performs full-text search via Wiley's API

## Statistical Analysis: 
Analytic and visualization support for research insights.
- Statistician Agent: Performs survival regression and creates Kaplan-Meier and descriptive plots using lifelines library

## Clinical Trials: 
Analyze trials and support protocol drafting
- Clinical Study Search Agent: Retrieves data from ClinicalTrials.gov, helping users explore prior study designs by condition, intervention, or sponsor. It highlights eligibility criteria, endpoints, and outcome measures from past trials.
- Clinical Trial Protocol Generator Agent: Builds new study protocols using best practices and the Common Data Model (CDM). It assists in drafting and refining sections such as inclusion/exclusion criteria, endpoints, and statistical plans.

## Competitive Intelligence:
Monitor and analyze public data sources
- Web Search Agent: Uses the Tavily API to retrieve relevant, filtered news and web content with built-in content guardrails
- USPTO Search Agent: Queries patent filings by topic or assignee using the USPTO Open Data API
- SEC 10-K Agent: Extracts financial insights and trends from company filings
