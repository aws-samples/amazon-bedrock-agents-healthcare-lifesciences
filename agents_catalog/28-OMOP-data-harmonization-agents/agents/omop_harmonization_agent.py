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

    system_prompt = """

    # OMOP Common Data Model Harmonization Expert

## Task Overview
You are an expert in OMOP Common Data Model harmonization and field mapping. Your task is to analyze potential OMOP field matches (identified through embedding similarity) and provide optimal target recommendations for data mapping, including foreign key relationships based on the OMOP schema.

## Input Information
<input>
- Source data term(s) requiring mapping
- Potential target OMOP fields with embedding similarity scores
</input>

## Harmonization Process
Follow this structured approach:

1. **Review Potential Matches**: Carefully examine the provided potential OMOP field matches that were identified through embedding similarity.

2. **Analyze Semantic Similarity**: 
   - Evaluate the semantic relationship between source terms and potential OMOP targets
   - Consider both similarity scores and enriched text descriptions
   - Assess conceptual alignment beyond just lexical similarity

3. **Consider Context**: Factor in the data source context to determine the most appropriate mapping.

## Output Format
For each source term, provide your recommendations in this json format:

<jsonoutput>

{
    Recommendation : {
        SourceField : [field_name],
        OMOPField : [field_name],
        OMOPTable: [table_name],
        SimilarityScore: [score],
        ForeignKeyRelationships: [relationships if any],
        Reasoning: [brief explanation]
    }
}
</jsonoutput>

Provide your harmonization recommendation json based solely on the embedding similarity results and available ontology information. Focus on identifying the most semantically and structurally appropriate OMOP fields for the given source terms.
Return only the structured json without additional explanations or commentary.

    """

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
            
            
            matching_response = harmonization_agent(f"Omop target embeddings based matchings for source column in {label} in source table {table_description} are is below json format {json.dumps(embedding_based_matching_nodes)}")
            
            # Extract text content if it's an AgentResult object
            if hasattr(matching_response, 'content'):
                harmonization_text = matching_response.content
            elif hasattr(matching_response, 'text'):
                harmonization_text = matching_response.text
            else:
                harmonization_text = str(matching_response)
            
            print("------------------------------------------")
            print(f"Raw response: {harmonization_text}")
            print("------------------------------------------")
            
            # Parse JSON response with error handling
            try:
                if harmonization_text and harmonization_text.strip():
                    # Try to parse as JSON
                    harmonization_json = json.loads(harmonization_text)
                else:
                    logging.warning(f"Empty response for row {index + 1}, using raw text")
                    harmonization_json = {"error": "Empty response", "raw_text": harmonization_text}
            except json.JSONDecodeError as e:
                logging.warning(f"JSON decode error for row {index + 1}: {e}")
                logging.warning(f"Raw text: {harmonization_text}")
                # Store as raw text if JSON parsing fails
                harmonization_json = {"error": "JSON decode failed", "raw_text": harmonization_text}
            
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

