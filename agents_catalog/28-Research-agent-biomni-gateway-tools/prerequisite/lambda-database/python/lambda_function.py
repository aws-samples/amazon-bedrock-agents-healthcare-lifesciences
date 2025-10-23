import json
import sys
import os

# Add the current directory to the path to import database functions
sys.path.append(os.path.dirname(__file__))

# Import all the database query functions
from database import (
    query_uniprot,
    query_alphafold,
    query_interpro,
    query_pdb,
    query_pdb_identifiers,
    query_stringdb,
    query_paleobiology,
    query_jaspar,
    query_worms,
    query_cbioportal,
    query_clinvar,
    query_geo,
    query_dbsnp,
    query_ucsc,
    query_ensembl,
    query_opentarget,
    query_monarch,
    query_openfda,
    query_clinicaltrials,
    query_gwas_catalog,
    query_gnomad,
    query_reactome,
    query_regulomedb,
    query_pride,
    query_gtopdb,
    query_mpd,
    query_emdb,
    query_synapse
)

def lambda_handler(event, context):
    """
    Lambda handler for the Database Gateway.
    
    This function routes requests to the appropriate database query function
    based on the tool name specified in the context.
    """
    try:
        # Get the tool name from the context
        tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        print(f"Tool name: {tool_name}")
        print(f"Event: {event}")
        
        # Remove any prefix from tool name if present
        delimiter = "___"
        if delimiter in tool_name:
            tool_name = tool_name[tool_name.index(delimiter) + len(delimiter):]
        
        print(f"Processed tool name: {tool_name}")
        
        # Route to the appropriate function based on tool name
        if tool_name == 'query_uniprot':
            result = query_uniprot(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint'),
                max_results=event.get('max_results', 5)
            )
        elif tool_name == 'query_alphafold':
            result = query_alphafold(
                uniprot_id=event.get('uniprot_id'),
                endpoint=event.get('endpoint', 'prediction'),
                residue_range=event.get('residue_range'),
                download=event.get('download', False),
                output_dir=event.get('output_dir'),
                file_format=event.get('file_format', 'pdb'),
                model_version=event.get('model_version', 'v4'),
                model_number=event.get('model_number', 1)
            )
        elif tool_name == 'query_interpro':
            result = query_interpro(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_pdb':
            result = query_pdb(
                prompt=event.get('prompt'),
                query=event.get('query')
            )
        elif tool_name == 'query_pdb_identifiers':
            result = query_pdb_identifiers(
                identifiers=event.get('identifiers'),
                return_type=event.get('return_type', 'entry'),
                download=event.get('download', False),
                attributes=event.get('attributes')
            )
        elif tool_name == 'query_stringdb':
            result = query_stringdb(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_paleobiology':
            result = query_paleobiology(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_jaspar':
            result = query_jaspar(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_worms':
            result = query_worms(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_cbioportal':
            result = query_cbioportal(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_clinvar':
            result = query_clinvar(
                prompt=event.get('prompt'),
                search_term=event.get('search_term')
            )
        elif tool_name == 'query_geo':
            result = query_geo(
                prompt=event.get('prompt'),
                search_term=event.get('search_term')
            )
        elif tool_name == 'query_dbsnp':
            result = query_dbsnp(
                prompt=event.get('prompt'),
                search_term=event.get('search_term')
            )
        elif tool_name == 'query_ucsc':
            result = query_ucsc(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_ensembl':
            result = query_ensembl(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_opentarget':
            result = query_opentarget(
                prompt=event.get('prompt'),
                query=event.get('query')
            )
        elif tool_name == 'query_monarch':
            result = query_monarch(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_openfda':
            result = query_openfda(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_clinicaltrials':
            result = query_clinicaltrials(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_gwas_catalog':
            result = query_gwas_catalog(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_gnomad':
            result = query_gnomad(
                prompt=event.get('prompt'),
                gene_symbol=event.get('gene_symbol'),
                variant_id=event.get('variant_id')
            )
        elif tool_name == 'query_reactome':
            result = query_reactome(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_regulomedb':
            result = query_regulomedb(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_pride':
            result = query_pride(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_gtopdb':
            result = query_gtopdb(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_mpd':
            result = query_mpd(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_emdb':
            result = query_emdb(
                prompt=event.get('prompt'),
                endpoint=event.get('endpoint')
            )
        elif tool_name == 'query_synapse':
            result = query_synapse(
                prompt=event.get('prompt'),
                query_term=event.get('query_term'),
                return_fields=event.get('return_fields', ["name", "node_type", "description"]),
                max_results=event.get('max_results', 20),
                query_type=event.get('query_type', 'file'),
                verbose=event.get('verbose', True)
            )
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unknown tool: {tool_name}',
                    'available_tools': [
                        'query_uniprot', 'query_alphafold', 'query_interpro', 'query_pdb',
                        'query_pdb_identifiers', 'query_stringdb', 
                        'query_paleobiology', 'query_jaspar', 'query_worms', 'query_cbioportal',
                        'query_clinvar', 'query_geo', 'query_dbsnp', 'query_ucsc', 'query_ensembl',
                        'query_opentarget', 'query_monarch', 'query_openfda', 'query_clinicaltrials',
                        'query_gwas_catalog', 'query_gnomad', 'query_reactome', 'query_regulomedb',
                        'query_pride', 'query_gtopdb',  'query_mpd', 'query_emdb',
                        'query_synapse'
                    ]
                })
            }
        print(f"Processed results: {result}")
        # Return successful response
        return {
            'statusCode': 200,
            'body': json.dumps(result) if isinstance(result, dict) else str(result)
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}',
                'tool_name': tool_name if 'tool_name' in locals() else 'unknown'
            })
        }