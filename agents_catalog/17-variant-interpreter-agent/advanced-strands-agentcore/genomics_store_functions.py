"""
Genomics Store Analysis Functions Module
Targeting: genomicsvariantstore, genomicsannotationstore, default database
Using HealthOmics stores directly instead of DynamoDB tracking
"""

import os
import boto3
from botocore.client import Config
import json
from datetime import datetime
import time
import re
import pandas as pd
from botocore.exceptions import ClientError, NoCredentialsError, NoRegionError

# Initialize AWS configuration with comprehensive error handling
def get_aws_config():
    """Get AWS configuration with multiple fallback options"""
    region = None
    account_id = None
    
    # Method 1: Environment variables
    region = os.environ.get('AWS_DEFAULT_REGION') or os.environ.get('AWS_REGION') or os.environ.get('REGION')
    
    # Method 2: boto3 session
    if not region:
        try:
            session = boto3.Session()
            region = session.region_name
        except Exception:
            pass
    
    # Method 3: Default region
    if not region:
        region = '<YOUR_REGION>'
        print(f"No region configured, using default: {region}")
    
    # Try to get account ID
    try:
        sts_client = boto3.client('sts', region_name=region)
        account_id = sts_client.get_caller_identity()['Account']
        print(f"✅ AWS configuration detected - Region: {region}, Account: {account_id}")
    except Exception as e:
        print(f"⚠️ Warning: Could not get AWS account info: {e}")
        account_id = os.environ.get('ACCOUNT_ID', '<YOUR_ACCOUNT_ID>')
        print(f"Using default account ID: {account_id}")
    
    return region, account_id

# Get AWS configuration
REGION, ACCOUNT_ID = get_aws_config()

