import json
import urllib3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()
MCP_ENDPOINT = os.environ.get('MCP_ENDPOINT', 'http://bridge.sila2.local:8080')

def lambda_handler(event, context):
    # Extract tool name from client_context (Gateway passes it here)
    tool_name = None
    if hasattr(context, 'client_context') and context.client_context:
        custom = context.client_context.custom
        if custom and 'bedrockAgentCoreToolName' in custom:
            tool_name = custom['bedrockAgentCoreToolName']
            # Remove prefix if present (e.g., "sila2-bridge-container___get_temperature" -> "get_temperature")
            if '___' in tool_name:
                tool_name = tool_name.split('___', 1)[1]
    
    # If no tool name found, default to list_devices for empty event
    if not tool_name:
        if not event or len(event) == 0:
            tool_name = "list_devices"
        else:
            logger.error("No tool name found in client_context")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Tool name not found in request"},
                "id": 1
            }
    
    try:
        # Build proper MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": event if event else {}
            },
            "id": 1
        }
        
        # Forward to Bridge Container MCP endpoint
        response = http.request(
            'POST',
            MCP_ENDPOINT,
            body=json.dumps(mcp_request),
            headers={'Content-Type': 'application/json'},
            timeout=30.0
        )
        
        result = json.loads(response.data.decode('utf-8'))
        return result
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": event.get('id')
        }
