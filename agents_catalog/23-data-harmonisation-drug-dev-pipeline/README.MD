# Data Harmonisation for Drug Development Pipeline

This solution automatically collects, standardises, and enriches drug development pipeline data from pharmaceutical companies.

## Problem Statement

Harmonising data from disparate systems is time-consuming and costly. Pharmaceutical companies publish their drug/product development pipelines on their websites, but analyzing this data systematically presents several challenges:

- Manual downloading is often required
- Each company reports data in their own format
- Key data fields (indication, compound name, etc.) are reported inconsistently
- No standardized ontologies or controlled vocabularies are applied

An automated solution that retrieves, extracts, compiles to a common data model, and standardises with ontologies is essential to make the data FAIR (Findable, Accessible, Interoperable, Reusable) and ready for upstream analysis.

## Solution Overview

This notebook demonstrates how to extract and process pharmaceutical pipeline data using prompts without coding.

### Step 1: Data Collection
Using Fetch MCP to collect data from Novartis, Novo Nordisk, and Pfizer pipeline web pages, extracting the data and saving it as individual JSON objects.

### Step 2: Common Data Model Creation
Analyzing each JSON file to create a unified data model that represents all collected data. This step combines data from the three companies into a single dataset.

### Step 3: Data Standardisation and Enrichment
Automatically detecting appropriate ontologies to standardize the data, ensuring consistency across all entries.

The final data is saved as a JSON file, ready for downstream analysis.

For implementation details, please see `./pipeline_data/PROJECT_SUMMARY.md` and `README.md`. This folder was generated entirely using Q CLI.

### Data Collection
We utilize web scraping techniques to collect pipeline data from companies' official websites. This solution respects `robots.txt` directives and only collects data from websites that permit it.