# Environment variables for genomics stores
MODEL_ID = os.environ.get('MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
LAKE_FORMATION_DATABASE = os.environ.get('LAKE_FORMATION_DATABASE', '<YOUR_AWS_PROFILE>')
VARIANT_STORE_NAME = os.environ.get('VARIANT_STORE_NAME', 'genomicsvariantstore')
ANNOTATION_STORE_NAME = os.environ.get('ANNOTATION_STORE_NAME', 'genomicsannotationstore')

# Genomic analysis constants
PATHOGENIC_SIGNIFICANCE = ['Pathogenic', 'Likely_pathogenic', 'Pathogenic/Likely_pathogenic']
BENIGN_SIGNIFICANCE = ['Benign', 'Likely_benign', 'Benign/Likely_benign']
HIGH_IMPACT_CONSEQUENCES = ['stop_gained', 'stop_lost', 'start_lost', 'frameshift_variant', 'splice_donor_variant', 'splice_acceptor_variant']
MODERATE_IMPACT_CONSEQUENCES = ['missense_variant', 'inframe_deletion', 'inframe_insertion']

# Bedrock configuration
BEDROCK_CONFIG = Config(connect_timeout=300, read_timeout=300, retries={'max_attempts': 0})

# Initialize clients
def initialize_aws_clients():
    """Initialize AWS clients with error handling"""
    clients = {}
    
    try:
        clients['athena'] = boto3.client('athena', region_name=REGION)
        print("✅ Athena client initialized")
    except Exception as e:
        print(f"⚠️ Athena client failed: {e}")
        clients['athena'] = None
    
    try:
        clients['bedrock'] = boto3.client(service_name='bedrock-runtime', region_name=REGION, config=BEDROCK_CONFIG)
        print("✅ Bedrock client initialized")
    except Exception as e:
        print(f"⚠️ Bedrock client failed: {e}")
        clients['bedrock'] = None
    
    try:
        clients['omics'] = boto3.client('omics', region_name=REGION)
        print("✅ HealthOmics client initialized")
    except Exception as e:
        print(f"⚠️ HealthOmics client failed: {e}")
        clients['omics'] = None
    
    try:
        clients['glue'] = boto3.client('glue', region_name=REGION)
        print("✅ Glue client initialized")
    except Exception as e:
        print(f"⚠️ Glue client failed: {e}")
        clients['glue'] = None
    
    return clients

# Initialize all clients
aws_clients = initialize_aws_clients()
athena_client = aws_clients['athena']
bedrock_client = aws_clients['bedrock']
omics_client = aws_clients['omics']
glue_client = aws_clients['glue']

print(f"Region: {REGION}")
print(f"Account ID: {ACCOUNT_ID}")
print(f"Variant Store: {VARIANT_STORE_NAME}")
print(f"Annotation Store: {ANNOTATION_STORE_NAME}")
print(f"Database: {LAKE_FORMATION_DATABASE}")

# === CORE GENOMIC ANALYSIS FUNCTIONS ===
def get_variant_store_info():
    """
    Get information about the genomicsvariantstore using HealthOmics API
    """
    if omics_client is None:
        return {'error': 'HealthOmics client not available'}
        
    try:
        # Get variant store details
        var_store = omics_client.get_variant_store(name=VARIANT_STORE_NAME)
        
        store_info = {
            'name': var_store['name'],
            'id': var_store['id'],
            'status': var_store['status'],
            'creation_time': var_store.get('creationTime', ''),
            'description': var_store.get('description', ''),
            'reference': var_store.get('reference', {}),
            'sse_config': var_store.get('sseConfig', {}),
            'status_message': var_store.get('statusMessage', ''),
            'store_size_bytes': var_store.get('storeSizeBytes', 0),
            'tags': var_store.get('tags', {})
        }
        
        return {
            'variant_store': store_info,
            'store_type': 'HealthOmics Variant Store'
        }
        
    except Exception as e:
        return {'error': f'Error getting variant store info: {str(e)}'}

def get_annotation_store_info():
    """
    Get information about the genomicsannotationstore using HealthOmics API
    """
    if omics_client is None:
        return {'error': 'HealthOmics client not available'}
        
    try:
        # Get annotation store details
        ann_store = omics_client.get_annotation_store(name=ANNOTATION_STORE_NAME)
        
        store_info = {
            'name': ann_store['name'],
            'id': ann_store['id'],
            'status': ann_store['status'],
            'creation_time': ann_store.get('creationTime', ''),
            'description': ann_store.get('description', ''),
            'store_format': ann_store.get('storeFormat', ''),
            'store_options': ann_store.get('storeOptions', {}),
            'sse_config': ann_store.get('sseConfig', {}),
            'status_message': ann_store.get('statusMessage', ''),
            'store_size_bytes': ann_store.get('storeSizeBytes', 0),
            'tags': ann_store.get('tags', {})
        }
        
        return {
            'annotation_store': store_info,
            'store_type': 'HealthOmics Annotation Store'
        }
        
    except Exception as e:
        return {'error': f'Error getting annotation store info: {str(e)}'}

def execute_athena_query_on_stores(query, database=None):
    """
    Execute Athena query on genomics stores using default database
    """
    if athena_client is None:
        raise Exception("Athena client not available. Please configure AWS credentials and region.")
        
    try:
        if not database:
            database = LAKE_FORMATION_DATABASE
        
        print(f"Executing query on database '{database}': {query}")
        
        # Print the query execution details in the expected format
        print("=" * 84)
        print(f"Executing query on database '{database}': ")
        print(f"        {query}")
        
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': database},
            WorkGroup='primary',
            ResultConfiguration={
                'OutputLocation': f's3://aws-athena-query-results-{ACCOUNT_ID}-{REGION}/'
            }
        )
        
        query_id = response['QueryExecutionId']
        
        # Wait for completion
        max_attempts = 30
        for attempt in range(max_attempts):
            result = athena_client.get_query_execution(QueryExecutionId=query_id)
            status = result['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                break
            elif status in ['FAILED', 'CANCELLED']:
                error_reason = result['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                raise Exception(f"Query failed: {error_reason}")
            
            time.sleep(2)
        
        if status != 'SUCCEEDED':
            raise Exception("Query timed out")
        
        # Get results with pagination
        rows = []
        next_token = None
        columns = None
        
        while True:
            if next_token:
                results = athena_client.get_query_results(
                    QueryExecutionId=query_id,
                    NextToken=next_token,
                    MaxResults=1000
                )
            else:
                results = athena_client.get_query_results(
                    QueryExecutionId=query_id,
                    MaxResults=1000
                )
            
            # Get column names from first response
            if columns is None:
                columns = [col['Name'] for col in results['ResultSet']['ResultSetMetadata']['ColumnInfo']]
            
            # Process rows (skip header only on first page)
            start_idx = 1 if next_token is None else 0
            for row in results['ResultSet']['Rows'][start_idx:]:
                row_data = [col.get('VarCharValue', '') for col in row['Data']]
                row_dict = dict(zip(columns, row_data))
                rows.append(row_dict)
            
            # Check if there are more results
            next_token = results.get('NextToken')
            if not next_token:
                break
        
        print(f"Retrieved {len(rows)} total rows from Athena query")
        return rows
        
    except Exception as e:
        print(f"Error executing Athena query: {e}")
def get_table_schema_info():
    """
    Get schema information for variant and annotation stores
    """
    try:
        var_store_info = get_variant_store_info()
        ann_store_info = get_annotation_store_info()
        
        # Get actual store names from HealthOmics
        var_store_name = VARIANT_STORE_NAME
        ann_store_name = ANNOTATION_STORE_NAME
        
        # Try to get schema from Glue catalog if available
        variant_schema = "sampleid, contigname, start, end, referenceallele, alternatealleles, filters, annotations, qual, depth, information"
        annotation_schema = "contigname, start, end, referenceallele, alternatealleles, attributes"
        
        if glue_client:
            try:
                # Get variant store schema
                var_response = glue_client.get_table(
                    DatabaseName=LAKE_FORMATION_DATABASE,
                    Name=var_store_name
                )
                variant_columns = [col['Name'] for col in var_response['Table']['StorageDescriptor']['Columns']]
                variant_schema = ", ".join(variant_columns)
            except Exception as e:
                print(f"Could not get variant store schema from Glue: {e}")
            
            try:
                # Get annotation store schema
                ann_response = glue_client.get_table(
                    DatabaseName=LAKE_FORMATION_DATABASE,
                    Name=ann_store_name
                )
                annotation_columns = [col['Name'] for col in ann_response['Table']['StorageDescriptor']['Columns']]
                annotation_schema = ", ".join(annotation_columns)
            except Exception as e:
                print(f"Could not get annotation store schema from Glue: {e}")
        
        annotation_structure = """
VEP Annotations Structure:
- v.annotations.vep[1].symbol (gene symbol)
- v.annotations.vep[1].impact (HIGH, MODERATE, LOW)
- v.annotations.vep[1].consequence[1] (variant consequence)
- v.annotations.vep[1].biotype (gene biotype)
- v.annotations.vep[1].sift_prediction (SIFT score)
- v.annotations.vep[1].polyphen_prediction (PolyPhen score)

ClinVar Attributes Structure:
- a.attributes['CLNSIG'] (clinical significance)
- a.attributes['CLNDN'] (disease name)
- a.attributes['GENEINFO'] (gene information)
- a.attributes['CLNREVSTAT'] (review status)
- a.attributes['RS'] (dbSNP ID)
- a.attributes['ALLELEID'] (ClinVar allele ID)
"""
        
        return {
            'variant_store_name': var_store_name,
            'annotation_store_name': ann_store_name,
            'variant_store_schema': variant_schema,
            'annotation_store_schema': annotation_schema,
            'annotation_structure': annotation_structure
        }
        
    except Exception as e:
        return {'error': f'Error getting schema info: {str(e)}'}

def construct_dynamic_query(user_question, patient_ids=None):
    """
    Construct a dynamic SQL query based on user question and schema information
    """
    try:
        # Get schema information
        schema_info = get_table_schema_info()
        
        if 'error' in schema_info:
            return schema_info
        
        var_store_name = schema_info['variant_store_name']
        ann_store_name = schema_info['annotation_store_name']
        
        # Create a comprehensive prompt for Claude to construct the query
        schema_context = f"""
GENOMIC DATABASE SCHEMA INFORMATION:

VARIANT STORE TABLE: {var_store_name}
Available columns: {schema_info.get('variant_store_schema', 'Schema not available')}

ANNOTATION STORE TABLE: {ann_store_name} 
Available columns: {schema_info.get('annotation_store_schema', 'Schema not available')}

ANNOTATION ATTRIBUTES STRUCTURE:
{schema_info.get('annotation_structure', 'Structure not available')}

COMMON JOIN PATTERN:
The variant and annotation stores are typically joined on:
- REPLACE(v.contigname, 'chr', '') = a.contigname
- v.start = a.start
- v.referenceallele = a.referenceallele
- v.alternatealleles[1] = a.alternatealleles[1]

VEP ANNOTATIONS ACCESS (MUST use cardinality checks):
- VEP gene symbol: CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].symbol END
- VEP impact: CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].impact END
- VEP consequence: CASE WHEN cardinality(v.annotations.vep) > 0 AND cardinality(v.annotations.vep[1].consequence) > 0 THEN v.annotations.vep[1].consequence[1] END
- VEP biotype: CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].biotype END

CLINVAR ATTRIBUTES ACCESS:
- Clinical significance: a.attributes['CLNSIG']
- Disease name: a.attributes['CLNDN']
- Gene info: a.attributes['GENEINFO']
- Review status: a.attributes['CLNREVSTAT']
- dbSNP ID: a.attributes['RS']
- Allele ID: a.attributes['ALLELEID']

COMMON FILTERS:
- Quality variants: v.filters[1] = 'PASS'
- High quality variants: v.qual > 50 AND contains(v.filters, 'PASS')
- Pass only variants: contains(v.filters, 'PASS') AND v.qual > 30
- Pathogenic variants: a.attributes['CLNSIG'] IN ('Pathogenic', 'Likely_pathogenic')
- High impact: CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].impact END = 'HIGH'

CRITICAL SYNTAX RULES:
1. Table references: Use {var_store_name} and {ann_store_name} exactly as shown
2. Join syntax: REPLACE(v.contigname, 'chr', '') = a.contigname (NOT both sides)
3. VEP arrays: ALWAYS use CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].field END
4. Alternatealleles: Use v.alternatealleles[1] for first alternate allele
5. Quality filtering: Always include v.qual > 30 AND contains(v.filters, 'PASS')

USER QUESTION: {user_question}
"""
        
        if patient_ids:
            schema_context += f"\nPATIENT FILTER: Include only these patient IDs: {patient_ids}"
        
        schema_context += """

Please construct a SQL query to answer the user's question using the schema information provided above. 
The query should:
1. Use proper table aliases (v for variant store, a for annotation store)
2. Include appropriate JOINs if both tables are needed
3. Handle array access safely with cardinality checks for VEP annotations
4. Use proper attribute access for ClinVar data
5. Include patient filtering if specified
6. Be optimized for performance

Return ONLY the SQL query without any explanation or markdown formatting.
"""
        
        return {
            'schema_context': schema_context,
            'var_store_name': var_store_name,
            'ann_store_name': ann_store_name,
            'patient_ids': patient_ids
        }
        
    except Exception as e:
        return {"error": f"Error constructing dynamic query: {str(e)}"}

def execute_dynamic_query(user_question, patient_ids=None):
    """
    Execute a dynamically constructed query based on user question
    """
    try:
        # Get query construction context
        query_context = construct_dynamic_query(user_question, patient_ids)
        
        if 'error' in query_context:
            return query_context
        
        # Use bedrock to generate the SQL query
        if bedrock_client is None:
            return {"error": "Bedrock client not available for dynamic query construction"}
        
        prompt = query_context['schema_context']
        
        # Call Claude to generate the SQL query
        response = bedrock_client.invoke_model(
            modelId="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt + "\n\nIMPORTANT: Use LEFT JOIN or INNER JOIN explicitly instead of just JOIN."
                    }
                ]
            })
        )
        
        response_body = json.loads(response['body'].read())
        generated_query = response_body['content'][0]['text'].strip()
        
        # Clean up the query (remove any markdown formatting)
        if generated_query.startswith('```sql'):
            generated_query = generated_query.replace('```sql', '').replace('```', '').strip()
        elif generated_query.startswith('```'):
            generated_query = generated_query.replace('```', '').strip()
        
        # Execute the generated query
        results = execute_athena_query_on_stores(generated_query)
        
        return {
            'user_question': user_question,
            'generated_query': generated_query,
            'results': results,
            'query_context': 'Dynamic query constructed using schema analysis'
        }
        
    except Exception as e:
        return {"error": f"Error executing dynamic query: {str(e)}"}

