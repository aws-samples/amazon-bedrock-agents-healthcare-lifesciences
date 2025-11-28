import json
import urllib3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

http = urllib3.PoolManager()
MCP_ENDPOINT = os.environ.get('MCP_ENDPOINT', 'http://bridge.sila2.local:8080')

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # AgentCore Gateway sends tool calls in different formats
        # Format 1: {"name": "tool_name", "arguments": {...}}
        # Format 2: {"method": "tools/call", "params": {"name": "tool_name", "arguments": {...}}}
        # Format 3: Empty {} or tool arguments directly
        
        tool_name = event.get('name', '')
        arguments = event.get('arguments', event if event else {})
        
        # Remove Gateway prefix if present
        if tool_name and '___' in tool_name:
            tool_name = tool_name.split('___', 1)[1]
        
        # Determine method based on tool_name or event content
        if not tool_name:
            # Empty event or arguments only - assume list_devices
            method = "tools/call"
            params = {"name": "list_devices", "arguments": arguments}
        else:
            method = "tools/call"
            params = {"name": tool_name, "arguments": arguments}
        
        # Build JSON-RPC request for Bridge Container
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": event.get('id', 1)
        }
        
        logger.info(f"Forwarding to Bridge: {json.dumps(jsonrpc_request)}")
        
        response = http.request(
            'POST',
            f"{MCP_ENDPOINT}/mcp",
            body=json.dumps(jsonrpc_request),
            headers={'Content-Type': 'application/json'},
            timeout=30.0
        )
        
        logger.info(f"Bridge response status: {response.status}")
        result = json.loads(response.data.decode('utf-8'))
        logger.info(f"Bridge response: {json.dumps(result)[:200]}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": event.get('id')
        }
