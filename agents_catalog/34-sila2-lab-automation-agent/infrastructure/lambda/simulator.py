"""
Lambda function for SiLA2 simulator.
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict

from sila2_stub.simulator.server import SiLA2Server

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize simulator
simulator = SiLA2Server(
    host="0.0.0.0",
    port=int(os.environ.get("SIMULATOR_PORT", "50052")),
)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Response
    """
    try:
        # Get request details
        http_method = event.get("requestContext", {}).get("http", {}).get("method")
        body = event.get("body", "{}")
        
        if not isinstance(body, dict):
            body = json.loads(body)
        
        # Handle request
        if http_method == "POST":
            command = body.get("command")
            parameters = body.get("parameters", {})
            
            if not command:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "Missing command parameter",
                    }),
                }
            
            # Execute command
            method = getattr(simulator, command.lower(), None)
            if not method:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": f"Unknown command: {command}",
                    }),
                }
            
            try:
                # Run command in event loop
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(method(**parameters))
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "success": True,
                        "result": result,
                    }),
                }
                
            except Exception as e:
                logger.error(f"Command execution failed: {e}")
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "error": str(e),
                    }),
                }
                
        elif http_method == "GET":
            # Get simulator status
            try:
                loop = asyncio.get_event_loop()
                state = loop.run_until_complete(simulator.get_plate_state())
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "success": True,
                        "state": state,
                    }),
                }
                
            except Exception as e:
                logger.error(f"Failed to get simulator status: {e}")
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "error": str(e),
                    }),
                }
                
        else:
            return {
                "statusCode": 405,
                "body": json.dumps({
                    "error": f"Method not allowed: {http_method}",
                }),
            }
            
    except Exception as e:
        logger.error(f"Request handling failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
            }),
        }

    finally:
        # Clean up event loop
        try:
            loop = asyncio.get_event_loop()
            loop.close()
        except:
            pass
