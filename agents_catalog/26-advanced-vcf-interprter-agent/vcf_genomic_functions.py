"""
VCF Genomic Analysis Functions Module
"""

import os
import boto3
from botocore.client import Config
import json
from datetime import datetime
import time
import re
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

# Environment variables from Lambda
MODEL_ID = os.environ.get('MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'VcfImportTracking3')
LAKE_FORMATION_DATABASE = os.environ.get('LAKE_FORMATION_DATABASE', 'vcf_analysis_db')

# Genomic analysis constants from Lambda
PATHOGENIC_SIGNIFICANCE = ['Pathogenic', 'Likely_pathogenic', 'Pathogenic/Likely_pathogenic']
BENIGN_SIGNIFICANCE = ['Benign', 'Likely_benign', 'Benign/Likely_benign']
HIGH_IMPACT_CONSEQUENCES = ['stop_gained', 'stop_lost', 'start_lost', 'frameshift_variant', 'splice_donor_variant', 'splice_acceptor_variant']
MODERATE_IMPACT_CONSEQUENCES = ['missense_variant', 'inframe_deletion', 'inframe_insertion']

# Bedrock configuration from Lambda
BEDROCK_CONFIG = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})

# Initialize clients
def initialize_aws_clients():
    """Initialize AWS clients with error handling"""
    clients = {}
    
    try:
        clients['dynamodb'] = boto3.resource('dynamodb', region_name=REGION)
        print("✅ DynamoDB client initialized")
    except Exception as e:
        print(f"⚠️ DynamoDB client failed: {e}")
        clients['dynamodb'] = None
    
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
        clients['glue'] = boto3.client('glue', region_name=REGION)
        print("✅ Glue client initialized")
    except Exception as e:
        print(f"⚠️ Glue client failed: {e}")
        clients['glue'] = None
    
    try:
        clients['ram'] = boto3.client('ram', region_name=REGION)
        print("✅ RAM client initialized")
    except Exception as e:
        print(f"⚠️ RAM client failed: {e}")
        clients['ram'] = None
    
    return clients

# Initialize all clients
aws_clients = initialize_aws_clients()
dynamodb = aws_clients['dynamodb']
athena_client = aws_clients['athena']
bedrock_client = aws_clients['bedrock']
glue_client = aws_clients['glue']
ram_client = aws_clients['ram']

print(f"Region: {REGION}")
print(f"Account ID: {ACCOUNT_ID}")

# === CORE GENOMIC ANALYSIS FUNCTIONS ===

