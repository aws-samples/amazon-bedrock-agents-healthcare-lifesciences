# Common Data Model for Pharmaceutical Pipeline Data

## Overview
This document describes the harmonized common data model used to combine pipeline data from Novo Nordisk, Pfizer, and Novartis into a unified structure. The model standardizes field names, values, and data types across all three companies.

## File Structure

### Main Output File
- **File**: `harmonized_pipeline_data.json`
- **Size**: 76.2 KB
- **Total Candidates**: 77 (47 Novo Nordisk + 10 Pfizer + 20 Novartis)
- **Generated**: 2025-07-03T20:30:52

## Data Model Schema

### 1. Root Level Structure
```json
{
  "metadata": { ... },
  "companies": [ ... ],
  "unified_pipeline": [ ... ],
  "therapeutic_areas": [ ... ],
  "development_phases": [ ... ],
  "compound_types": [ ... ],
  "mechanisms_of_action": [ ... ],
  "summary_statistics": { ... }
}
```

### 2. Metadata Section
Contains harmonization information and data provenance:

| Field | Type | Description |
|-------|------|-------------|
| `harmonization_date` | ISO DateTime | When the harmonization was performed |
| `version` | String | Version of the data model |
| `description` | String | Description of the dataset |
| `data_sources` | Array | Source information for each company |
| `total_companies` | Integer | Number of companies included |
| `total_candidates` | Integer | Total number of pipeline candidates |

### 3. Companies Section
Array of company-specific information:

| Field | Type | Description |
|-------|------|-------------|
| `company_name` | String | Full company name |
| `company_code` | String | 3-letter company code (NVO, PFE, NVS) |
| `data_source` | String | URL of original data source |
| `extraction_date` | String | Date when data was extracted |
| `pipeline_overview` | Object | Company's pipeline description |
| `total_candidates` | Integer | Number of candidates for this company |
| `phase_distribution` | Object | Count of candidates by development phase |

### 4. Unified Pipeline Section (Core Data)
Array of harmonized candidate records with standardized schema:

