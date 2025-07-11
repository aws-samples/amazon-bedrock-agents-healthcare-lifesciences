from typing import Any, Dict
import read_pubmed
import search_pubmed
from strands import Agent


# Define a system prompt
SYSTEM_PROMPT = """You are a life science research assistant. When given a scientific question, follow this process:

1. Use the search_pubmed tool with rerank="referenced_by", max_results to 200-500, and max_records to 20-50 to find highly-cited papers. Search broadly first, then narrow down. Use temporal filters like "last 5 years"[dp] for recent work. 
2. Use read_pubmed on the 1-2 most relevant articles from your search results to gain a better understanding of the space. Focus on highly-cited papers and reviews.
3. Extract and summarize the most relevant clinical findings.
3. Return structured, well-cited information with PMID references.

Key guidelines:
- Always use rerank="referenced_by" in searches to prioritize influential papers.
- Limit searches to 20-50 articles for focused analysis.
- Select articles strategically based on citation count and relevance.
"""


# The handler function signature `def handler(event, context)` is what Lambda
# looks for when invoking your function.
def handler(event: Dict[str, Any], _context) -> str:
    agent = Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[search_pubmed, read_pubmed],
    )

    response = agent(event.get("prompt"))
    return str(response)
