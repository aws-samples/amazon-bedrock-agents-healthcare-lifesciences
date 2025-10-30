import json
import sys
import os

# Add the current directory to the path to import literature functions
sys.path.append(os.path.dirname(__file__))

# Import all the literature query functions
from literature import (
    fetch_supplementary_info_from_doi,
    query_arxiv,
    query_scholar,
    query_pubmed,
    search_google,
    # advanced_web_search_claude,
    extract_url_content,
    extract_pdf_content
)

def lambda_handler(event, context):
    """
    AWS Lambda handler for literature research functions.
    
    Expected event structure from AgentCore Gateway:
    {
        "query": "cancer research",
        "max_papers": 10
    }
    """
    print(f"Context : {context}")
    print(f"Event: {event}")
    
    try:
        # Extract function name from context (AgentCore Gateway provides this)
        function_name = None
        if hasattr(context, 'client_context') and context.client_context and hasattr(context.client_context, 'custom'):
            tool_name = context.client_context.custom.get('bedrockAgentCoreToolName', '')
            # Extract function name from tool name (e.g., "LiteratureLambda___query_pubmed" -> "query_pubmed")
            if '___' in tool_name:
                function_name = tool_name.split('___')[1]
        
        # Fallback to event-based function name
        if not function_name:
            function_name = event.get('function_name')
        
        if not function_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing function_name in request or context'
                })
            }
        
        # Parameters come directly from event for AgentCore Gateway
        parameters = {k: v for k, v in event.items() if k != 'function_name'}
        
        # Map function names to actual functions
        function_map = {
            'fetch_supplementary_info_from_doi': fetch_supplementary_info_from_doi,
            'query_arxiv': query_arxiv,
            'query_scholar': query_scholar,
            'query_pubmed': query_pubmed,
            'search_google': search_google,
            # 'advanced_web_search_claude': advanced_web_search_claude,
            'extract_url_content': extract_url_content,
            'extract_pdf_content': extract_pdf_content
        }
        
        if function_name not in function_map:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unknown function: {function_name}',
                    'available_functions': list(function_map.keys())
                })
            }
        
        # Call the requested function with parameters
        func = function_map[function_name]
        result = func(**parameters)

        out = {
            'statusCode': 200,
            'body': json.dumps({
                'function': function_name,
                'result': result
            })
        }
        print(f"Function output: {out}")
        return out
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error executing {function_name}: {str(e)}'
            })
        }
