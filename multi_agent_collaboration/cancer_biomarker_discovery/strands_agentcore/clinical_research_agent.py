
import os
import boto3
import json
import uuid
import requests
from typing import Dict, Any, List
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import retrieve

from utils.PubMed import PubMed

# Initialize KB tool variable
kb_tool = None

# Get AWS account information
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
region = boto3.Session().region_name

# Initialize AWS clients
bedrock_client = boto3.client('bedrock-runtime', region_name=region)
bedrock_agent_client = boto3.client("bedrock-agent", region_name=region)

print(f"Region: {region}")
print(f"Account ID: {account_id}")

# Find the Knowledge Base
response = bedrock_agent_client.list_knowledge_bases()

# Iterate through knowledge bases and find needed one
ncbi_kb_id = None
for kb in response['knowledgeBaseSummaries']:
    kb_name = kb['name']
    if 'ncbiKnowledgebase' in kb_name:
        ncbi_kb_id = kb['knowledgeBaseId']
        break

if ncbi_kb_id:
    print(f"Found Knowledge Base ID: {ncbi_kb_id}")
    os.environ["KNOWLEDGE_BASE_ID"] = ncbi_kb_id
    print("Knowledge Base will be integrated using direct Strands tool approach")
else:
    print("Warning: Knowledge Base not found. Internal evidence retrieval may not work.")
    ncbi_kb_id = None

clinical_research_agent_name = "Clinical-evidence-researcher-strands"
clinical_research_agent_description = "Research internal and external evidence using Strands framework"
clinical_research_agent_instruction = """You are a medical research assistant AI specialized in summarizing internal and external 
evidence related to cancer biomarkers. Your primary task is to interpret user queries, gather internal and external 
evidence, and provide relevant medical insights based on the results. Use only the appropriate tools as required by 
the specific question. Always use the retrieve knowledge base tool first for internal evidence search. Follow these instructions carefully: 

1. Use the retrieve tool to search internal evidence. Use the query PubMed tool after you performed a search using the retrieve tool.

2. When querying PubMed: 
   a. Summarize the findings of each relevant study with citations to the specific pubmed web link of the study 
   b. The json output will include 'Link', 'Title', 'Summary'. 
   c. Always return the Title and Link (for example, 'https://pubmed.ncbi.nlm.nih.gov/') of each study in your response.  

3. For internal evidence, make use of the knowledge base to retrieve relevant information. 
   Always provide citations to specific content chunks. 

4. When providing your response: 
   a. Start with a brief summary of your understanding of the user's query. 
   b. Explain the steps you're taking to address the query. Ask for clarifications from the user if required. 
   c. Separate the responses generated from internal evidence (knowledge base) and external evidence (PubMed api).  
   d. Conclude with a concise summary of the findings and their potential implications for medical research.
"""

# Define the tools using Strands @tool decorator
@tool
def query_pubmed(query: str) -> str:
    """
    Query PubMed for relevant biomedical literature based on the user's query.
    This tool searches PubMed abstracts and returns relevant studies with titles, links, and summaries.
    
    Args:
        query (str): The search query for PubMed
    
    Returns:
        str: JSON string containing PubMed search results with titles, links, and summaries
    """
    
    pubmed = PubMed()

    print(f"\nPubMed Query: {query}\n")
    result = pubmed.run(query)
    print(f"\nPubMed Results: {result}\n")
    return result

# Create list of custom tools
clinical_research_agent_tools = [query_pubmed, retrieve]
print(f"Created {len(clinical_research_agent_tools)} custom tools for the Strands agent")

# Create Bedrock model for Strands
model = BedrockModel(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name=region,
    temperature=0.1,
    streaming=False
)
