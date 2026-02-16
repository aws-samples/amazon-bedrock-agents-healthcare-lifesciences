#!/usr/bin/env python3

import sys
import os
import json
from unittest.mock import Mock

# Add the lambda function path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../prerequisite/lambda-literature/python"))

from lambda_function import lambda_handler

def test_lambda_function():
    """Test the literature lambda function with a mock context"""
    
    # Create mock context similar to the one in the error
    mock_context = Mock()
    mock_context.aws_request_id = "5f16b0bc-e18e-4355-a488-b38bcb0479d7"
    mock_context.log_group_name = "/aws/lambda/researchappStackInfra-LiteratureLambda-2KIJkHAU1v6c"
    mock_context.function_name = "researchappStackInfra-LiteratureLambda-2KIJkHAU1v6c"
    
    # Mock client_context
    mock_client_context = Mock()
    mock_client_context.custom = {
        'bedrockAgentCoreTargetId': 'RAM62IHPVL',
        'bedrockAgentCoreGatewayId': 'researchapp-gw-ws6ooojp8n',
        'bedrockAgentCoreToolName': 'LiteratureLambda___query_pubmed'
    }
    mock_context.client_context = mock_client_context
    
    # Test event from user
    event = {
        'query': 'trastuzumab resistance mechanisms HER2 breast cancer',
        'max_papers': 15
    }
    
    print("Testing literature lambda function...")
    print(f"Event: {event}")
    
    try:
        result = lambda_handler(event, mock_context)
        print(f"Result: {json.dumps(result, indent=2)}")
        return result
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_lambda_function()
