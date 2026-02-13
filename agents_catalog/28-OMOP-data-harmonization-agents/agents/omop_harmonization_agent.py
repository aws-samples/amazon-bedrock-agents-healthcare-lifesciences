import sys
import os
from strands import tool, Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp import stdio_client, StdioServerParameters
import logging
import argparse
import pandas as pd
from omop_structure_agent import create_omop_structure_agent, create_mcp_client
import json
from pydantic import BaseModel, Field

sys.path.append('omop-ontology')
from OMOP_ontology import OMOPOntology

global neptune_graph_id
global region
global shared_mcp_client
global shared_structure_agent

# Set root logger to INFO
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s", 
    handlers=[logging.StreamHandler()]
)

# Set strands logger to DEBUG
logging.getLogger("strands").setLevel(logging.INFO)

# Shared resources to avoid reinitialization
shared_mcp_client = None
shared_structure_agent = None

class OMOPMapping(BaseModel):
    source: str = Field(description="Source field name")
    target: str = Field(description="Target field name")
    explanation: str = Field(description="Explanation for the mapping")
    foreign_key: str = Field(description="Foreign key relationship if applicable", default="")
    foreign_key_table: str = Field(description="Foreign key table if applicable", default="")
    foreign_key_field: str = Field(description="Foreign key field if applicable", default="")

# class OMOPMappingList(BaseModel):
#     mappings: list[OMOPMapping] = Field(description="List of OMOP field mappings")

def find_embedding_based_similar_matching_fields(source, ontology):
    """
    Find similar fields based on embedding similarity.

    Args:
        source (str): The source field name.
        ontology: OMOPOntology instance
    """
    similar_nodes = ontology.find_similar_fields(source, top_k=3)
    return similar_nodes

def initialize_shared_mcp_resources():
    """Initialize shared MCP client and structure agent once."""
    global shared_mcp_client, shared_structure_agent, neptune_graph_id
    
    if shared_mcp_client is None:
        logging.info("Initializing shared MCP client...")
        shared_mcp_client = create_mcp_client(neptune_graph_id)
        
        # Initialize structure agent within MCP context
        with shared_mcp_client:
            tools = shared_mcp_client.list_tools_sync()
            shared_structure_agent = create_omop_structure_agent(tools)
        
        logging.info("Shared MCP resources initialized!")

@tool
def omop_structure_agent(query):
    """Query OMOP structure using shared MCP client to avoid reinitialization."""
    global shared_mcp_client, shared_structure_agent
    
    # Initialize shared resources if not already done
    if shared_mcp_client is None or shared_structure_agent is None:
        initialize_shared_mcp_resources()
    
    # Use shared MCP client within context
    with shared_mcp_client:
        response = shared_structure_agent(query)
        return response


def create_harmonization_synthesizer_agent():

    bedrockmodel = BedrockModel(
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        temperature=0.7
    )
    
    # system_prompt = """You are an expert in OMOP Common Data Model harmonization and field mapping. Your role is to help users map their data terms to appropriate OMOP fields using semantic similarity and embeddings.

    # You are given the potential matching target OMOP fields based on embedding similarity. Your task is to analyze these potential matches and provide the best target recommendations, including identifying foreign key relationships.

    # HARMONIZATION WORKFLOW:
    # 1. You will receive potential target OMOP fields that have been identified through embedding similarity
    # 2. Analyze these candidates considering semantic similarity scores and enriched text
    # 3. Consider the data source context when evaluating matches
    # 4. Identify foreign key relationships between fields and tables
    # 5. Provide ranked recommendations with explanations
    # 6. Include field names, table names, similarity scores, foreign key relationships, and reasoning for your selections

    # Use the given potential targets based on embeddings to provide your harmonization recommendations. If necessary, use the graph ontology provided to further refine your analysis and identify foreign key relationships."""

    system_prompt = """You are an expert in OMOP Common Data Model harmonization and field mapping. 

Your task is to analyze potential OMOP field matches (identified through embedding similarity) and provide optimal target recommendations for data mapping.

## Process:
1. Review the provided embedding-based matches for the source field
2. Analyze semantic similarity scores and field descriptions
3. Consider the source data context for better mapping accuracy
4. Identify foreign key relationships where applicable
5. Provide the best mapping recommendation

## Output Requirements:
- Provide exactly ONE best mapping recommendation per source field
- Use the structured format with all required fields
- Include foreign key information when the target field has relationships
- Provide clear reasoning for your mapping choice
- Focus on the highest similarity score and best semantic match

You will return a structured OMOPMapping object with:
- source: The original source field name
- target: The recommended OMOP field name (format: table.field)
- explanation: Clear reasoning for why this is the best mapping
- foreign_key: Description of foreign key relationship if applicable
- foreign_key_table: The table that this field references (if FK)
- foreign_key_field: The field that this field references (if FK)"""

    agent = Agent(
        model=bedrockmodel,
        system_prompt=system_prompt,
        tools=[omop_structure_agent],
        agent_id="omop_harmonization_agent",
        name="OMOP Harmonization Agent",
        description="An agent that harmonizes data terms to OMOP fields using find_embedding_based_similar_matching_fields."
    )
    
    return agent

# def harmonize_fields_to_omop(field_data: list, neptune_endpoint: str, region: str) -> list[OMOPMapping]:
#     """
#     Harmonize multiple fields to OMOP CDM and return array of OMOPMapping objects.
    
#     Args:
#         field_data: List of dicts with 'label' and 'table_description' keys
#         neptune_endpoint: Neptune graph endpoint
#         region: AWS region
        