def format_dynamic_query_results(query_result):
    """
    Format results from dynamic query execution
    """
    if isinstance(query_result, dict) and 'error' in query_result:
        return f"❌ Error: {query_result['error']}"
    
    if 'results' not in query_result:
        return "❌ No results returned from dynamic query"
    
    results = query_result['results']
    user_question = query_result.get('user_question', 'Unknown question')
    generated_query = query_result.get('generated_query', 'Query not available')
    
    formatted_response = f"🔍 Dynamic Query Analysis for: '{user_question}'\n"
    formatted_response += "=" * 60 + "\n\n"
    
    formatted_response += "📋 Generated SQL Query:\n"
    formatted_response += "-" * 30 + "\n"
    formatted_response += f"{generated_query}\n\n"
    
    formatted_response += "📊 Query Results:\n"
    formatted_response += "-" * 30 + "\n"
    
    if isinstance(results, dict) and 'error' in results:
        formatted_response += f"❌ Query execution error: {results['error']}\n"
    elif isinstance(results, list):
        if len(results) == 0:
            formatted_response += "No results found matching your criteria.\n"
        else:
            formatted_response += f"Found {len(results)} results:\n\n"
            # Show first few rows as sample
            sample_size = min(10, len(results))
            for i, row in enumerate(results[:sample_size], 1):
                formatted_response += f"Row {i}: {row}\n"
            if len(results) > sample_size:
                formatted_response += f"\n... and {len(results) - sample_size} more rows"
    else:
        formatted_response += str(results)
    
    return formatted_response

