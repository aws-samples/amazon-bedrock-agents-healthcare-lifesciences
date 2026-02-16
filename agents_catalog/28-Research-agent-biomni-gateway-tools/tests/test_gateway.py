#!/usr/bin/python

import click
import time
import json
import sys
import os
import boto3
import requests
from strands.tools.mcp import MCPClient, MCPAgentTool
from mcp.types import Tool as MCPTool
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.utils import get_ssm_parameter

# Predefined prompts for testing
PROMPTS = [
    "Find information about human insulin protein",
    "Find protein structures for insulin", 
    "Find metabolic pathways related to insulin",
    "Find protein domains in insulin",
    "Find genetic variants in BRCA1 gene",
    "Find drug targets for diabetes",
    "Find insulin signaling pathways",
    "Give me alphafold structure predictions for human insulin"
]

TOOL_SPECIFIC_PROMPTS = [
    # Protein and Structure Databases
    "Use uniprot tool to find information about human insulin protein",
    "Use alphafold tool for structure predictions for uniprot_id P01308",
    "Use interpro tool to find protein domains in insulin",
    "Use pdb tool to find protein structures for insulin",
    "Use pdb_identifiers tool to lookup entry information for PDB ID 1ZNI",
    "Use stringdb tool to find protein interactions for insulin",
    "Use emdb tool to find electron microscopy structures of ribosomes",
    "Use pride tool to find proteomics data for breast cancer",
    
    # Pathway and Functional Databases
    "Use reactome tool to find insulin signaling pathways",
    "Use jaspar tool to find transcription factor binding sites for p53",
    
    # Genetic Variation and Clinical Databases
    "Use clinvar tool to find pathogenic variants in BRCA1 gene",
    "Use dbsnp tool to find common SNPs in APOE gene",
    "Use gnomad tool to find population frequencies for BRCA2 variants",
    "Use gwas_catalog tool to find GWAS associations for diabetes",
    "Use regulomedb tool to find regulatory information for rs123456",
    "Use monarch tool to find phenotype associations for BRCA1",
    
    # Genomic and Expression Databases
    "Use ensembl tool to find gene information for BRCA2",
    "Use ucsc tool to find genomic coordinates for TP53 gene",
    "Use geo tool to find RNA-seq datasets for cancer",
    
    # Drug and Clinical Trial Databases
    "Use opentarget tool to find drug targets for diabetes",
    "Use openfda tool to find adverse events for aspirin",
    "Use clinicaltrials tool to find clinical trials for Alzheimer disease",
    "Use gtopdb tool to find GPCR targets and ligands",
    
    # Cancer and Disease Databases
    "Use cbioportal tool to find mutations in TCGA breast cancer",
    "Use synapse tool to find drug screening datasets",
    
    # Model Organism and Biodiversity Databases
    "Use mpd tool to find mouse strain phenotype data for diabetes",
    "Use worms tool to find marine species classification",
    "Use paleobiology tool to find fossil records of dinosaurs",
]

MAX_TOOLS=5

def get_gateway_access_token():
    """Get M2M bearer token for gateway authentication."""
    try:
        # Get credentials from SSM
        machine_client_id = get_ssm_parameter("/app/researchapp/agentcore/machine_client_id")
        machine_client_secret = get_ssm_parameter("/app/researchapp/agentcore/cognito_secret")
        cognito_domain = get_ssm_parameter("/app/researchapp/agentcore/cognito_domain")
        user_pool_id = get_ssm_parameter("/app/researchapp/agentcore/userpool_id")

        # Clean the domain
        cognito_domain = cognito_domain.strip()
        if cognito_domain.startswith("https://"):
            cognito_domain = cognito_domain[8:]

        # Get resource server scopes
        cognito_client = boto3.client('cognito-idp')
        response = cognito_client.list_resource_servers(UserPoolId=user_pool_id, MaxResults=1)
        
        if response['ResourceServers']:
            resource_server_id = response['ResourceServers'][0]['Identifier']
            scopes = f"{resource_server_id}/read"
        else:
            scopes = "gateway:read gateway:write"

        # M2M OAuth flow
        token_url = f"https://{cognito_domain}/oauth2/token"
        token_data = {
            "grant_type": "client_credentials",
            "client_id": machine_client_id,
            "client_secret": machine_client_secret,
            "scope": scopes
        }
        
        response = requests.post(
            token_url, 
            data=token_data, 
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            print(f"Failed to get access token: {response.text}")
            return None
            
        access_token = response.json()["access_token"]
        return access_token
        
    except Exception as e:
        print(f"Error getting M2M bearer token: {str(e)}")
        return None

def tool_search(gateway_endpoint, jwt_token, query, max_tools=5):
    """Search for tools using the gateway's semantic search."""
    tool_params = {
        "name": "x_amz_bedrock_agentcore_search",
        "arguments": {"query": query},
    }
    
    request_body = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": tool_params,
    }
    
    response = requests.post(
        gateway_endpoint,
        json=request_body,
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        },
    )
    
    if response.status_code == 200:
        tool_resp = response.json()
        tools = tool_resp["result"]["structuredContent"]["tools"]
        tools = tools[:max_tools]
        return tools
    else:
        print(f"Search failed: {response.text}")
        return []

