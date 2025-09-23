import os
import boto3
from botocore.client import Config
import json
from datetime import datetime
import csv
import io
import gzip

# Environment variables
REGION = os.environ.get('REGION','us-east-1')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID','123456789123')
BUCKET_NAME = os.environ.get('BUCKET_NAME','apj-omics-us')
MODEL_ID = os.environ.get('MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
modelid = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
#BATCH_JOB_QUEUE = os.environ.get('BATCH_JOB_QUEUE')

# Bedrock configuration
BEDROCK_CONFIG = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})

# Initialize clients
s3_client = boto3.client('s3')
sagemaker_runtime = boto3.client('runtime.sagemaker')
bedrock_agent_client = boto3.client("bedrock-agent-runtime", region_name=REGION, config=BEDROCK_CONFIG)
bedrock_client = boto3.client(service_name='bedrock-runtime', region_name=REGION, config=BEDROCK_CONFIG)


def create_response(status_code, body):
    """Create a standardized API response"""
    return {
        'statusCode': status_code,
        'body': json.dumps(body)
    }

def retrieve_and_generate(input_prompt, document_s3_uri, sourceType="S3"):
    """Execute Bedrock retrieve and generate operation"""
    if sourceType == "S3":
        return bedrock_agent_client.retrieve_and_generate(
            input={
                'text': input_prompt
            },
            retrieveAndGenerateConfiguration={
                'type': 'EXTERNAL_SOURCES',
                'externalSourcesConfiguration': {
                    'modelArn': f'arn:aws:bedrock:{REGION}::foundation-model/{MODEL_ID}',
                    "sources": [
                        {
                            "sourceType": sourceType,
                            "s3Location": {
                                "uri": document_s3_uri
                            }
                        }
                    ]
                }
            }
        )
    else:
        raise NotImplementedError("Expects an S3 URI Location")

def get_s3_object(prefix):
    """Search for an object in S3 with given prefix"""
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    if 'Contents' not in response or not response['Contents']:
        return None
    return response['Contents'][1]['Key']

def document_conversation(bedrock_client,
                     model_id,
                     input_text,
                     doc_bytes, format):
    """
    Sends a message to a model.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        input text : The input message.
        doc_bytes : The input document.
        format : document format

    Returns:
        response (JSON): The conversation that the model generated.

    """

    print(f"Generating message with model {model_id}")

    # Message to send.
    
    message = {
        "role": "user",
        "content": [
            {
                "text": input_text
            },
            {
                "document": {
                    "name": "MyDocument",
                    "format": format,
                    "source": {
                        "bytes": doc_bytes
                    }
                }
            }
        ]
    }

    messages = [message]

    # Send the message.
    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages
    )
    print(response)
    return response

def retrieve_existing_vep_report(patient_id):
    if not patient_id:
        return create_response(400, {'error': 'patient_id is required'})

    # Search for the VEP report in S3
    prefix=f"omics-test-out/{patient_id}/pubdir/reports/EnsemblVEP/report/"

    document_key = get_s3_object(prefix)
    if not document_key:
        return create_response(404, {'error': f'No VEP report found for patient_id: {patient_id}'})
    
    prompt = "Summarize the main findings including the tables and charts in the VEP report. If the information is not present, return None"
    #report = retrieve_and_generate(prompt, f"s3://{BUCKET_NAME}/{document_key}")
    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=document_key)
    print(document_key)
    content = response['Body'].read()
    report = document_conversation(bedrock_client, modelid, prompt, content, format="pdf")
    return create_response(200, {
        's3_uri': f"s3://{BUCKET_NAME}/{document_key}",
        'result': report
    })

