import os
import argparse
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client 
from strands.tools.mcp.mcp_client import MCPClient
from strands import Agent
from mcp import stdio_client, StdioServerParameters

import logging

logging.getLogger("strands").setLevel(logging.DEBUG)

AWS_VARS = [
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
    "AWS_PROFILE", "AWS_SDK_LOAD_CONFIG",
    "AWS_WEB_IDENTITY_TOKEN_FILE", "AWS_ROLE_ARN", "AWS_ROLE_SESSION_NAME",
    "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI", "AWS_CONTAINER_CREDENTIALS_FULL_URI",
    "AWS_CONTAINER_AUTHORIZATION_TOKEN", "AWS_EC2_METADATA_DISABLED",
    "AWS_STS_REGIONAL_ENDPOINTS",
]

def create_mcp_client(neptune_endpoint: str, region) -> MCPClient:
    env = {
        "NEPTUNE_ENDPOINT": f"neptune-graph://{neptune_endpoint}",
        "AWS_DEFAULT_REGION" : region,
        "AWS_REGION" : region
    }
    for k in AWS_VARS:
        v = os.getenv(k)
        if v:
            env[k] = v
    return MCPClient(lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["awslabs.amazon-neptune-mcp-server@latest"],
            env=env,
        )
    ))

def create_omop_structure_agent(tools):
    """Create and initialize the OMOP structure agent with tools."""
    bedrockmodel = BedrockModel(
        model_id="us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        temperature=0.7
    )
    
    system_prompt = """You are an expert in the OMOP Common Data Model (CDM) and its structure. You are provided with tools to query the OMOP CDM database structure.

        ALWAYS use the available tools to:
        1. First fetch the schema to understand the correct labels and property names
        2. Query the database for specific table structures, relationships, and field information
        3. Provide accurate, tool-verified information about OMOP CDM components

        Your task is to assist users in understanding and navigating the OMOP CDM by leveraging these tools. When a user asks about tables, fields, or relationships, use the tools to retrieve current, accurate information rather than relying on general knowledge.

        If you cannot find information using the available tools, respond with "I don't know" rather than providing potentially incorrect information."""

    agent = Agent(
        model=bedrockmodel,
        system_prompt=system_prompt,
        tools=[tools],
        agent_id="omop_structure_agent",
        name="OMOP Structure Agent",
        description="An agent that helps users understand the structure of the OMOP CDM."
    )
    
    return agent

def create_initial_messages():
    """Create initial messages for the conversation."""
    return []

def main():
    """Main function to run the OMOP structure analysis tool."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="OMOP CDM Structure Analysis Tool")
    parser.add_argument(
        "--neptune-endpoint", 
        required=True, 
        help="Neptune endpoint (e.g., g-5u74xg2ma0)"
    )

    parser.add_argument(
        "--region", 
        required=True, 
        help="AWS region (e.g., us-east-1)"
    )
    
    args = parser.parse_args()
    
    # Create MCP client with provided parameters
    mcp_client = create_mcp_client(args.neptune_endpoint, args.region)
    
    # Use proper context manager - this is the Pythonic way!
    with mcp_client:
        # Get tools once inside the context
        tools = mcp_client.list_tools_sync()
        
        # Create agent with tools
        omop_structure_agent = create_omop_structure_agent(tools)
        omop_structure_agent.messages = create_initial_messages()
        
        print("\n🏥 OMOP CDM Structure Analysis Tool 🔍\n")
        print("Ask questions about OMOP Common Data Model structure, tables, relationships, and fields.")
        print("Type 'exit' to quit.\n")
        
        while True:
            query = input("\nEnter your OMOP CDM question> ").strip()
            
            if query.lower() == "exit":
                print("\nGoodbye! 👋")
                break
                
            if not query:
                print("Please enter a question about the OMOP CDM.")
                continue
                
            print("\nAnalyzing OMOP structure...\n")
            
            try:
                # Create the user message with proper format
                user_message = {
                    "role": "user",
                    "content": [{"text": query}],
                }
                
                # Add message to conversation
                omop_structure_agent.messages.append(user_message)
                
                # Get response
                response = omop_structure_agent(query)
                print(f"OMOP Analysis Results:\n{response}\n")
                
            except Exception as e:
                print(f"Error: {str(e)}\n")
                
            finally:
                # Reset conversation after each query
                omop_structure_agent.messages = create_initial_messages()

if __name__ == "__main__":
    main()