#!/usr/bin/python

import asyncio
import click
from bedrock_agentcore.identity.auth import requires_access_token
from strands.tools.mcp import MCPClient,MCPAgentTool
from mcp.types import Tool as MCPTool
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
import sys
import os
import boto3
import requests
from time import sleep

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.utils import get_ssm_parameter

gateway_access_token = None


@requires_access_token(
    provider_name=get_ssm_parameter("/app/researchapp/agentcore/cognito_provider"),
    scopes=[],  # Optional unless required
    auth_flow="M2M",
)
async def _get_access_token_manually(*, access_token: str):
    
    global gateway_access_token
    gateway_access_token = access_token
    
    return access_token

async def get_gateway_access_token():
    """Get gateway access token using manual M2M flow."""
    try:
        # Get dentials from SSM
        machine_client_id = get_ssm_parameter("/app/researchapp/agentcore/machine_client_id")
        machine_client_secret = get_ssm_parameter("/app/researchapp/agentcore/cognito_secret")
        cognito_domain = get_ssm_parameter("/app/researchapp/agentcore/cognito_domain")
        user_pool_id = get_ssm_parameter("/app/researchapp/agentcore/userpool_id")
        #print(user_pool_id)

        # Remove https:// if it's already in the domain
        # Clean the domain properly
        cognito_domain = cognito_domain.strip()
        if cognito_domain.startswith("https://"):
            cognito_domain = cognito_domain[8:]  # Remove "https://"
        #print(f"Cleaned domain: {repr(cognito_domain)}")
        token_url = f"https://{cognito_domain}/oauth2/token"
        #print(f"Token URL: {token_url}")  # Debug print
        # nosemgrep sleep to wait for resources
        sleep(2)
        #print(f"Token URL: {repr(token_url)}")
        
        # Test URL 
        from urllib.parse import urlparse
        parsed = urlparse(token_url)
        #print(f"Parsed - scheme: {parsed.scheme}, netloc: {parsed.netloc}")
        
        # Get resource server ID from machine client configuration
        try:
            cognito_client = boto3.client('cognito-idp')
            
            
            # List resource servers to find the ID
            response = cognito_client.list_resource_servers(UserPoolId=user_pool_id,MaxResults=1)
            print(response)
            if response['ResourceServers']:
                resource_server_id = response['ResourceServers'][0]['Identifier']
                #print(resource_server_id)
                scopes = f"{resource_server_id}/read"
            else:
                scopes = "gateway:read gateway:write"
        except Exception as e:
            raise Exception(f"Error getting scopes: {str(e)}")

        #print("Scope")
        #print(scopes)
        # Perform M2M OAuth flow
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
            raise Exception(f"Failed to get access token: {response.text}")
        global gateway_access_token
        access_token=response.json()["access_token"]
        gateway_access_token = access_token
        #print(f"Gateway Access Token: {access_token}")    
        return access_token     
        
    except Exception as e:
        raise Exception(f"Error getting gateway access token: {str(e)}")

def tools_to_strands_mcp_tools(client, tools, top_n):
    strands_mcp_tools = []
    for tool in tools[:top_n]:
        mcp_tool = MCPTool(
            name=tool["name"],
            description=tool["description"],
            inputSchema=tool["inputSchema"],
        )
        strands_mcp_tools.append(MCPAgentTool(mcp_tool, client))
    return strands_mcp_tools

def tool_search(gateway_endpoint, jwt_token, query):
    toolParams = {
        "name": "x_amz_bedrock_agentcore_search",
        "arguments": {"query": query},
    }
    toolResp = invoke_gateway_tool(
        gateway_endpoint=gateway_endpoint, jwt_token=jwt_token, tool_params=toolParams
    )
    tools = toolResp["result"]["structuredContent"]["tools"]
    return tools

def invoke_gateway_tool(gateway_endpoint, jwt_token, tool_params):
    # print(f"Invoking tool {tool_params['name']}")

    requestBody = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": tool_params,
    }
    response = requests.post(
        gateway_endpoint,
        json=requestBody,
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        },
    )

    return response.json()


@click.command()
@click.option("--prompt", "-p", required=True, help="Prompt to send to the MCP agent")
def main(prompt: str):
    """CLI tool to interact with an MCP Agent using a prompt."""

    # Fetch access token
    #asyncio.run(_get_access_token_manually(access_token=""))
    asyncio.run(get_gateway_access_token())
    # Load gateway configuration from SSM parameters
    try:
        gateway_url = get_ssm_parameter("/app/researchapp/agentcore/gateway_url")
    except Exception as e:
        print(f"❌ Error reading gateway URL from SSM: {str(e)}")
        sys.exit(1)

    print(f"Gateway Endpoint - MCP URL: {gateway_url}")

    prompts = [
        "Find information about human insulin protein",
        "Find protein structures for insulin", 
        "Find metabolic pathways related to insulin",
        "Find protein domains in insulin",
        "Find genetic variants in BRCA1 gene",
        "Find drug targets for diabetes",
        "Find insulin signaling pathways",
        "Give me alphafold structure predictions for human insulin"
            ] 
    tool_specific_prompts = [
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
    "Use kegg tool to find metabolic pathways related to insulin",
    "Use reactome tool to find insulin signaling pathways",
    "Use jaspar tool to find transcription factor binding sites for p53",
    "Use remap tool to find CTCF binding sites in human genome",
    
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
    "Use iucn tool to find conservation status of polar bears (requires API token)",
    "Use worms tool to find marine species classification",
    "Use paleobiology tool to find fossil records of dinosaurs",
    
        ]
    
    
    # Set up MCP client
    client = MCPClient(
        lambda: streamablehttp_client(
            gateway_url,
            headers={"Authorization": f"Bearer {gateway_access_token}"},
        )
    )

    with client:
        
        agent1 = Agent(tools=client.list_tools_sync()) #agent that includes all the tools 
        print(prompt)
        response = agent1(prompt)
        print("Agent 1 response without semantic search")
        print(str(response))
        for prompt in prompts:
            print(prompt)
            response = agent1(prompt)
            print("Agent 1 response without semantic search")
            print(str(response))
            tools_found = tool_search(
            gateway_endpoint=gateway_url,
            jwt_token=gateway_access_token,
            query=prompt,
            )
            print("Agent 2 response with semantic search with top 3 tools")
            print('total tools found')
            print(tools_found)
            agent2 = Agent(tools=tools_to_strands_mcp_tools(client,tools_found, 3)) #agent that uses gateway search to filter tools 
            response = agent2(prompt)
            print(str(response))     
            


if __name__ == "__main__":
    main()