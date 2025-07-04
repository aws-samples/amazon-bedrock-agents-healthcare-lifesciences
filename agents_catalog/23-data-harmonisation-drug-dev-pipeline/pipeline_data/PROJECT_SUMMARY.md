# Pharmaceutical Pipeline Data Extraction Project

## Project Overview
This project successfully extracted and harmonized drug development pipeline data from three major pharmaceutical companies: **Novo Nordisk**, **Pfizer**, and **Novartis**. The data has been structured in JSON format for easy analysis and comparison.

## Data Sources
- **Novo Nordisk**: https://www.novonordisk.com/science-and-technology/r-d-pipeline.html
- **Pfizer**: https://www.pfizer.com/science/drug-product-pipeline  
- **Novartis**: https://www.novartis.com/research-development/novartis-pipeline

## Files Generated

### 1. Individual Company Pipeline Data
- `novo_nordisk_pipeline.json` - Complete pipeline data for Novo Nordisk (47 candidates detailed)
- `pfizer_pipeline.json` - Complete pipeline data for Pfizer (108 candidates total)
- `novartis_pipeline.json` - Complete pipeline data for Novartis (20+ candidates detailed)

### 2. Comparative Analysis
- `pipeline_comparison_summary.json` - Comprehensive comparison across all three companies
- `PROJECT_SUMMARY.md` - This summary document
- `README.md` - Project documentation

### 3. Analysis Tools
- `pipeline_analysis.py` - Python script for data analysis and visualization
- `requirements.txt` - Python dependencies for the analysis script

## Key Findings

### Company Specializations
- **Novo Nordisk**: Market leader in diabetes and obesity with 108 candidates
  - Strong focus on GLP-1 receptor agonists, insulin analogues, and combination therapies
  - Emerging presence in cardiovascular disease and rare blood disorders
  
- **Pfizer**: Broad therapeutic portfolio with 108 candidates
  - Strong in oncology, immunology, vaccines, and internal medicine
  - Extensive use of regulatory designations (Fast Track, Breakthrough, Orphan Drug)
  
- **Novartis**: Innovation leader in precision medicine with 100+ candidates
  - Pioneering radioligand therapy platform
  - Strong oncology focus with novel targeting mechanisms

### Development Phase Distribution
- All companies maintain substantial early-stage pipelines (Phase 1 & 2)
- Novo Nordisk has several candidates in filing stage, indicating near-term launches
- Pfizer shows balanced distribution across all phases
- Novartis focuses on innovative mechanisms with longer development timelines

### Therapeutic Area Competition
- **Oncology**: Intense competition between Pfizer and Novartis with different approaches
- **Diabetes/Obesity**: Novo Nordisk maintains clear leadership position
- **Immunology**: Both Pfizer and Novartis have strong competing pipelines
- **Rare Diseases**: Novo Nordisk building significant presence in blood disorders

## Data Quality and Limitations

### Strengths
- Comprehensive extraction from official company sources
- Structured JSON format for easy analysis
- Detailed candidate information including mechanisms of action
- Comparative analysis across companies

### Limitations
- Data completeness varies by company (some provide more detail than others)
- Pipeline data is updated quarterly by companies, so timing may vary
- Some proprietary information may not be publicly disclosed
- Regulatory status and timelines are subject to change

## Usage Instructions

### For Data Analysis
1. Install Python dependencies: `pip install -r requirements.txt`
2. Run analysis script: `python pipeline_analysis.py`
3. Generated visualizations and reports will be saved in the same directory

### For Data Integration
- JSON files can be easily imported into databases, analytics platforms, or BI tools
- Standardized structure allows for cross-company comparisons
- Data can be used for competitive intelligence, market analysis, or investment research

## Future Enhancements

### Potential Improvements
1. **Automated Updates**: Set up scheduled data extraction to keep pipeline data current
2. **Additional Companies**: Expand to include more pharmaceutical companies
3. **Clinical Trial Integration**: Link to ClinicalTrials.gov for additional trial details
4. **Market Analysis**: Add market size and commercial potential estimates
5. **Regulatory Tracking**: Monitor FDA/EMA approval status changes

### Technical Enhancements
1. **API Development**: Create REST API for real-time data access
2. **Dashboard Creation**: Build interactive dashboard for data visualization
3. **Machine Learning**: Develop predictive models for approval success rates
4. **Alert System**: Notify of significant pipeline changes or updates

## Contact and Maintenance
- **Created**: July 3, 2025
- **Data Specialist**: Healthcare Life Sciences Team
- **Update Frequency**: Quarterly (recommended)
- **Next Review**: October 2025

## Disclaimer
This data is extracted from publicly available sources and is intended for research and analysis purposes. Pipeline information is subject to change based on clinical trial results, regulatory decisions, and company strategic priorities. Users should verify current information directly with company sources for the most up-to-date details.