#### Candidate Record Schema
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `candidate_id` | String | Yes | Unique identifier (format: {COMPANY}_{###}) |
| `company` | String | Yes | Company name |
| `company_code` | String | Yes | 3-letter company code |
| `compound_name` | String | Yes | Name of the compound/drug |
| `compound_code` | String | No | Internal company compound code |
| `brand_name` | String | No | Commercial brand name (if available) |
| `indication` | String | Yes | Medical condition being treated |
| `therapeutic_area` | String | Yes | Normalized therapeutic area |
| `development_phase` | String | Yes | Normalized development phase |
| `compound_type` | String | Yes | Type of compound (Biologic, Small Molecule, etc.) |
| `mechanism_of_action` | String | No | How the drug works |
| `submission_type` | String | No | New Molecular Entity or Product Enhancement |
| `regulatory_designations` | Array | No | Special FDA/EMA designations |
| `filing_date` | String | No | Expected or actual filing date |
| `lead_indication` | Boolean | No | Whether this is the primary indication |
| `status` | String | Yes | Current status (Current, Discontinued, etc.) |
| `source_data` | Object | Yes | Original data from company source |

## Data Harmonization Rules

### 1. Development Phase Normalization
Original phases are mapped to standardized values:

| Original | Harmonized |
|----------|------------|
| "phase 1", "phase_1" | "Phase 1" |
| "phase 2", "phase_2" | "Phase 2" |
| "phase 3", "phase_3" | "Phase 3" |
| "filed", "registration" | "Registration/Filed" |

### 2. Therapeutic Area Normalization
Therapeutic areas are consolidated into major categories:

| Original | Harmonized |
|----------|------------|
| "Inflammation & Immunology" | "Immunology" |
| "Internal Medicine", "Cardiovascular Disease" | "Cardiovascular/Metabolic" |
| "Oncology: Solid Tumors", "Oncology: Hematology" | "Oncology" |
| "Emerging Therapy Areas", "In-market Brands and Global Health" | "Other/Emerging" |
| "Rare Blood Disorders", "Rare Endocrine Disorders" | "Rare Diseases" |

### 3. Compound Type Classification
Compounds are classified based on available information:

| Type | Criteria |
|------|----------|
| "Biologic" | Proteins, antibodies, peptides |
| "Small Molecule" | Chemical compounds, oral drugs |
| "Vaccine" | Immunization products |
| "Cell Therapy" | Cell-based treatments |
| "RNA Therapy" | siRNA, mRNA therapeutics |
| "Radioligand" | Radioactive targeting compounds |

### 4. Candidate ID Generation
Unique identifiers follow the pattern: `{COMPANY_CODE}_{SEQUENTIAL_NUMBER}`
- Novo Nordisk: NVO_001, NVO_002, ...
- Pfizer: PFE_001, PFE_002, ...
- Novartis: NVS_001, NVS_002, ...

## Summary Statistics

### Distribution by Company
- **Novo Nordisk**: 47 candidates (61.0%)
- **Pfizer**: 10 candidates (13.0%) *[Sample data only]*
- **Novartis**: 20 candidates (26.0%)

### Distribution by Development Phase
- **Phase 1**: 34 candidates (44.2%)
- **Phase 2**: 19 candidates (24.7%)
- **Phase 3**: 18 candidates (23.4%)
- **Registration/Filed**: 6 candidates (7.8%)

### Distribution by Therapeutic Area
- **Oncology**: 19 candidates (24.7%)
- **Obesity**: 13 candidates (16.9%)
- **Diabetes**: 12 candidates (15.6%)
- **Cardiovascular/Metabolic**: 10 candidates (13.0%)
- **Immunology**: 7 candidates (9.1%)
- **Other/Emerging**: 7 candidates (9.1%)
- **Rare Diseases**: 7 candidates (9.1%)
- **Vaccines**: 1 candidate (1.3%)
- **Neuroscience**: 1 candidate (1.3%)

## Data Quality Notes

### Completeness
- **High**: candidate_id, company, compound_name, indication, therapeutic_area, development_phase, status
- **Medium**: compound_type, mechanism_of_action
- **Low**: compound_code, brand_name, filing_date, regulatory_designations

### Limitations
1. **Pfizer Data**: Only sample candidates included (10 out of 108 total)
2. **Varying Detail**: Companies provide different levels of detail
3. **Update Frequency**: Data reflects point-in-time extraction (2025-07-03)
4. **Proprietary Information**: Some details may be withheld by companies

## Usage Examples

### Query All Phase 3 Oncology Candidates
```python
phase3_oncology = [
    candidate for candidate in data["unified_pipeline"]
    if candidate["development_phase"] == "Phase 3" 
    and candidate["therapeutic_area"] == "Oncology"
]
```

### Count Candidates by Company and Phase
```python
from collections import defaultdict
counts = defaultdict(lambda: defaultdict(int))
for candidate in data["unified_pipeline"]:
    counts[candidate["company"]][candidate["development_phase"]] += 1
```

### Find Biologics in Diabetes
```python
diabetes_biologics = [
    candidate for candidate in data["unified_pipeline"]
    if candidate["therapeutic_area"] == "Diabetes"
    and candidate["compound_type"] == "Biologic"
]
```

## Validation Rules

### Required Fields Validation
- All candidates must have: candidate_id, company, compound_name, indication, therapeutic_area, development_phase, status
- candidate_id must be unique across all records
- company must be one of: "Novo Nordisk", "Pfizer", "Novartis"
- development_phase must be one of: "Phase 1", "Phase 2", "Phase 3", "Registration/Filed"

### Data Type Validation
- String fields cannot be empty strings
- Boolean fields must be true/false
- Array fields must be valid arrays (can be empty)
- Date fields should follow ISO format when present

## Future Enhancements

### Potential Additions
1. **Clinical Trial IDs**: Link to ClinicalTrials.gov identifiers
2. **Market Size**: Add addressable market information
3. **Competition**: Cross-reference competing compounds
4. **Timeline**: Add projected milestone dates
5. **Risk Assessment**: Include development risk scores

### Schema Evolution
- Version 1.1: Add clinical trial integration
- Version 1.2: Include competitive landscape data
- Version 2.0: Add real-time update capabilities

## Maintenance

### Update Process
1. Extract new data from company sources
2. Run harmonization script: `python3 harmonize_pipeline_data.py`
3. Validate output using data quality checks
4. Update documentation if schema changes
5. Archive previous version

### Quality Assurance
- Automated validation of required fields
- Cross-reference with previous versions for consistency
- Manual review of new therapeutic areas or compound types
- Verification of candidate counts against company totals

---

**Last Updated**: July 3, 2025  
**Data Model Version**: 1.0  
**Next Review**: October 2025
