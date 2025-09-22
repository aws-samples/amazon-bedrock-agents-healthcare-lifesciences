"""
Sample tools for the AgentCore Strands Template.
These are basic tools that can be used as examples or starting points.
"""

from typing import Dict, Any
import json
from strands import tool
from agent.agent_config.tools.PubMed import PubMed

@tool(
    name="Query_pubmed",
    description="Query PubMed for relevant biomedical literature based on the user's query.This tool searches PubMed abstracts and returns relevant studies with titles, links, and summaries.",
)
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

# List of available tools for easy import
SAMPLE_TOOLS = [
    query_pubmed
]
