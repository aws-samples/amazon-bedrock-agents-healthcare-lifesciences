import json
import logging
import os
import urllib.parse
import urllib.request

from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

SYSTEM_PROMPT = """You are a research assistant specializing in web-based information retrieval. Your task:

1. Analyze queries precisely
2. Search for authoritative, current sources
3. Deliver concise, factual responses
4. Include source citations

Guidelines:
- Communicate with clarity and precision
- Evaluate source reliability
- Focus on recent, relevant data
- Decompose complex questions
- Document search methodology
- Request query refinement when needed

Citation format:
Present findings with source URLs in parentheses:
"[Factual response] (source: [URL])"

For example, if the user asks:

"who built the tower of london?"

And you find the answer at this url:

"https://en.wikipedia.org//w/index.php?title=Tower_of_London"

A good response is:

"William the Conqueror built the tower of london in 1078 (source: https://en.wikipedia.org//w/index.php?title=Tower_of_London)"
"""


@tool
def web_search(
    search_query: str,
    target_website: str = "",
    topic: str = "general",
    days: int = 30,
) -> str:
    """Execute an internet search query using Tavily Search.

    Args:
        search_query: The search query to execute with Tavily. Example: 'Who is Leo Messi?'
        target_website: The specific website to search including its domain name. If not provided, the most relevant website will be used.
        topic: The topic being searched. 'news' or 'general'. Helps narrow the search when news is the focus.
        days: The number of days of history to search. Helps when looking for recent events or news.
    """
    api_key = TAVILY_API_KEY
    if not api_key:
        return "Error: TAVILY_API_KEY environment variable is not set."

    logger.info(f"Executing Tavily search: {urllib.parse.quote(search_query)}")

    payload = {
        "api_key": api_key,
        "query": search_query,
        "search_depth": "advanced",
        "include_images": False,
        "include_answer": False,
        "include_raw_content": False,
        "max_results": 3,
        "topic": topic,
        "days": days,
        "include_domains": [target_website] if target_website else [],
        "exclude_domains": [],
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.tavily.com/search",
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    try:
        response = urllib.request.urlopen(request, timeout=25)  # nosec: B310
        return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return f"Error: Tavily search failed with HTTP {e.code}"
    except Exception as e:
        return f"Error: Tavily search failed: {e}"


def create_agent() -> Agent:
    """Create and return the Tavily web search agent."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        streaming=True,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[web_search],
    )
