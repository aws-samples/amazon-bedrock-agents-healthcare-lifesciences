"""
SiLA2 Gateway Tools - AWS AgentCore Gateway integration
Based on AWS official samples
"""
import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """Lambda handler for AgentCore Gateway tools"""
    try:
        logger.info(f"Gateway request: {event}")
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        tool_name = body.get('tool_name')
        parameters = body.get('parameters', {})
        
        # Route to appropriate tool
        if tool_name == 'list_available_devices':
            result = list_available_devices()
        elif tool_name == 'get_device_status':
            result = get_device_status(parameters.get('device_id'))
        elif tool_name == 'start_device_operation':
            result = start_device_operation(
                parameters.get('device_id'),
                parameters.get('operation')
            )
        elif tool_name == 'stop_device_operation':
            result = stop_device_operation(
                parameters.get('device_id'),
                parameters.get('operation_id')
            )
        else:
            result = {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Gateway error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"success": False, "error": str(e)})
        }

def list_available_devices() -> Dict[str, Any]:
    """List all available SiLA2 devices"""
    devices = [
        {
            "device_id": "HPLC-01",
            "device_type": "HPLC",
            "status": "ready",
            "location": "Lab-A"
        },
        {
            "device_id": "CENTRIFUGE-01", 
            "device_type": "Centrifuge",
            "status": "busy",
            "location": "Lab-B"
        },
        {
            "device_id": "PIPETTE-01",
            "device_type": "Pipette",
            "status": "ready",
            "location": "Lab-A"
        }
    ]
    
    return {
        "success": True,
        "devices": devices,
        "count": len(devices)
    }

def get_device_status(device_id: str) -> Dict[str, Any]:
    """Get status of a specific device"""
    if not device_id:
        return {"success": False, "error": "device_id is required"}
    
    return {
        "success": True,
        "device_id": device_id,
        "status": "ready",
        "temperature": "25.0°C"
    }

def start_device_operation(device_id: str, operation: str) -> Dict[str, Any]:
    """Start an operation on a device"""
    if not device_id:
        return {"success": False, "error": "device_id is required"}
    
    return {
        "success": True,
        "device_id": device_id,
        "operation": operation or "default_analysis",
        "status": "started",
        "operation_id": f"OP-{device_id}-001"
    }

def stop_device_operation(device_id: str, operation_id: str) -> Dict[str, Any]:
    """Stop an operation on a device"""
    if not device_id or not operation_id:
        return {"success": False, "error": "device_id and operation_id are required"}
    
    return {
        "success": True,
        "device_id": device_id,
        "operation_id": operation_id,
        "status": "stopped"
    }