import json
import sys
import os

# Add the current directory to the path to import cancer_biology functions
sys.path.append(os.path.dirname(__file__))

# Import all the cancer biology analysis functions
from cancer_biology import (
    analyze_ddr_network_in_cancer,
    analyze_cell_senescence_and_apoptosis,
    detect_and_annotate_somatic_mutations,
    detect_and_characterize_structural_variations,
    perform_gene_expression_nmf_analysis,
    analyze_copy_number_purity_ploidy_and_focal_events
)

def lambda_handler(event, context):
    """
    Lambda handler for the Cancer Biology Gateway.
    
    This function routes requests to the appropriate cancer biology analysis function
    based on the tool name specified in the context.
    """
    try:
        # Get the tool name from the context
        tool_name = context.client_context.custom['bedrockAgentCoreToolName']
        print(f"Tool name: {tool_name}")
        print(f"Event: {event}")
        
        # Remove any prefix from tool name if present (strip text before ___ delimiter)
        delimiter = "___"
        if delimiter in tool_name:
            tool_name = tool_name[tool_name.index(delimiter) + len(delimiter):]
        
        print(f"Processed tool name: {tool_name}")
        
        # Route to the appropriate function based on tool name
        if tool_name == 'analyze_ddr_network_in_cancer':
            result = analyze_ddr_network_in_cancer(
                expression_data_path=event.get('expression_data_path'),
                mutation_data_path=event.get('mutation_data_path'),
                output_dir=event.get('output_dir', './results')
            )
        elif tool_name == 'analyze_cell_senescence_and_apoptosis':
            result = analyze_cell_senescence_and_apoptosis(
                fcs_file_path=event.get('fcs_file_path')
            )
        elif tool_name == 'detect_and_annotate_somatic_mutations':
            result = detect_and_annotate_somatic_mutations(
                tumor_bam=event.get('tumor_bam'),
                normal_bam=event.get('normal_bam'),
                reference_genome=event.get('reference_genome'),
                output_prefix=event.get('output_prefix'),
                snpeff_database=event.get('snpeff_database', 'GRCh38.105')
            )
        elif tool_name == 'detect_and_characterize_structural_variations':
            result = detect_and_characterize_structural_variations(
                bam_file_path=event.get('bam_file_path'),
                reference_genome_path=event.get('reference_genome_path'),
                output_dir=event.get('output_dir'),
                cosmic_db_path=event.get('cosmic_db_path'),
                clinvar_db_path=event.get('clinvar_db_path')
            )
        elif tool_name == 'perform_gene_expression_nmf_analysis':
            result = perform_gene_expression_nmf_analysis(
                expression_data_path=event.get('expression_data_path'),
                n_components=event.get('n_components', 10),
                normalize=event.get('normalize', True),
                output_dir=event.get('output_dir', 'nmf_results'),
                random_state=event.get('random_state', 42)
            )
        elif tool_name == 'analyze_copy_number_purity_ploidy_and_focal_events':
            result = analyze_copy_number_purity_ploidy_and_focal_events(
                tumor_bam=event.get('tumor_bam'),
                reference_genome=event.get('reference_genome'),
                normal_bam=event.get('normal_bam'),
                output_dir=event.get('output_dir', 'cn_analysis_results'),
                targets_bed=event.get('targets_bed'),
                antitargets_bed=event.get('antitargets_bed'),
                gene_bed=event.get('gene_bed'),
                focal_genes=event.get('focal_genes'),
                log2_amp_threshold=event.get('log2_amp_threshold', 1.0),
                log2_del_threshold=event.get('log2_del_threshold', -1.0)
            )
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unknown tool: {tool_name}',
                    'available_tools': [
                        'analyze_ddr_network_in_cancer',
                        'analyze_cell_senescence_and_apoptosis',
                        'detect_and_annotate_somatic_mutations',
                        'detect_and_characterize_structural_variations',
                        'perform_gene_expression_nmf_analysis',
                        'analyze_copy_number_purity_ploidy_and_focal_events'
                    ]
                })
            }
        
        print(f"Execution completed successfully")
        print(f"Result preview: {result[:200] if isinstance(result, str) else str(result)[:200]}...")
        
        # Return successful response with research log in body
        return {
            'statusCode': 200,
            'body': result
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}',
                'tool_name': tool_name if 'tool_name' in locals() else 'unknown'
            })
        }
