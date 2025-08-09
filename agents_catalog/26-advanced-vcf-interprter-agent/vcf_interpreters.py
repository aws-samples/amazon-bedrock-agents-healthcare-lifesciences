import boto3
import json
import time
import re
from collections import defaultdict
from typing import Dict, Any
from strands import Agent, tool
from strands.models import BedrockModel

# Import main analysis functions from separate module
from vcf_genomic_functions import (
    execute_genomic_analysis,
    list_available_patients_internal,
    REGION,
    ACCOUNT_ID
)

# Get AWS account information
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
region = boto3.Session().region_name

# Initialize AWS clients (these are also initialized in the imported functions)
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
dynamodb = boto3.client('dynamodb')
athena_client = boto3.client('athena')
glue_client = boto3.client('glue')
ram_client = boto3.client('ram')

vcf_agent_name = 'VCF-genomic-analyst-strands'
vcf_agent_description = "VCF genomic variant analysis engine using Strands framework"
vcf_agent_instruction = """
You are a genomic research assistant AI specialized in analyzing VCF (Variant Call Format) data and genomic variants from AWS HealthOmics. 
Your primary task is to interpret user queries about genomic variants, execute appropriate analyses, and provide relevant genomic insights based on the data.
Use only the appropriate tools as required by the specific question. Follow these instructions carefully:

IMPORTANT: Never apologize or say "I apologize for the error" unless there's an actual error.
If a query returns no results, simply state the facts: "No variants found matching your criteria."

When calling functions:
- If successful: Present results directly
- If no data found: State "No data found for [specific criteria]"  
- If actual error: State "Error occurred: [specific error message]"

Do not add conversational fluff or apologetic language.

1. Before analyzing variants for specific patients:
   a. Use the list_available_patients tool to check which patients have processed VCF data available.
   b. Verify that the requested patient IDs exist in the system before proceeding with analysis.

2. When performing variant analysis:
   a. Use analyze_patient_variants for structured queries with specific analysis types:
      - variant_count: Count total variants for patients
      - pathogenic_variants: Find clinically significant pathogenic variants
      - benign_variants: Find benign variants with ClinVar annotations
      - pharmacogenomic_variants: Find variants affecting drug metabolism
      - gene_analysis: Analyze variants in specific genes
      - clinical_significance: Analyze distribution of clinical significance
      - chromosome_analysis: Analyze variants by chromosome
      - frequency_analysis: Analyze variant allele frequencies
      - common_variants: Find variants shared across multiple patients
      - compare_patients: Compare variant profiles between patients
   b. Use query_genomic_data for natural language queries that need interpretation.
   c. Use list_available_patients for total number of samples and other ID related information

3. When providing genomic insights:
   a. Always explain the clinical significance of pathogenic variants found.
   b. For pharmacogenomic variants, mention potential drug interactions or metabolism effects.
   c. Provide context about variant frequencies and population genetics when relevant.
   d. Explain the difference between high-impact and moderate-impact variants.

4. When responding to user queries:
   a. Start with a brief summary of your understanding of the genomic query.
   b. Explain the analysis approach you're taking.
   c. Present the results with appropriate genomic context and clinical interpretation.
   d. Suggest follow-up analyses if relevant (e.g., gene-specific analysis after finding pathogenic variants).

5. Important genomic considerations:
   a. Always mention data sources (ClinVar annotations, variant stores) when applicable.
   b. Explain limitations of the analysis (e.g., annotation coverage, variant calling quality).
   c. Provide appropriate disclaimers for clinical interpretation of variants.
   d. Suggest consulting with genetic counselors for clinical decision-making when appropriate.
"""