#     Returns:
#         List of OMOPMapping objects
#     """
#     global neptune_graph_id
#     neptune_graph_id = neptune_endpoint
    
#     mappings = []
    
#     try:
#         # Initialize ontology
#         ontology = OMOPOntology(graph_id=neptune_endpoint, region_name=region)
        
#         # Create harmonization agent
#         harmonization_agent = create_harmonization_synthesizer_agent()
        
#         for field_info in field_data:
#             label = field_info['label']
#             table_description = field_info.get('table_description', '')
            
#             logging.info(f"Processing field: {label}")
            
#             # Find embedding matches
#             source = f"{label}:{table_description}" if table_description else label
#             embedding_matches = find_embedding_based_similar_matching_fields(source, ontology)
            
#             # Create harmonization request
#             harmonization_request = f"""
#             Source Field: {label}
#             Source Context: {table_description}
            
#             Embedding-based OMOP matches found:
#             {json.dumps(embedding_matches, indent=2)}
            
#             Please provide the best OMOP mapping for this source field.
#             """
            
#             try:
#                 # Get structured mapping
#                 mapping = harmonization_agent.structured_output(
#                     OMOPMapping, 
#                     harmonization_request
#                 )
#                 mappings.append(mapping)
                
#             except Exception as e:
#                 logging.error(f"Error processing field {label}: {e}")
#                 # Add error mapping
#                 error_mapping = OMOPMapping(
#                     source=label,
#                     target="unknown",
#                     explanation=f"Error processing: {str(e)}",
#                     foreign_key="",
#                     foreign_key_table="",
#                     foreign_key_field=""
#                 )
#                 mappings.append(error_mapping)
    
#     finally:
#         cleanup_shared_resources()
    
#     return mappings

def create_initial_messages():
    """Create initial messages for the conversation."""
    return []

def cleanup_shared_resources():
    """Clean up shared MCP resources."""
    global shared_mcp_client, shared_structure_agent
    
    if shared_mcp_client:
        try:
            shared_mcp_client.close()
        except:
            pass
    
    shared_mcp_client = None
    shared_structure_agent = None
    logging.info("Cleaned up shared MCP resources")

def main(file_path, neptune_endpoint, region):
    """Main function to run the OMOP harmonization tool with file input."""
    global neptune_graph_id
    
    logging.info(f"Starting OMOP harmonization with input source: {file_path}")
    logging.info(f"Neptune endpoint: {neptune_endpoint}, Region: {region}")
    
    # Set global variables for shared resources
    neptune_graph_id = neptune_endpoint
    
    try:
        # Initialize ontology with provided parameters
        ontology = OMOPOntology(graph_id=neptune_endpoint, region_name=region)
    
        df = pd.read_csv(file_path)
        logging.info(f"Loaded CSV with {len(df)} rows and {len(df.columns)} columns")
        
        harmonization_agent = create_harmonization_synthesizer_agent()
        
        # Create results file
        results_file = file_path.replace('.csv', '_harmonization_results.json')
        results = []

        for index, row in df.iterrows():
            label = row['Label']
            table_description = row['Table Description']
            
            logging.info(f"******************Processing row {index + 1}: Label='{label}', Table Description='{table_description}'")
            source = f"{label}:{table_description}"
            embedding_based_matching_nodes = find_embedding_based_similar_matching_fields(source, ontology)
            # print("------------------------------------------")
            # print(embedding_based_matching_nodes)
            # print("------------------------------------------")
            
            # Create harmonization request
            harmonization_request = f"""
            Source Field: {label}
            Source Context: {table_description}
            
            Embedding-based OMOP matches found:
            {json.dumps(embedding_based_matching_nodes, indent=2)}
            
            Please provide the best OMOP mapping for this source field.
            """
            
            try:
                # Use structured output to get OMOPMapping object
                mapping_response = harmonization_agent.structured_output(
                    OMOPMapping, 
                    harmonization_request
                )
                
                print("------------------------------------------")
                print(f"Structured mapping for '{label}':")
                print(f"Source: {mapping_response.source}")
                print(f"Target: {mapping_response.target}")
                print(f"Explanation: {mapping_response.explanation}")
                if mapping_response.foreign_key:
                    print(f"Foreign Key: {mapping_response.foreign_key}")
                print("------------------------------------------")
                
                # Convert to dict for JSON serialization
                harmonization_json = mapping_response.model_dump()
                
            except Exception as e:
                logging.error(f"Error getting structured output for row {index + 1}: {e}")
                # Fallback to create a basic mapping
                harmonization_json = {
                    "source": label,
                    "target": "unknown",
                    "explanation": f"Error processing: {str(e)}",
                    "foreign_key": "",
                    "foreign_key_table": "",
                    "foreign_key_field": ""
                }
            
            #break
            # Write result to file
            result_entry = {
                'row_index': index + 1,
                'input_label': label,
                'input_table_description': table_description,
                'source': source,
                'embedding_matches': embedding_based_matching_nodes,
                'harmonization_response': harmonization_json
            }
            results.append(result_entry)
            logging.info(f"Completed processing row {index + 1}")
            #break
    
        # Write all results to file
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logging.info(f"Results written to {results_file}")
    
    except Exception as e:
        logging.error(f"Error during harmonization: {str(e)}")
        raise
    finally:
        cleanup_shared_resources()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='OMOP Harmonization Agent')
    parser.add_argument('--input-source', required=True, help='Input source file path')
    parser.add_argument('--neptune-endpoint', required=True, help='Neptune graph endpoint ID')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    args = parser.parse_args()

    main(args.input_source, args.neptune_endpoint, args.region)

