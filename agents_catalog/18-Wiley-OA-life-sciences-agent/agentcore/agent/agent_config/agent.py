import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

WILEY_ONLINE_LIBRARY = "https://51xu00806d.execute-api.us-east-1.amazonaws.com/api?question="

SYSTEM_PROMPT = """You are a highly knowledgeable and friendly AI assistant designed to assist users with accurate and detailed information.
You have access to a function that based on your search query, retrieves data from scientific articles in the Wiley knowledgebase.
When responding to user queries, follow these guidelines:

1. **Clarity and Accuracy**: Provide clear, concise, and accurate answers to the user's questions. Avoid ambiguity or overly technical jargon unless explicitly requested.

2. **Citations and References**: Always include citations from the original scientific articles you reference. Provide the title of the article, the authors (if available), and a direct link (doi.org) to the source.

3. **Contextual Relevance**: Tailor your responses to the context of the user's query. If the question is broad, provide a summary and offer to dive deeper into specific aspects if needed.

4. **Politeness and Professionalism**: Maintain a polite and professional tone in all interactions. Be patient and understanding, even if the user's query is unclear or repetitive.

5. **Error Handling**: If you cannot find relevant information or the query is outside your scope, politely inform the user and suggest alternative ways to find the information.

6. **Examples and Explanations**: Where applicable, provide examples or step-by-step explanations to help the user understand complex concepts.

7. **Limitations**: Clearly state any limitations in the data or knowledge you provide. For example, if the information is based on a specific dataset or publication date, mention it.

Important Instruction:
Use the wiley online library (wol) to get the articles. It will return high quality article excerpts based on the query.
Make sure to add the hyperlink to the https://doi.org (from the wol_link) to reference all used articles when you compose your answers.
It is imperative to include the doi.org hyperlinks in your final response.
"""


@tool
def wiley_search(question: str) -> str:
    """Execute a search query against the Wiley Open Access life sciences library to retrieve relevant scientific article excerpts.

    Args:
        question: The search query to execute with Wiley. Example: 'How to handle uncertain deaths?'
    """
    if not question or not question.strip():
        return "Error: Query parameter 'question' is required."

    try:
        encoded_question = urllib.parse.quote(question.strip())
        req = urllib.request.Request(WILEY_ONLINE_LIBRARY + encoded_question)
        with urllib.request.urlopen(req, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            data = response.read().decode(charset)
            json_data = json.loads(data)
            return json.dumps(json_data, indent=2) if isinstance(json_data, (dict, list)) else str(json_data)
    except urllib.error.URLError as e:
        return f"Error: Request to Wiley API failed: {e.reason}"
    except json.JSONDecodeError:
        return "Error: Failed to parse JSON response from Wiley API."
    except Exception as e:
        return f"Error: Unexpected failure querying Wiley API: {e}"


def create_agent() -> Agent:
    """Create and return the Wiley OA life sciences search agent."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        streaming=True,
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[wiley_search],
    )