def get_available_samples_from_variant_store():
    """
    Get available samples directly from the variant store instead of DynamoDB
    """
    try:
        # Query the variant store to get unique sample IDs
        query = f"""
        SELECT DISTINCT sampleid, COUNT(*) as variant_count
        FROM {VARIANT_STORE_NAME}
        GROUP BY sampleid
        ORDER BY sampleid
        """
        
        results = execute_athena_query_on_stores(query)
        
        if not results:
            return {
                'analysis_type': 'Available Samples',
                'results': [],
                'summary': 'No samples found in variant store.'
            }
        
        samples = []
        for row in results:
            samples.append({
                'sample_id': row['sampleid'],
                'variant_count': int(row['variant_count']),
                'source': 'variant_store'
            })
        
        response_text = f"Available samples in variant store ({len(samples)} total):\n"
        for sample in samples:
            response_text += f"- {sample['sample_id']}: {sample['variant_count']:,} variants\n"
        
        return {
            'analysis_type': 'Available Samples',
            'results': samples,
            'summary': response_text,
            'total_count': len(samples)
        }
        
    except Exception as e:
        return {'error': f'Error getting samples from variant store: {str(e)}'}


# === MAIN ANALYSIS FUNCTIONS FOR GENOMICS STORES ===
def get_stores_information():
    """
    Get comprehensive information about variant and annotation stores
    """
    try:
        variant_info = get_variant_store_info()
        annotation_info = get_annotation_store_info()
        
        response_text = f"Genomics Stores Information:\n\n"
        
        # Variant Store Info
        response_text += f"Variant Store ({VARIANT_STORE_NAME}):\n"
        if 'error' in variant_info:
            response_text += f"  Error: {variant_info['error']}\n"
        else:
            store = variant_info.get('variant_store', {})
            response_text += f"  - ID: {store.get('id', 'N/A')}\n"
            response_text += f"  - Status: {store.get('status', 'N/A')}\n"
            response_text += f"  - Created: {store.get('creation_time', 'N/A')}\n"
            response_text += f"  - Description: {store.get('description', 'N/A')}\n"
            response_text += f"  - Size: {store.get('store_size_bytes', 0):,} bytes\n"
        
        # Annotation Store Info
        response_text += f"\nAnnotation Store ({ANNOTATION_STORE_NAME}):\n"
        if 'error' in annotation_info:
            response_text += f"  Error: {annotation_info['error']}\n"
        else:
            store = annotation_info.get('annotation_store', {})
            response_text += f"  - ID: {store.get('id', 'N/A')}\n"
            response_text += f"  - Status: {store.get('status', 'N/A')}\n"
            response_text += f"  - Format: {store.get('store_format', 'N/A')}\n"
            response_text += f"  - Created: {store.get('creation_time', 'N/A')}\n"
            response_text += f"  - Size: {store.get('store_size_bytes', 0):,} bytes\n"
        
        return {
            'analysis_type': 'Stores Information',
            'variant_store_info': variant_info,
            'annotation_store_info': annotation_info,
            'summary': response_text
        }
        
    except Exception as e:
        return {
            'analysis_type': 'Stores Information',
            'error': f"Error getting stores information: {str(e)}",
            'summary': f"Failed to retrieve stores information: {str(e)}"
        }

