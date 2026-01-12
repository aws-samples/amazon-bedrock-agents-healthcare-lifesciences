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
        # Pure HTTP forwarding - Bridge Container handles all MCP logic
        response = http.request(
            'POST',
            f"{MCP_ENDPOINT}/mcp",
            body=json.dumps(event),
            headers={'Content-Type': 'application/json'},
            timeout=30.0
        )
        
        result = json.loads(response.data.decode('utf-8'))
        logger.info(f"Bridge response: {response.status}")
        return result
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": event.get('id')
        }