def parse_user_query(query):
    """
    Enhanced parser for genomic analysis queries (needed by tools)
    """
    query_lower = query.lower()
    
    # Extract patient/sample ID patterns
    patient_patterns = [
        r'patient\s+(\w+)',
        r'sample\s+(\w+)', 
        r'id\s+(\w+)',
        r'(\bNA\d+\b)',  # Common pattern like NA21135
        r'(\bHG\d+\b)',  # Another common pattern
        r'(\b\d{7}\b)',  # 7-digit patient IDs
    ]
    
    patient_ids = []
    for pattern in patient_patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        patient_ids.extend(matches)
    
    # Remove duplicates
    patient_ids = list(set(patient_ids))
    
    # Enhanced query type detection for genomic analysis
    query_type = 'unknown'
    if 'variant' in query_lower and 'count' in query_lower:
        query_type = 'variant_count'
    elif 'common variant' in query_lower or 'shared variant' in query_lower:
        query_type = 'common_variants'
    elif 'pathogenic' in query_lower or 'disease' in query_lower:
        query_type = 'pathogenic_variants'
    elif 'benign' in query_lower:
        query_type = 'benign_variants'
    elif 'pharmacogenomic' in query_lower or 'drug' in query_lower or 'medication' in query_lower:
        query_type = 'pharmacogenomic_variants'
    elif 'gene symbol' in query_lower or 'gene name' in query_lower:
        query_type = 'gene_analysis'
    elif 'protein' in query_lower and ('deletion' in query_lower or 'truncation' in query_lower):
        query_type = 'protein_affecting_variants'
    elif 'clinical significance' in query_lower or 'clnsig' in query_lower:
        query_type = 'clinical_significance'
    elif 'annotation' in query_lower:
        query_type = 'annotated_variants'
    elif 'compare' in query_lower:
        query_type = 'compare_patients'
    elif 'list' in query_lower and 'patient' in query_lower:
        query_type = 'list_patients'
    elif 'chromosome' in query_lower or 'chr' in query_lower:
        query_type = 'chromosome_analysis'
    elif 'frequency' in query_lower or 'allele frequency' in query_lower:
        query_type = 'frequency_analysis'
    
    # Extract additional parameters
    gene_pattern = r'gene\s+(\w+)'
    genes = re.findall(gene_pattern, query, re.IGNORECASE)
    
    chromosome_pattern = r'chr(?:omosome)?\s*(\d+|[XY])'
    chromosomes = re.findall(chromosome_pattern, query, re.IGNORECASE)
    
    return {
        'patient_ids': patient_ids,
        'query_type': query_type,
        'genes': genes,
        'chromosomes': chromosomes,
        'original_query': query
    }

print("✅ Query parsing function defined")

# === STRANDS AGENT TOOLS ===

@tool
def analyze_patient_variants(patient_ids: str, analysis_type: str = "variant_count", genes: str = "", chromosomes: str = "") -> str:
    """Analyze genomic variants for specific patients with various analysis types.
    
    Args:
        patient_ids: Comma-separated list of patient IDs to analyze
        analysis_type: Type of analysis (variant_count, pathogenic_variants, pharmacogenomic_variants, clinical_significance, etc.)
        genes: Comma-separated list of genes to focus on (optional)
        chromosomes: Comma-separated list of chromosomes to analyze (optional)
    
    Returns:
        JSON string with analysis results
    """
    try:
        # Convert string inputs to lists if needed
        patient_list = patient_ids.split(',') if isinstance(patient_ids, str) else [patient_ids]
        patient_list = [p.strip() for p in patient_list]  # Remove whitespace
        
        gene_list = genes.split(',') if genes else []
        gene_list = [g.strip() for g in gene_list if g.strip()]  # Remove empty strings
        
        chromosome_list = chromosomes.split(',') if chromosomes else []
        chromosome_list = [c.strip() for c in chromosome_list if c.strip()]  # Remove empty strings
        
        analysis_request = {
            'patient_ids': patient_list,
            'query_type': analysis_type,
            'genes': gene_list,
            'chromosomes': chromosome_list,
            'original_query': f"Analyze {analysis_type} for patients {patient_list}"
        }
        
        # Call the main analysis function from the imported module
        result = execute_genomic_analysis(analysis_request)
        return json.dumps(result, indent=2)
            
    except Exception as e:
        return f"Error analyzing patient variants: {str(e)}"

@tool
def query_genomic_data(query: str) -> str:
    """Send a natural language query to analyze genomic data and variants.
    
    Args:
        query: Natural language query about genomic variants
    
    Returns:
        JSON string with analysis results
    """
    try:
        # Parse the query using the local function
        analysis_request = parse_user_query(query)
        
        if not analysis_request or analysis_request['query_type'] == 'unknown':
            return 'Could not understand the query. Please provide more specific information about patients, variants, or genes.'
        
        # Call the main analysis function from the imported module
        result = execute_genomic_analysis(analysis_request)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error querying genomic data: {str(e)}"

@tool
def list_available_patients() -> str:
    """Get a list of all patients with processed VCF data available for analysis.
    
    Returns:
        JSON string with list of available patients
    """
    try:
        # Call the main function from the imported module
        result = list_available_patients_internal()
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error listing available patients: {str(e)}"

# Create list of tools
vcf_agent_tools = [analyze_patient_variants, query_genomic_data, list_available_patients]

model = BedrockModel(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        region_name=region,
        temperature=0.1,
        streaming=False
    )