def parse_user_query(query):
    """
    Enhanced parser for genomic analysis queries
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

def get_database_info_from_dynamodb(patient_ids=None):
    """
    Get database and table information from DynamoDB
    """
    if dynamodb is None:
        print("DynamoDB client not available")
        return {}
        
    try:
        table = dynamodb.Table(DYNAMODB_TABLE)
        
        if patient_ids:
            # Get specific patients
            db_info = {}
            for patient_id in patient_ids:
                try:
                    response = table.get_item(Key={'SampleID': patient_id})
                    if 'Item' in response:
                        item = response['Item']
                        if item.get('Status') == 'COMPLETED':
                            db_info[patient_id] = {
                                'database': item.get('TargetDatabase', LAKE_FORMATION_DATABASE),
                                'table': item.get('TargetTable', 'hcagentsvs4'),
                                'athena_path': item.get('ExpectedAthenaPath', f'{LAKE_FORMATION_DATABASE}.hcagentsvs4'),
                                's3_uri': item.get('S3Uri', ''),
                                'status': item.get('Status', ''),
                                'completion_time': item.get('CompletionTime', '')
                            }
                except Exception as e:
                    print(f"Error getting info for patient {patient_id}: {e}")
            return db_info
        else:
            # Get all completed patients
            response = table.scan(
                FilterExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'Status'},
                ExpressionAttributeValues={':status': 'COMPLETED'}
            )
            
            db_info = {}
            for item in response['Items']:
                patient_id = item['SampleID']
                db_info[patient_id] = {
                    'database': item.get('TargetDatabase', LAKE_FORMATION_DATABASE),
                    'table': item.get('TargetTable', 'hcagentsvs4'),
                    'athena_path': item.get('ExpectedAthenaPath', f'{LAKE_FORMATION_DATABASE}.hcagentsvs4'),
                    's3_uri': item.get('S3Uri', ''),
                    'status': item.get('Status', ''),
                    'completion_time': item.get('CompletionTime', '')
                }
            
            return db_info
            
    except Exception as e:
        print(f"Error getting database info: {e}")
        return {}

def execute_athena_query(query, database=None):
    """
    Execute Athena query and return results as list of dictionaries
    """
    if athena_client is None:
        raise Exception("Athena client not available. Please configure AWS credentials and region.")
        
    try:
        if not database:
            database = LAKE_FORMATION_DATABASE
        
        print(f"Executing query: {query}")
        
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': database},
            WorkGroup='datasets-workgroup',
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
        
        # Get results
        results = athena_client.get_query_results(QueryExecutionId=query_id)
        
        # Convert to list of dictionaries instead of DataFrame
        columns = [col['Name'] for col in results['ResultSet']['ResultSetMetadata']['ColumnInfo']]
        rows = []
        
        for row in results['ResultSet']['Rows'][1:]:  # Skip header
            row_data = [col.get('VarCharValue', '') for col in row['Data']]
            row_dict = dict(zip(columns, row_data))
            rows.append(row_dict)
        
        return rows
        
    except Exception as e:
        print(f"Error executing Athena query: {e}")
        raise e

# === MAIN ANALYSIS FUNCTIONS ===

def execute_genomic_analysis(analysis_request):
    """
    Execute the appropriate genomic analysis based on the request
    """
    query_type = analysis_request['query_type']
    patient_ids = analysis_request['patient_ids']
    genes = analysis_request.get('genes', [])
    chromosomes = analysis_request.get('chromosomes', [])
    
    print(f"Executing analysis: {query_type} for patients: {patient_ids}")
    
    # Get database and table information
    db_info = get_database_info_from_dynamodb(patient_ids)
    
    if not db_info:
        return {
            'error': 'No genomic data found for the specified patient(s). Please check if the VCF files have been processed.'
        }
    
    # Execute appropriate analysis
    if query_type == 'variant_count':
        return count_variants_for_patients(patient_ids, db_info)
    elif query_type == 'common_variants':
        return find_common_variants(patient_ids, db_info)
    elif query_type == 'pathogenic_variants':
        return find_pathogenic_variants(patient_ids, db_info)
    elif query_type == 'benign_variants':
        return find_benign_variants(patient_ids, db_info)
    elif query_type == 'pharmacogenomic_variants':
        return find_pharmacogenomic_variants(patient_ids, db_info)
    elif query_type == 'gene_analysis':
        return analyze_gene_variants(patient_ids, db_info, genes)
    elif query_type == 'protein_affecting_variants':
        return find_protein_affecting_variants(patient_ids, db_info)
    elif query_type == 'clinical_significance':
        return analyze_clinical_significance(patient_ids, db_info)
    elif query_type == 'chromosome_analysis':
        return analyze_chromosome_variants(patient_ids, db_info, chromosomes)
    elif query_type == 'frequency_analysis':
        return analyze_variant_frequencies(patient_ids, db_info)
    elif query_type == 'annotated_variants':
        return get_annotated_variants(patient_ids, db_info)
    elif query_type == 'compare_patients':
        return compare_patients(patient_ids, db_info)
    elif query_type == 'list_patients':
        return list_available_patients_internal()
    else:
        return get_general_patient_info(patient_ids, db_info)

def count_variants_for_patients(patient_ids, db_info):
    """
    Count variants for specific patients
    """
    try:
        results = {}
        
        for patient_id in patient_ids:
            if patient_id in db_info:
                table_path = db_info[patient_id]['athena_path']
                
                query = f"""
                SELECT COUNT(*) as variant_count
                FROM {table_path}
                WHERE sampleid = '{patient_id}'
                """
                
                rows = execute_athena_query(query)
                if rows:
                    results[patient_id] = int(rows[0]['variant_count'])
                else:
                    results[patient_id] = 0
            else:
                results[patient_id] = f"No data found for patient {patient_id}"
        
        # Generate natural language response
        response_text = "Variant count analysis:\n"
        for patient_id, count in results.items():
            if isinstance(count, int):
                response_text += f"- Patient {patient_id}: {count:,} variants\n"
            else:
                response_text += f"- Patient {patient_id}: {count}\n"
        
        return {
            'analysis_type': 'Variant Count',
            'results': results,
            'summary': response_text
        }
        
    except Exception as e:
        return {'error': f'Error counting variants: {str(e)}'}

def find_pathogenic_variants(patient_ids, db_info):
    """
    Find pathogenic variants using annotation store join
    """
    try:
        # Get the table path
        table_path = list(db_info.values())[0]['athena_path']
        
        # Create patient filter if specific patients requested
        patient_filter = ""
        if patient_ids:
            patient_list = "', '".join(patient_ids)
            patient_filter = f"AND variants.sampleid IN ('{patient_list}')"
        
        # Use pathogenic significance constants
        pathogenic_list = "', '".join(PATHOGENIC_SIGNIFICANCE)
        
        # Complex join query with annotation stores
        query = f"""
        SELECT 
            variants.sampleid,
            variants.contigname,
            variants.start,
            variants.referenceallele,
            variants.alternatealleles,
            variants.attributes AS variant_attributes,
            clinvar.attributes['CLNSIG'] as clinical_significance,
            clinvar.attributes['GENEINFO'] as gene_info,
            clinvar.attributes['CLNDN'] as disease_name,
            clinvar.attributes['CLNREVSTAT'] as review_status
        FROM {table_path} as variants 
        INNER JOIN clinvarannotation as clinvar ON 
            variants.contigname = CONCAT('chr', clinvar.contigname) 
            AND variants.start = clinvar.start 
            AND variants."end" = clinvar."end" 
            AND variants.referenceallele = clinvar.referenceallele 
            AND variants.alternatealleles = clinvar.alternatealleles 
        WHERE clinvar.attributes['CLNSIG'] IN ('{pathogenic_list}')
        {patient_filter}
        ORDER BY variants.sampleid, variants.contigname, variants.start
        """
        
        rows = execute_athena_query(query)
        
        if not rows:
            return {
                'analysis_type': 'Pathogenic Variants',
                'results': [],
                'summary': 'No pathogenic variants found with ClinVar annotations.'
            }
        
        # Group by patient
        patient_counts = {}
        gene_counts = {}
        
        for row in rows:
            patient = row['sampleid']
            gene = row['gene_info']
            
            patient_counts[patient] = patient_counts.get(patient, 0) + 1
            gene_counts[gene] = gene_counts.get(gene, 0) + 1
        
        response_text = f"Pathogenic variants analysis:\n"
        for patient_id, count in patient_counts.items():
            response_text += f"- Patient {patient_id}: {count} pathogenic variants\n"
        
        response_text += f"\nTop affected genes:\n"
        for gene, count in list(gene_counts.items())[:5]:
            response_text += f"- {gene}: {count} pathogenic variants\n"
        
        response_text += f"\nTotal: {len(rows)} pathogenic variants found\n"
        
        return {
            'analysis_type': 'Pathogenic Variants',
            'results': rows,
            'patient_counts': patient_counts,
            'gene_counts': gene_counts,
            'summary': response_text,
            'total_count': len(rows)
        }
        
    except Exception as e:
        return {'error': f'Error finding pathogenic variants: {str(e)}'}

def find_pharmacogenomic_variants(patient_ids, db_info):
    """
    Find pharmacogenomic variants using ClinVar annotations
    """
    try:
        table_path = list(db_info.values())[0]['athena_path']
        
        patient_filter = ""
        if patient_ids:
            patient_list = "', '".join(patient_ids)
            patient_filter = f"AND variants.sampleid IN ('{patient_list}')"
        
        query = f"""
        SELECT 
            variants.sampleid,
            variants.contigname,
            variants.start,
            variants.referenceallele,
            variants.alternatealleles,
            clinvar.attributes['CLNSIG'] as clinical_significance,
            clinvar.attributes['GENEINFO'] as gene_info,
            clinvar.attributes['CLNDN'] as disease_name,
            clinvar.attributes['CLNREVSTAT'] as review_status
        FROM {table_path} as variants 
        INNER JOIN clinvarannotation as clinvar ON 
            variants.contigname = CONCAT('chr', clinvar.contigname) 
            AND variants.start = clinvar.start 
            AND variants."end" = clinvar."end" 
            AND variants.referenceallele = clinvar.referenceallele 
            AND variants.alternatealleles = clinvar.alternatealleles 
        WHERE (
            LOWER(clinvar.attributes['CLNDN']) LIKE '%drug%' OR
            LOWER(clinvar.attributes['CLNDN']) LIKE '%medication%' OR
            LOWER(clinvar.attributes['CLNDN']) LIKE '%pharmacogenomic%' OR
            LOWER(clinvar.attributes['GENEINFO']) IN ('cyp2d6', 'cyp2c19', 'cyp2c9', 'cyp3a4', 'cyp3a5', 'slco1b1', 'dpyd', 'tpmt', 'ugt1a1')
        )
        {patient_filter}
        ORDER BY variants.sampleid, variants.contigname, variants.start
        """
        
        rows = execute_athena_query(query)
        
        if not rows:
            return {
                'analysis_type': 'Pharmacogenomic Variants',
                'results': [],
                'summary': 'No pharmacogenomic variants found.'
            }
        
        patient_counts = {}
        for row in rows:
            patient = row['sampleid']
            patient_counts[patient] = patient_counts.get(patient, 0) + 1
        
        response_text = f"Pharmacogenomic variants analysis:\n"
        for patient_id, count in patient_counts.items():
            response_text += f"- Patient {patient_id}: {count} pharmacogenomic variants\n"
        
        response_text += f"\nTotal: {len(rows)} pharmacogenomic variants found\n"
        
        return {
            'analysis_type': 'Pharmacogenomic Variants',
            'results': rows,
            'patient_counts': patient_counts,
            'summary': response_text,
            'total_count': len(rows)
        }
        
    except Exception as e:
        return {'error': f'Error finding pharmacogenomic variants: {str(e)}'}

def analyze_clinical_significance(patient_ids, db_info):
    """
    Analyze distribution of clinical significance across variants
    """
    try:
        table_path = list(db_info.values())[0]['athena_path']
        
        patient_filter = ""
        if patient_ids:
            patient_list = "', '".join(patient_ids)
            patient_filter = f"AND variants.sampleid IN ('{patient_list}')"
        
        query = f"""
        SELECT 
            variants.sampleid,
            clinvar.attributes['CLNSIG'] as clinical_significance,
            COUNT(*) as variant_count
        FROM {table_path} as variants 
        INNER JOIN clinvarannotation as clinvar ON 
            variants.contigname = CONCAT('chr', clinvar.contigname) 
            AND variants.start = clinvar.start 
            AND variants."end" = clinvar."end" 
            AND variants.referenceallele = clinvar.referenceallele 
            AND variants.alternatealleles = clinvar.alternatealleles 
        WHERE clinvar.attributes['CLNSIG'] IS NOT NULL
        {patient_filter}
        GROUP BY variants.sampleid, clinvar.attributes['CLNSIG']
        ORDER BY variants.sampleid, variant_count DESC
        """
        
        rows = execute_athena_query(query)
        
        if not rows:
            return {
                'analysis_type': 'Clinical Significance Analysis',
                'results': [],
                'summary': 'No variants with clinical significance found.'
            }
        
        # Create summary by patient
        patient_summary = {}
        for record in rows:
            patient = record['sampleid']
            significance = record['clinical_significance']
            count = int(record['variant_count'])
            
            if patient not in patient_summary:
                patient_summary[patient] = {}
            patient_summary[patient][significance] = count
        
        response_text = f"Clinical significance analysis:\n"
        for patient, significances in patient_summary.items():
            response_text += f"\nPatient {patient}:\n"
            total = sum(significances.values())
            for sig, count in sorted(significances.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total) * 100
                response_text += f"  - {sig}: {count} variants ({percentage:.1f}%)\n"
        
        return {
            'analysis_type': 'Clinical Significance Analysis',
            'results': rows,
            'patient_summary': patient_summary,
            'summary': response_text,
            'total_count': len(rows)
        }
        
    except Exception as e:
        return {'error': f'Error analyzing clinical significance: {str(e)}'}

def list_available_patients_internal():
    """
    List all available patients in the system
    """
    try:
        db_info = get_database_info_from_dynamodb()
        
        if not db_info:
            return {
                'analysis_type': 'Available Patients',
                'results': [],
                'summary': 'No patients found in the system.'
            }
        
        patients = []
        for patient_id, info in db_info.items():
            patients.append({
                'patient_id': patient_id,
                'status': info['status'],
                'completion_time': info['completion_time'],
                'database': info['database'],
                'table': info['table']
            })
        
        response_text = f"Available patients ({len(patients)} total):\n"
        for patient in patients:
            response_text += f"- {patient['patient_id']} (Status: {patient['status']})\n"
        
        return {
            'analysis_type': 'Available Patients',
            'results': patients,
            'summary': response_text,
            'total_count': len(patients)
        }
        
    except Exception as e:
        return {'error': f'Error listing patients: {str(e)}'}

# Additional analysis functions (stubs for missing functions)
def find_common_variants(patient_ids, db_info):
    """Find variants shared across multiple patients"""
    return {'error': 'Common variants analysis not yet implemented'}

def find_benign_variants(patient_ids, db_info):
    """Find benign variants"""
    return {'error': 'Benign variants analysis not yet implemented'}

def analyze_gene_variants(patient_ids, db_info, genes):
    """Analyze variants in specific genes"""
    return {'error': 'Gene analysis not yet implemented'}

def find_protein_affecting_variants(patient_ids, db_info):
    """Find protein affecting variants"""
    return {'error': 'Protein affecting variants analysis not yet implemented'}

def analyze_chromosome_variants(patient_ids, db_info, chromosomes):
    """Analyze variants by chromosome"""
    return {'error': 'Chromosome analysis not yet implemented'}

def analyze_variant_frequencies(patient_ids, db_info):
    """Analyze variant frequencies"""
    return {'error': 'Frequency analysis not yet implemented'}

def get_annotated_variants(patient_ids, db_info):
    """Get annotated variants"""
    return {'error': 'Annotated variants analysis not yet implemented'}

def compare_patients(patient_ids, db_info):
    """Compare patients"""
    return {'error': 'Patient comparison not yet implemented'}

def get_general_patient_info(patient_ids, db_info):
    """Get general patient information"""
    return {'error': 'General patient info not yet implemented'}