def get_all_mcp_tools_from_mcp_client(client):
    """Get all tools from MCP client with pagination."""
    more_tools = True
    tools = []
    pagination_token = None
    while more_tools:
        tmp_tools = client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(tmp_tools)
        if tmp_tools.pagination_token is None:
            more_tools = False
        else:
            more_tools = True
            pagination_token = tmp_tools.pagination_token
    return tools

def tools_to_strands_mcp_tools(tools, top_n, client):
    """Convert search results to Strands MCPAgentTool objects."""
    strands_mcp_tools = []
    for tool in tools[:top_n]:
        mcp_tool = MCPTool(
            name=tool["name"],
            description=tool["description"],
            inputSchema=tool["inputSchema"],
        )
        strands_mcp_tools.append(MCPAgentTool(mcp_tool, client))
    return strands_mcp_tools

@click.command()
@click.option("--prompt", "-p", help="Prompt to send to the agent")
@click.option("--use-search", is_flag=True, help="Use semantic search to find relevant tools")
@click.option("--search-query", help="Search query for finding relevant tools (defaults to prompt)")
@click.option("--max-tools", default=5, help="Maximum number of tools to use from search results")
@click.option("--test-prompts", is_flag=True, help="Test with predefined prompts")
@click.option("--test-tool-prompts", is_flag=True, help="Test with tool-specific prompts")
def main(prompt, use_search, search_query, max_tools, test_prompts, test_tool_prompts):
    """Test the gateway with semantic search capabilities."""
    
    # Get gateway access token
    jwt_token = get_gateway_access_token()
    if not jwt_token:
        print("❌ Failed to get gateway access token")
        return
    
    # Get gateway endpoint
    gateway_endpoint = get_ssm_parameter("/app/researchapp/agentcore/gateway_url")
    print(f"Gateway Endpoint - MCP URL: {gateway_endpoint}")
    
    # Create MCP client
    client = MCPClient(
        lambda: streamablehttp_client(
            gateway_endpoint, headers={"Authorization": f"Bearer {jwt_token}"}
        )
    )
    
    # Create Bedrock model
    model = BedrockModel(
        model_id="global.anthropic.claude-sonnet-4-20250514-v1:0",
        temperature=0.7,
        streaming=True,
    )
    
    with client:
        # Determine which prompts to use
        prompts_to_test = []
        if test_prompts:
            prompts_to_test = PROMPTS
        elif test_tool_prompts:
            prompts_to_test = TOOL_SPECIFIC_PROMPTS
        elif prompt:
            prompts_to_test = [prompt]
        else:
            print("❌ Please provide a prompt or use --test-prompts or --test-tool-prompts")
            return    
        
        # Process each prompt
        for i, test_prompt in enumerate(prompts_to_test, 1):
            print(f"\n{'='*60}")
            print(f"Testing prompt {i}/{len(prompts_to_test)}")
            print(f"💬 Prompt: {test_prompt}")
            print('='*60)
                    
            if use_search:
                # Use semantic search only
                search_query_to_use = search_query or test_prompt
                print(f"\n🔍 Searching for tools with query: '{search_query_to_use}'")
                
                start_time = time.time()
                tools_found = tool_search(gateway_endpoint, jwt_token, search_query_to_use, max_tools=MAX_TOOLS)
                search_time = time.time() - start_time
                
                if not tools_found:
                    print("❌ No tools found from search")
                    continue
                    
                print(f"✅ Found {len(tools_found)} relevant tools in {search_time:.2f}s")
                print(f"Top tool: {tools_found[0]['name']}")
                
                agent_tools = tools_to_strands_mcp_tools(tools_found, max_tools, client)
                agent = Agent(model=model, tools=agent_tools)
                
                start_time = time.time()
                
                try:
                    result = agent(test_prompt)
                    execution_time = time.time() - start_time
                    
                    print(f"\n⏱️  Total time: {execution_time + search_time:.2f}s (search: {search_time:.2f}s, execution: {execution_time:.2f}s)")
                    print(f"🎯 Response: {result.message['content'][0]['text']}")
                    
                    if hasattr(result, 'metrics') and result.metrics:
                        tokens = result.metrics.accumulated_usage.get("totalTokens", 0)
                        print(f"🔢 Total tokens used: {tokens:,}")
                        
                except Exception as e:
                    print(f"❌ Error executing agent: {str(e)}")
                    
            else:
                # Use all tools (traditional approach)
                print("📋 Getting all available tools...")
                start_time = time.time()
                all_tools = get_all_mcp_tools_from_mcp_client(client)
                list_time = time.time() - start_time
                print(f"✅ Found {len(all_tools)} total tools in {list_time:.2f}s\n")

                agent = Agent(model=model, tools=all_tools)
                
                start_time = time.time()
                
                try:
                    result = agent(test_prompt)
                    execution_time = time.time() - start_time
                    
                    print(f"\n⏱️  Execution time: {execution_time:.2f}s")
                    print(f"🎯 Response: {result.message['content'][0]['text']}")
                    
                    if hasattr(result, 'metrics') and result.metrics:
                        tokens = result.metrics.accumulated_usage.get("totalTokens", 0)
                        print(f"🔢 Total tokens used: {tokens:,}")
                        
                except Exception as e:
                    print(f"❌ Error executing agent: {str(e)}")

if __name__ == "__main__":
    main()