def parse_vep_output(vcf_content):
    variants = []
    csq_fields = ["Allele", "Consequence", "IMPACT", "SYMBOL", "Gene", "Feature_type", 
                  "Feature", "BIOTYPE", "EXON", "INTRON", "HGVSc", "HGVSp", 
                  "cDNA_position", "CDS_position", "Protein_position", "Amino_acids", 
                  "Codons", "Existing_variation", "DISTANCE", "STRAND", "FLAGS", 
                  "SYMBOL_SOURCE", "HGNC_ID"]
    
    header_found = False
    header_columns = None
    
    # Process the VCF content in chunks
    chunk_size = 1000  # Adjust based on your needs
    current_chunk = []
    
    for line in vcf_content.split('\n'):
        if line.startswith('#CHROM'):
            header_found = True
            header_columns = line.strip().split('\t')
            continue
        
        if not header_found or not line.strip() or line.startswith('#'):
            continue
            
        current_chunk.append(line)
        
        # Process chunk when it reaches the specified size
        if len(current_chunk) >= chunk_size:
            variants.extend(process_variant_chunk(current_chunk, csq_fields))
            current_chunk = []
    
    # Process any remaining variants
    if current_chunk:
        variants.extend(process_variant_chunk(current_chunk, csq_fields))
    
    return variants

def process_variant_chunk(chunk, csq_fields):
    chunk_variants = []
    for line in chunk:
        fields = line.strip().split('\t')
        if len(fields) < 8:
            continue
            
        # Extract basic variant information
        chrom, pos, id_, ref, alt, qual, filter_, info = fields[:8]
        
        # Parse INFO field to get CSQ
        info_dict = {}
        for info_field in info.split(';'):
            if '=' in info_field:
                key, value = info_field.split('=', 1)
                info_dict[key] = value
        
        if 'CSQ' not in info_dict:
            continue
            
        # Process each CSQ annotation
        for csq in info_dict['CSQ'].split(','):
            csq_values = csq.split('|')
            if len(csq_values) != len(csq_fields):
                continue
                
            variant = {
                'chr': chrom,
                'pos': int(pos),
                'id': id_,
                'ref': ref,
                'alt': alt,
                'qual': qual,
                'filter': filter_
            }
            
            for field, value in zip(csq_fields, csq_values):
                variant[field.lower()] = value if value else None
                
            for key, value in info_dict.items():
                if key != 'CSQ':
                    variant[f'info_{key.lower()}'] = value
                    
            chunk_variants.append(variant)
    
    return chunk_variants