def query_variants_by_gene_function(gene_symbols, sample_ids=None, include_frequency=True):
    """Query variants in specific genes with comprehensive clinical annotations"""
    try:
        genes = [g.strip().upper() for g in gene_symbols if g.strip()]
        if not genes:
            return {"error": "No valid gene symbols provided"}
        
        gene_list = "', '".join(genes)
        
        sample_filter = ""
        if sample_ids:
            samples = [s.strip() for s in sample_ids if s.strip()]
            if samples:
                sample_list = "', '".join(samples)
                sample_filter = f"AND v.sampleid IN ('{sample_list}')"
        
        frequency_fields = ""
        if include_frequency:
            frequency_fields = "v.information['af'] as allele_frequency_1000g,"
        
        query = f"""
        WITH variant_annotations AS (
            SELECT 
                v.sampleid,
                v.contigname,
                v.start,
                v.referenceallele,
                v.alternatealleles[1] as alternate_allele,
                v.qual,
                v.depth,
                {frequency_fields}
                v.filters[1] as filter_status,
                
                CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].symbol END as vep_gene,
                CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].impact END as vep_impact,
                CASE WHEN cardinality(v.annotations.vep) > 0 AND cardinality(v.annotations.vep[1].consequence) > 0 
                     THEN v.annotations.vep[1].consequence[1] END as vep_consequence,
                
                a.attributes['CLNSIG'] as clinvar_significance,
                a.attributes['CLNDN'] as associated_disease,
                split_part(a.attributes['GENEINFO'], ':', 1) as clinvar_gene
                
            FROM {VARIANT_STORE_NAME} v
            LEFT JOIN {ANNOTATION_STORE_NAME} a ON (
                REPLACE(v.contigname, 'chr', '') = REPLACE(a.contigname, 'chr', '')
                AND v.start = a.start
                AND v.referenceallele = a.referenceallele
                AND v.alternatealleles[1] = a.alternatealleles[1]
            )
            WHERE v.qual > 30 
                AND contains(v.filters, 'PASS')
                AND (
                    (cardinality(v.annotations.vep) > 0 AND UPPER(v.annotations.vep[1].symbol) IN ('{gene_list}'))
                    OR UPPER(split_part(a.attributes['GENEINFO'], ':', 1)) IN ('{gene_list}')
                )
                {sample_filter}
        )
        
        SELECT 
            sampleid,
            CONCAT(contigname, ':', CAST(start as VARCHAR), ':', referenceallele, '>', alternate_allele) as variant_id,
            COALESCE(clinvar_gene, vep_gene) as gene_symbol,
            vep_consequence as consequence,
            vep_impact as impact,
            clinvar_significance,
            associated_disease,
            qual,
            depth,
            {'allele_frequency_1000g,' if include_frequency else ''}
            
            CASE 
                WHEN clinvar_significance = 'Pathogenic' AND vep_impact = 'HIGH' THEN 10
                WHEN clinvar_significance = 'Pathogenic' AND vep_impact = 'MODERATE' THEN 9
                WHEN clinvar_significance = 'Likely_pathogenic' AND vep_impact = 'HIGH' THEN 8
                WHEN clinvar_significance = 'Likely_pathogenic' AND vep_impact = 'MODERATE' THEN 7
                WHEN clinvar_significance = 'Uncertain_significance' AND vep_impact = 'HIGH' THEN 6
                WHEN vep_impact = 'HIGH' THEN 5
                WHEN clinvar_significance = 'Uncertain_significance' AND vep_impact = 'MODERATE' THEN 4
                ELSE 1
            END as priority_score

        FROM variant_annotations
        ORDER BY priority_score DESC, qual DESC
        """
        
        results = execute_athena_query_on_stores(query)
        
        gene_counts = {}
        impact_counts = {}
        significance_counts = {}
        
        for row in results:
            gene = row.get('gene_symbol', 'Unknown')
            impact = row.get('impact', 'Unknown')
            significance = row.get('clinvar_significance', 'Unknown')
            
            gene_counts[gene] = gene_counts.get(gene, 0) + 1
            if impact != 'Unknown':
                impact_counts[impact] = impact_counts.get(impact, 0) + 1
            if significance != 'Unknown':
                significance_counts[significance] = significance_counts.get(significance, 0) + 1
        
        return {
            "analysis_type": "Gene-Specific Variant Analysis",
            "genes_queried": genes,
            "total_variants": len(results),
            "variants": results[:100],
            "summary": {
                "variants_per_gene": gene_counts,
                "impact_distribution": impact_counts,
                "clinical_significance": significance_counts
            }
        }
        
    except Exception as e:
        return {"error": f"Error in gene variant query: {str(e)}"}

