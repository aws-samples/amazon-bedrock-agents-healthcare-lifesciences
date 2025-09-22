import boto3
import json
import time
import re
from collections import defaultdict
from typing import Dict, Any
from strands import Agent, tool
from strands.models import BedrockModel

# Import main analysis functions from separate module
from genomics_store_functions import (
    execute_dynamic_query,
    format_dynamic_query_results,
    query_variants_by_gene_function,
    query_variants_by_chromosome_function,
    analyze_allele_frequencies_function,
    compare_sample_variants_function,
    get_stores_information,
    get_available_samples_from_variant_store,
    REGION,
    ACCOUNT_ID,
    VARIANT_STORE_NAME,
    ANNOTATION_STORE_NAME,
    LAKE_FORMATION_DATABASE
)

# Get AWS account information
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
region = boto3.Session().region_name

# Initialize AWS clients for genomics stores
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
athena_client = boto3.client('athena')
omics_client = boto3.client('omics')
glue_client = boto3.client('glue')

genomics_store_agent_name = 'Genomics-Store-Analyst-Strands'
genomics_store_agent_description = "Genomics store analysis engine using genomicsvariantstore, genomicsannotationstore with dynamic query capabilities"
genomics_store_agent_instruction = """
You are an advanced genomics analysis assistant specialized in clinical variant interpretation using AWS HealthOmics genomicsvariantstore and genomicsannotationstore.

Your primary focus is on clinically actionable genomic analysis with these specialized capabilities:

CORE CLINICAL TOOLS:
1. **Gene-Specific Analysis** (query_variants_by_gene): For targeted gene panels, cancer genes (BRCA1/2, TP53), pharmacogenes (CYP2D6, CYP2C19)
2. **Chromosomal Analysis** (query_variants_by_chromosome): For chromosomal abnormalities, CNV analysis, specific genomic regions
3. **Population Frequency Analysis** (analyze_allele_frequencies): For rare disease variants, population genetics, allele frequency comparisons with 1000 Genomes
4. **Sample Comparison** (compare_sample_variants): For family studies, cohort analysis, population stratification
5. **Dynamic Queries** (execute_dynamic_genomics_query): For complex clinical questions requiring custom SQL

CLINICAL DECISION SUPPORT:
- Always apply quality filtering (qual > 30 AND PASS filters)
- Prioritize variants by clinical significance and functional impact
- Include 1000 Genomes frequency data for population context
- Provide actionable clinical interpretations

TOOL SELECTION STRATEGY:
1. **For specific genes**: Use query_variants_by_gene (e.g., "BRCA1 variants", "CYP2D6 pharmacogenomics")
2. **For chromosomal regions**: Use query_variants_by_chromosome (e.g., "chromosome 17 variants", "chr13:32000000-33000000")
3. **For frequency analysis**: Use analyze_allele_frequencies (e.g., "rare variants", "population frequencies")
4. **For cohort studies**: Use compare_sample_variants (e.g., "compare samples", "family analysis")
5. **For complex queries**: Use execute_dynamic_genomics_query

CLINICAL INTERPRETATION GUIDELINES:
- Pathogenic/Likely Pathogenic: Immediate clinical attention
- VUS (Variants of Uncertain Significance): Monitor and reassess
- High Impact + Rare: Potential novel findings
- Pharmacogenomic variants: Medication dosing implications
- Population frequency context: Distinguish rare from common variants

RESPONSE FORMAT:
- Lead with clinical significance
- Include gene context and functional impact
- Provide population frequency when available
- Suggest follow-up actions when appropriate
- Use clear, clinically relevant language

QUALITY STANDARDS:
- All analyses use comprehensive quality filtering
- Results include confidence metrics (quality scores, depth)
- Population context from 1000 Genomes Project
- Clinical annotations from ClinVar and VEP

Remember: Focus on clinically actionable insights that can inform patient care, genetic counseling, and treatment decisions.
"""

@tool
def query_variants_by_gene(gene_symbols: str, sample_ids: str = "", include_frequency: bool = True) -> str:
    """
    Query variants in specific genes with comprehensive clinical annotations.
    
    Args:
        gene_symbols: Comma-separated list of gene symbols (e.g., "BRCA1,BRCA2,TP53")
        sample_ids: Optional comma-separated list of sample IDs to filter
        include_frequency: Whether to include 1000 Genomes frequency data
    
    Returns:
        JSON string with gene-specific variant analysis
    """
    try:
        genes = [g.strip().upper() for g in gene_symbols.split(',') if g.strip()]
        samples = [s.strip() for s in sample_ids.split(',') if s.strip()] if sample_ids else None
        
        result = query_variants_by_gene_function(genes, samples, include_frequency)
        
        if isinstance(result, dict) and 'error' not in result:
            result['genomics_context'] = {
                'variant_store': VARIANT_STORE_NAME,
                'annotation_store': ANNOTATION_STORE_NAME,
                'database': LAKE_FORMATION_DATABASE,
                'analysis_type': 'gene_analysis',
                'tool_used': '🧬 Gene Variant Analysis Tool'
            }
        
        return f"{json.dumps(result, indent=2, default=str)}"
            
    except Exception as e:
        return f"Error in gene variant analysis: {str(e)}"