def analyze_variants(variants):
    """
    Analyze variants with memory optimizations
    Args:
        variants: List of variants to analyze
    """
    # Initialize analysis structure with limits
    MAX_STORED_VARIANTS = 1000  # Limit for storing detailed variants
    MAX_GENES = 100            # Limit for number of genes to track
    
    analysis = {
        'total_variants': len(variants),
        'variants_per_chromosome': {},
        'impact_summary': {
            'HIGH': 0,
            'MODERATE': 0,
            'LOW': 0,
            'MODIFIER': 0
        },
        'consequence_types': {},
        'transcript_effects': {
            'coding_variants': [],
            'non_coding_variants': [],
            'splice_variants': [],
            'regulatory_variants': []
        },
        'gene_impacts': {},
        'biotype_summary': {},
        'detailed_variants': []
    }
    
    # Track high-impact genes separately for efficient sorting
    gene_impact_scores = {}
    
    for variant in variants:
        # Basic variant location
        chrom = variant['chr']
        analysis['variants_per_chromosome'][chrom] = analysis['variants_per_chromosome'].get(chrom, 0) + 1
        
        # Impact analysis
        impact = variant.get('impact', 'UNKNOWN')
        analysis['impact_summary'][impact] = analysis['impact_summary'].get(impact, 0) + 1
        
        # Process consequences
        consequences = variant.get('consequence', '').split('&')
        for consequence in consequences:
            if not consequence:
                continue
                
            analysis['consequence_types'][consequence] = analysis['consequence_types'].get(consequence, 0) + 1
            
            # Create basic variant info (only store essential data)
            variant_info = {
                'location': f"{variant['chr']}:{variant['pos']}",
                'gene': variant.get('symbol')
            }
            
            # Categorize effects with size limits
            if any(term in consequence.lower() for term in ['missense', 'nonsense', 'frameshift', 'inframe']):
                if len(analysis['transcript_effects']['coding_variants']) < MAX_STORED_VARIANTS:
                    variant_info.update({
                        'consequence': consequence,
                        'hgvsp': variant.get('hgvsp'),
                        'impact': impact
                    })
                    analysis['transcript_effects']['coding_variants'].append(variant_info)
                    
            elif 'splice' in consequence.lower():
                if len(analysis['transcript_effects']['splice_variants']) < MAX_STORED_VARIANTS:
                    variant_info['hgvsc'] = variant.get('hgvsc')
                    analysis['transcript_effects']['splice_variants'].append(variant_info)
                    
            elif 'regulatory' in consequence.lower():
                if len(analysis['transcript_effects']['regulatory_variants']) < MAX_STORED_VARIANTS:
                    analysis['transcript_effects']['regulatory_variants'].append(variant_info)
                    
            elif 'non_coding' in consequence.lower():
                if len(analysis['transcript_effects']['non_coding_variants']) < MAX_STORED_VARIANTS:
                    analysis['transcript_effects']['non_coding_variants'].append(variant_info)

        # Track gene impacts efficiently
        gene = variant.get('symbol')
        if gene:
            if gene not in gene_impact_scores:
                gene_impact_scores[gene] = {
                    'high_impact': 0,
                    'moderate_impact': 0,
                    'low_impact': 0,
                    'modifier_impact': 0,
                    'total_variants': 0,
                    'variants': []
                }
            
            impact_key = f"{impact.lower()}_impact"
            gene_impact_scores[gene][impact_key] += 1
            gene_impact_scores[gene]['total_variants'] += 1
            
            # Store limited variants per gene
            if len(gene_impact_scores[gene]['variants']) < 50:  # Limit variants per gene
                gene_impact_scores[gene]['variants'].append({
                    'location': f"{variant['chr']}:{variant['pos']}",
                    'consequence': consequences[0] if consequences else None,
                    'hgvsc': variant.get('hgvsc'),
                    'hgvsp': variant.get('hgvsp')
                })

        # Biotype summary
        biotype = variant.get('biotype')
        if biotype:
            analysis['biotype_summary'][biotype] = analysis['biotype_summary'].get(biotype, 0) + 1

        # Store detailed variants for high and moderate impacts
        if impact in ['HIGH', 'MODERATE'] and len(analysis['detailed_variants']) < MAX_STORED_VARIANTS:
            analysis['detailed_variants'].append({
                'location': f"{variant['chr']}:{variant['pos']}",
                'ref': variant['ref'],
                'alt': variant['alt'],
                'gene': gene,
                'consequence': consequences[0] if consequences else None,
                'impact': impact,
                'hgvsc': variant.get('hgvsc'),
                'hgvsp': variant.get('hgvsp')
            })

    # Process gene impacts and sort for most significant
    sorted_genes = sorted(
        gene_impact_scores.items(),
        key=lambda x: (x[1]['high_impact'], x[1]['moderate_impact'], x[1]['total_variants']),
        reverse=True
    )[:MAX_GENES]
    
    analysis['gene_impacts'] = {
        gene: data for gene, data in sorted_genes
    }

    # Generate summary statistics
    analysis['summary'] = {
        'total_variants': analysis['total_variants'],
        'high_impact_variants': analysis['impact_summary']['HIGH'],
        'moderate_impact_variants': analysis['impact_summary']['MODERATE'],
        'coding_variants': len(analysis['transcript_effects']['coding_variants']),
        'splice_variants': len(analysis['transcript_effects']['splice_variants']),
        'most_affected_genes': [
            {
                'gene': gene,
                'high_impact': data['high_impact'],
                'moderate_impact': data['moderate_impact'],
                'total_variants': data['total_variants']
            }
            for gene, data in sorted_genes[:10]  # Top 10 genes only
        ],
        'top_consequences': sorted(
            analysis['consequence_types'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
    }

    return analysis

def vep_feature_extraction(patient_id):
    if not patient_id:
        return create_response(400, {'error': 'patient_id is required'})
        
    key = f"omics-test-out/{patient_id}/pubdir/annotation/null/null.ann.vcf.gz"
    
    try:
        variants = []
        # Stream the file in chunks
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        chunk_size = 1024 * 1024  # 1MB chunks
        
        with gzip.GzipFile(fileobj=response['Body']) as gz:
            buffer = ""
            while True:
                chunk = gz.read(chunk_size)
                if not chunk:
                    break
                
                try:
                    buffer += chunk.decode('utf-8')
                except UnicodeDecodeError:
                    buffer += chunk.decode('latin-1')
                
                lines = buffer.split('\n')
                # Keep the last incomplete line in the buffer
                buffer = lines[-1]
                # Process complete lines
                if len(lines) > 1:
                    chunk_variants = parse_vep_output('\n'.join(lines[:-1]))
                    variants.extend(chunk_variants)
        
        # Process any remaining content in the buffer
        if buffer:
            chunk_variants = parse_vep_output(buffer)
            variants.extend(chunk_variants)
        
        analysis = analyze_variants(variants)
        return analysis
        
    except Exception as e:
        return create_response(500, {'error': f'Error processing VCF file: {str(e)}'})
        

def store_large_response_in_s3(response):
    """Store large response in S3 and return a reference"""
    try:
        s3 = boto3.client('s3')
        bucket_name = 'apj-omics-us'  # Replace with your S3 bucket name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        key = f'responses/{timestamp}.json'
        
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(response)
        )
        
        return {
            "TEXT": {
                "body": f"Response was too large and has been stored in S3. \n"
                        f"Location: s3://{bucket_name}/{key}"
            }
        }
    except Exception as e:
        return {
            "TEXT": {
                "body": f"Error storing large response: {str(e)}"
            }
        }

def handle_response(response):
    """Handle response size appropriately"""
    try:
        # Check response size
        response_size = len(json.dumps(response))
        
        if response_size > 24000:  # Leave buffer for metadata
            return store_large_response_in_s3(response)
        
        return response
        
    except Exception as e:
        return {
            "TEXT": {
                "body": f"Error handling response: {str(e)}"
            }
        }

def lambda_handler(event, context):
    try:
        actionGroup = event['actionGroup']
        function = event['function']
        parameters = event.get('parameters', [])
        
        # Initialize default response
        responseBody = {
            "TEXT": {
                "body": "Error, no function was called"
            }
        }
        
        # Handle response size before returning
        # final_response = handle_response(responseBody)
        
        # return final_response
        
    except Exception as e:
        return {
            "TEXT": {
                "body": f"An error occurred: {str(e)}"
            }
        }  
    if function == 'retrieve_existing_vep_report':
        patient_id = None
        for param in parameters:
            if param["name"] == "patient_id":
                patient_id = param["value"]

        if not patient_id:
            raise Exception("Missing mandatory parameter: patient_id")
        vep_report = retrieve_existing_vep_report(patient_id)
        responseBody =  {
            'TEXT': {
                "body": f"Vep report for patient {patient_id}: {vep_report}"
            }
        }
        # Handle response size before creating the final response structure
        handled_response = handle_response(responseBody)
    elif function == 'vep_feature_extraction':
        patient_id = None
        for param in parameters:
            if param["name"] == "patient_id":
                patient_id = param["value"]

        feature_extraction = vep_feature_extraction(patient_id)

        responseBody =  {
            'TEXT': {
                "body": str(feature_extraction)
            }
        }
    # Handle response size before creating the final response structure
        handled_response = handle_response(responseBody)
    action_response = {
        'actionGroup': actionGroup,
        'function': function,
        'functionResponse': {
            'responseBody': handled_response
        }

    }
     # Handle response size before creating the final response structure
    #    handled_response = handle_response(responseBody)
    function_response = {'response': action_response, 'messageVersion': event['messageVersion']}
    print("Response: {}".format(function_response))

    return function_response

if __name__ == "__main__":
    # Example usage
    import os
    event = {
        "actionGroup": "actionGroup",
        "function": "vep_feature_extraction",
        "parameters": [
            {"name": "patient_id", "value": "3186764"}
        ],
        "messageVersion": "1.0"
    }

    print(lambda_handler(event, None))
    