def query_variants_by_chromosome_function(chromosome, sample_ids=None, position_range=None):
    """Query variants by chromosome with optional position range filtering"""
    try:
        chr_clean = chromosome.replace('chr', '').upper()
        
        sample_filter = ""
        if sample_ids:
            samples = [s.strip() for s in sample_ids if s.strip()]
            if samples:
                sample_list = "', '".join(samples)
                sample_filter = f"AND v.sampleid IN ('{sample_list}')"
        
        position_filter = ""
        if position_range and '-' in position_range:
            try:
                start_pos, end_pos = position_range.split('-')
                position_filter = f"AND v.start BETWEEN {int(start_pos)} AND {int(end_pos)}"
            except ValueError:
                return {"error": "Invalid position range format. Use 'start-end' format."}
        
        query = f"""
        SELECT 
            v.sampleid,
            v.contigname,
            v.start,
            v.referenceallele,
            v.alternatealleles[1] as alternate_allele,
            v.qual,
            v.depth,
            v.information['af'] as allele_frequency_1000g,
            
            CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].symbol END as gene_symbol,
            CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].impact END as impact,
            CASE WHEN cardinality(v.annotations.vep) > 0 AND cardinality(v.annotations.vep[1].consequence) > 0 
                 THEN v.annotations.vep[1].consequence[1] END as consequence,
            
            a.attributes['CLNSIG'] as clinical_significance,
            a.attributes['CLNDN'] as associated_disease
            
        FROM {VARIANT_STORE_NAME} v
        LEFT JOIN {ANNOTATION_STORE_NAME} a ON (
            REPLACE(v.contigname, 'chr', '') = REPLACE(a.contigname, 'chr', '')
            AND v.start = a.start
            AND v.referenceallele = a.referenceallele
            AND v.alternatealleles[1] = a.alternatealleles[1]
        )
        WHERE v.qual > 30 
            AND contains(v.filters, 'PASS')
            AND REPLACE(v.contigname, 'chr', '') = '{chr_clean}'
            {position_filter}
            {sample_filter}
        ORDER BY v.start
        """
        
        results = execute_athena_query_on_stores(query)
        
        gene_counts = {}
        impact_counts = {}
        
        for row in results:
            gene = row.get('gene_symbol')
            impact = row.get('impact')
            
            if gene:
                gene_counts[gene] = gene_counts.get(gene, 0) + 1
            if impact:
                impact_counts[impact] = impact_counts.get(impact, 0) + 1
        
        return {
            "analysis_type": "Chromosome-Specific Analysis",
            "chromosome": chr_clean,
            "position_range": position_range if position_range else "entire chromosome",
            "total_variants": len(results),
            "variants": results[:100],
            "summary": {
                "top_genes": dict(sorted(gene_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                "impact_distribution": impact_counts
            }
        }
        
    except Exception as e:
        return {"error": f"Error in chromosome variant query: {str(e)}"}

def analyze_allele_frequencies_function(sample_ids=None, frequency_threshold=0.01):
    """Analyze allele frequencies and compare with 1000 Genomes Project data"""
    try:
        sample_filter = ""
        if sample_ids:
            samples = [s.strip() for s in sample_ids if s.strip()]
            if samples:
                sample_list = "', '".join(samples)
                sample_filter = f"AND v.sampleid IN ('{sample_list}')"
        
        query = f"""
        WITH variant_data AS (
            SELECT 
                v.sampleid,
                v.contigname,
                v.start,
                v.referenceallele,
                v.alternatealleles[1] as alternate_allele,
                v.qual,
                v.depth,
                
                CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].symbol END as vep_gene,
                CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].impact END as vep_impact,
                CASE WHEN cardinality(v.annotations.vep) > 0 AND cardinality(v.annotations.vep[1].consequence) > 0 
                     THEN v.annotations.vep[1].consequence[1] END as vep_consequence,
                
                a.attributes['CLNSIG'] as clinical_significance,
                split_part(a.attributes['GENEINFO'], ':', 1) as clinvar_gene,
                
                TRY_CAST(v.information['af'] as DOUBLE) as allele_frequency,
                TRY_CAST(v.information['dp'] as INTEGER) as total_depth,
                TRY_CAST(v.information['mq'] as DOUBLE) as mapping_quality
                
            FROM {VARIANT_STORE_NAME} v
            LEFT JOIN {ANNOTATION_STORE_NAME} a ON (
                REPLACE(v.contigname, 'chr', '') = REPLACE(a.contigname, 'chr', '')
                AND v.start = a.start
                AND v.referenceallele = a.referenceallele
                AND v.alternatealleles[1] = a.alternatealleles[1]
            )
            WHERE v.information['af'] IS NOT NULL
                AND v.qual > 30 
                AND contains(v.filters, 'PASS')
                {sample_filter}
        )

        SELECT 
            sampleid,
            COALESCE(clinvar_gene, vep_gene) as gene_symbol,
            contigname,
            start,
            referenceallele,
            alternate_allele,
            qual,
            depth,
            allele_frequency,
            total_depth,
            mapping_quality,
            clinical_significance,
            vep_impact,
            vep_consequence as consequence,
            
            CASE 
                WHEN qual > 100 AND depth > 20 THEN 'High Quality'
                WHEN qual > 50 AND depth > 10 THEN 'Medium Quality'
                ELSE 'Low Quality'
            END as quality_tier,
            
            CASE 
                WHEN allele_frequency < 0.001 THEN 'Very Rare'
                WHEN allele_frequency < {frequency_threshold} THEN 'Rare'
                WHEN allele_frequency < 0.05 THEN 'Uncommon'
                WHEN allele_frequency IS NOT NULL THEN 'Common'
                ELSE 'Unknown'
            END as rarity_category,
            
            CASE 
                WHEN allele_frequency IS NOT NULL AND allele_frequency > 0 
                THEN ROUND(-LOG10(allele_frequency), 2)
                ELSE NULL
            END as rarity_score,
            
            CASE 
                WHEN allele_frequency IS NOT NULL AND allele_frequency > 0 AND allele_frequency < 1
                THEN ROUND(2 * allele_frequency * (1 - allele_frequency), 4)
                ELSE NULL
            END as expected_het_frequency

        FROM variant_data
        WHERE allele_frequency IS NOT NULL
        ORDER BY allele_frequency ASC, qual DESC
        """
        
        results = execute_athena_query_on_stores(query)
        
        rarity_counts = {}
        quality_counts = {}
        rare_variants = []
        
        for row in results:
            rarity = row.get('rarity_category', 'Unknown')
            quality = row.get('quality_tier', 'Unknown')
            
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
            
            if rarity in ['Very Rare', 'Rare']:
                rare_variants.append(row)
        
        return {
            "analysis_type": "Allele Frequency Analysis",
            "frequency_threshold": frequency_threshold,
            "total_variants_with_frequency": len(results),
            "rarity_distribution": rarity_counts,
            "quality_distribution": quality_counts,
            "rare_variants_detail": rare_variants[:50],
            "summary_statistics": {
                "very_rare_count": rarity_counts.get('Very Rare', 0),
                "rare_count": rarity_counts.get('Rare', 0),
                "high_quality_count": quality_counts.get('High Quality', 0)
            }
        }
        
    except Exception as e:
        return {"error": f"Error in allele frequency analysis: {str(e)}"}

def compare_sample_variants_function(sample_ids):
    """Compare variant profiles between multiple samples for population analysis"""
    try:
        samples = [s.strip() for s in sample_ids if s.strip()]
        if len(samples) < 2:
            return {"error": "At least 2 sample IDs required for comparison"}
        
        sample_list = "', '".join(samples)
        
        query = f"""
        WITH sample_variants AS (
            SELECT 
                v.sampleid,
                v.qual,
                v.depth,
                v.referenceallele,
                v.alternatealleles[1] as alternate_allele,
                v.filters[1] as filter_status,
                
                CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].symbol END as vep_gene,
                CASE WHEN cardinality(v.annotations.vep) > 0 THEN v.annotations.vep[1].impact END as vep_impact,
                
                a.attributes['CLNSIG'] as clinical_significance,
                split_part(a.attributes['GENEINFO'], ':', 1) as clinvar_gene
                
            FROM {VARIANT_STORE_NAME} v
            LEFT JOIN {ANNOTATION_STORE_NAME} a ON (
                REPLACE(v.contigname, 'chr', '') = REPLACE(a.contigname, 'chr', '')
                AND v.start = a.start
                AND v.referenceallele = a.referenceallele
                AND v.alternatealleles[1] = a.alternatealleles[1]
            )
            WHERE v.filters[1] = 'PASS'
                AND v.sampleid IN ('{sample_list}')
        )

        SELECT 
            sampleid,
            COUNT(*) as total_variants,
            
            COUNT(CASE WHEN clinical_significance = 'Pathogenic' THEN 1 END) as pathogenic_count,
            COUNT(CASE WHEN clinical_significance = 'Likely_pathogenic' THEN 1 END) as likely_pathogenic_count,
            COUNT(CASE WHEN clinical_significance = 'Uncertain_significance' THEN 1 END) as vus_count,
            COUNT(CASE WHEN clinical_significance IN ('Benign', 'Likely_benign') THEN 1 END) as benign_count,
            
            COUNT(CASE WHEN vep_impact = 'HIGH' THEN 1 END) as high_impact_count,
            COUNT(CASE WHEN vep_impact = 'MODERATE' THEN 1 END) as moderate_impact_count,
            COUNT(CASE WHEN vep_impact = 'LOW' THEN 1 END) as low_impact_count,
            COUNT(CASE WHEN vep_impact = 'MODIFIER' THEN 1 END) as modifier_impact_count,
            
            ROUND(AVG(CAST(qual as DOUBLE)), 2) as avg_quality,
            ROUND(AVG(CAST(depth as DOUBLE)), 2) as avg_depth,
            MIN(qual) as min_quality,
            MAX(qual) as max_quality,
            
            COUNT(DISTINCT COALESCE(clinvar_gene, vep_gene)) as unique_genes_affected,
            
            COUNT(CASE 
                WHEN LENGTH(referenceallele) = 1 AND LENGTH(alternate_allele) = 1 
                THEN 1 
            END) as snv_count,
            
            COUNT(CASE 
                WHEN LENGTH(referenceallele) > LENGTH(alternate_allele) 
                THEN 1 
            END) as deletion_count,
            
            COUNT(CASE 
                WHEN LENGTH(referenceallele) < LENGTH(alternate_allele) 
                THEN 1 
            END) as insertion_count,
            
            ROUND(
                COUNT(CASE WHEN clinical_significance IN ('Pathogenic', 'Likely_pathogenic') THEN 1 END) * 100.0 / COUNT(*), 
                2
            ) as pathogenic_percentage

        FROM sample_variants
        GROUP BY sampleid
        ORDER BY sampleid
        """
        
        results = execute_athena_query_on_stores(query)
        
        return {
            "analysis_type": "Sample Comparison Analysis",
            "samples_compared": samples,
            "comparison_results": results,
            "summary": {
                "total_samples": len(results),
                "comparison_metrics": [
                    "total_variants", "pathogenic_count", "high_impact_count", 
                    "avg_quality", "unique_genes_affected", "pathogenic_percentage"
                ]
            }
        }
        
    except Exception as e:
        return {"error": f"Error in sample comparison: {str(e)}"}