@tool
def query_variants_by_chromosome(chromosome: str, sample_ids: str = "", position_range: str = "") -> str:
    """
    Query variants by chromosome with optional position range filtering.
    
    Args:
        chromosome: Chromosome identifier (e.g., "1", "X", "Y", "MT")
        sample_ids: Optional comma-separated list of sample IDs
        position_range: Optional position range in format "start-end" (e.g., "1000000-2000000")
    
    Returns:
        JSON string with chromosome-specific variant analysis
    """
    try:
        samples = [s.strip() for s in sample_ids.split(',') if s.strip()] if sample_ids else None
        pos_range = position_range if position_range else None
        
        result = query_variants_by_chromosome_function(chromosome, samples, pos_range)
        
        if isinstance(result, dict) and 'error' not in result:
            result['genomics_context'] = {
                'variant_store': VARIANT_STORE_NAME,
                'annotation_store': ANNOTATION_STORE_NAME,
                'database': LAKE_FORMATION_DATABASE,
                'analysis_type': 'chromosome_analysis'
            }
        
        return f"{json.dumps(result, indent=2, default=str)}"
        
    except Exception as e:
        return f"Error in chromosome variant analysis: {str(e)}"

@tool
def analyze_allele_frequencies(sample_ids: str = "", frequency_threshold: float = 0.01) -> str:
    """
    Analyze allele frequencies and compare with 1000 Genomes Project data.
    
    Args:
        sample_ids: Optional comma-separated list of sample IDs
        frequency_threshold: Frequency threshold for rare variant analysis (default: 0.01 = 1%)
    
    Returns:
        JSON string with population frequency analysis
    """
    try:
        samples = [s.strip() for s in sample_ids.split(',') if s.strip()] if sample_ids else None
        
        result = analyze_allele_frequencies_function(samples, frequency_threshold)
        
        if isinstance(result, dict) and 'error' not in result:
            result['genomics_context'] = {
                'variant_store': VARIANT_STORE_NAME,
                'annotation_store': ANNOTATION_STORE_NAME,
                'database': LAKE_FORMATION_DATABASE,
                'analysis_type': 'frequency_analysis'
            }
        
        return f"{json.dumps(result, indent=2, default=str)}"
        
    except Exception as e:
        return f"Error in allele frequency analysis: {str(e)}"

@tool
def compare_sample_variants(sample_ids: str) -> str:
    """
    Compare variant profiles between multiple samples for population analysis.
    
    Args:
        sample_ids: Comma-separated list of sample IDs to compare (minimum 2 required)
    
    Returns:
        JSON string with sample comparison analysis
    """
    try:
        samples = [s.strip() for s in sample_ids.split(',') if s.strip()]
        
        result = compare_sample_variants_function(samples)
        
        if isinstance(result, dict) and 'error' not in result:
            result['genomics_context'] = {
                'variant_store': VARIANT_STORE_NAME,
                'annotation_store': ANNOTATION_STORE_NAME,
                'database': LAKE_FORMATION_DATABASE,
                'analysis_type': 'sample_comparison'
            }
        
        return f"{json.dumps(result, indent=2, default=str)}"
        
    except Exception as e:
        return f"Error in sample comparison: {str(e)}"

@tool
def execute_dynamic_genomics_query(user_question: str, sample_ids: str = "") -> str:
    """Execute a dynamic SQL query based on natural language question using AI-generated SQL.
    
    Args:
        user_question: Natural language question about genomic data
        sample_ids: Comma-separated list of sample IDs to filter (optional)
    
    Returns:
        Formatted string with query results and generated SQL
    """
    try:
        sample_list = None
        if sample_ids:
            sample_list = sample_ids.split(',')
            sample_list = [s.strip() for s in sample_list if s.strip()]
        
        # Call the dynamic query function
        result = execute_dynamic_query(user_question, sample_list)
        
        # Format the results for better readability
        formatted_result = format_dynamic_query_results(result)
        
        return f"{formatted_result}"
        
    except Exception as e:
        return f"Error executing dynamic genomics query: {str(e)}"

# Create list of tools for genomics stores
genomics_store_agent_tools = [
    query_variants_by_gene,
    query_variants_by_chromosome, 
    analyze_allele_frequencies,
    compare_sample_variants,
    execute_dynamic_genomics_query
]

model = BedrockModel(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        region_name=region,
        temperature=0.1,
        streaming=False
    )

def test_orchestrator_agent_with_query(query):
    """
    Test function to demonstrate proper query output format
    """
    print(f"Testing orchestrator agent with query: {query}")
    
    # Create the genomics store agent
    genomics_store_agent = Agent(
        name=genomics_store_agent_name,
        description=genomics_store_agent_description,
        instructions=genomics_store_agent_instruction,
        model=model,
        tools=genomics_store_agent_tools
    )
    
    # Execute the query
    try:
        response = genomics_store_agent.chat(query)
        return response
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

print("✅ Genomics store agent tools defined")
print(f"✅ Configured for:")
print(f"   - Variant Store: {VARIANT_STORE_NAME}")
print(f"   - Annotation Store: {ANNOTATION_STORE_NAME}")
print(f"   - Database: {LAKE_FORMATION_DATABASE}")
print(f"   - Region: {REGION}")
print(f"   - Tools: {len(genomics_store_agent_tools)}")

# Test with a sample query
if __name__ == "__main__":
    test_query = "How many patients are there in present cohort?"
    result = test_orchestrator_agent_with_query(test_query)
