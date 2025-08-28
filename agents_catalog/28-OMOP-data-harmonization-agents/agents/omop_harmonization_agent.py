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

sys.path.append('omop-ontology')
from OMOP_ontology import OMOPOntology

global neptune_graph_id

# Set root logger to INFO
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s", 
    handlers=[logging.StreamHandler()]
)

# Set strands logger to DEBUG
logging.getLogger("strands").setLevel(logging.DEBUG)

# ontology will be initialized in main() with argparse parameters

def find_embedding_based_similar_matching_fields(source, ontology):
    """
    Find similar fields based on embedding similarity.

    Args:
        source (str): The source field name.
        ontology: OMOPOntology instance
    """
    similar_nodes = ontology.find_similar_fields(source, top_k=3)
    return similar_nodes

@tool
def omop_structure_agent(query):
    mcp_client = create_mcp_client(neptune_graph_id)
    
    with mcp_client:
        tools = mcp_client.list_tools_sync()
        omop_structure_agent = create_omop_structure_agent(tools)
        response = omop_structure_agent(query)

        return response


def create_harmonization_synthesizer_agent():

    bedrockmodel = BedrockModel(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        temperature=0.3
    )
    
    system_prompt = """You are an expert in OMOP Common Data Model harmonization and field mapping. Your role is to help users map their data terms to appropriate OMOP fields using semantic similarity and embeddings.

    You are given the matching target OMOP fields based on embedding similarity. Your task is to analyze these potential matches and provide the best harmonization recommendations, including identifying foreign key relationships.

    HARMONIZATION WORKFLOW:
    1. You will receive potential target OMOP fields that have been identified through embedding similarity
    2. Analyze these candidates considering semantic similarity scores
    3. Consider the data source context when evaluating matches
    4. Identify foreign key relationships between fields and tables
    5. Provide ranked recommendations with explanations
    6. Include field names, table names, similarity scores, foreign key relationships, and reasoning for your selections

    Use the given potential targets based on embeddings to provide your harmonization recommendations. If necessary, use the graph ontology provided to further refine your analysis and identify foreign key relationships."""

    agent = Agent(
        model=bedrockmodel,
        system_prompt=system_prompt,
        tools=[omop_structure_agent],
        agent_id="omop_harmonization_agent",
        name="OMOP Harmonization Agent",
        description="An agent that harmonizes data terms to OMOP fields using find_embedding_based_similar_matching_fields."
    )
    
    return agent

def create_initial_messages():
    """Create initial messages for the conversation."""
    return []

def main(file_path, neptune_endpoint, region):
    """Main function to run the OMOP harmonization tool with file input."""
    import json
    
    logging.info(f"Starting OMOP harmonization with input source: {file_path}")
    logging.info(f"Neptune endpoint: {neptune_endpoint}, Region: {region}")
    
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
        print(embedding_based_matching_nodes)
        
        
        matching_response = harmonization_agent(f"Embeddings based matchings for {source} : {embedding_based_matching_nodes}")
        break
        # Write result to file
        result_entry = {
            'row_index': index + 1,
            'input_label': label,
            'input_table_description': table_description,
            'source': source,
            'embedding_matches': embedding_based_matching_nodes,
            'harmonization_response': matching_response
        }
        results.append(result_entry)
        
        logging.info(f"Completed processing row {index + 1}")
    
    # Write all results to file
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logging.info(f"Results written to {results_file}")
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='OMOP Harmonization Agent')
    parser.add_argument('--input-source', required=True, help='Input source file path')
    parser.add_argument('--neptune-endpoint', required=True, help='Neptune graph endpoint ID')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    args = parser.parse_args()

    neptune_graph_id = args.neptune_endpoint
    main(args.input_source, args.neptune_endpoint, args.region)

