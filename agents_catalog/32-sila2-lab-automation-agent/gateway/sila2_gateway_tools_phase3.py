"""
SiLA2 Gateway Tools for Phase 3 - Simplified version without sila2_client dependency
"""
import json
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SiLA2GatewayTools:
    """Gateway tools for SiLA2 lab automation - Phase 3 simplified version"""
    
    def __init__(self):
        # Phase 3: Mock devices without SiLA2Client dependency
        self.devices = {
            "HPLC-01": {"status": "ready", "type": "HPLC", "location": "Lab-A"},
            "CENTRIFUGE-01": {"status": "busy", "type": "Centrifuge", "location": "Lab-B"},
            "PIPETTE-01": {"status": "ready", "type": "Pipette", "location": "Lab-A"}
        }
    
    def list_available_devices(self) -> Dict[str, Any]:
        """List all available SiLA2 laboratory devices"""
        try:
            devices_list = []
            for device_id, info in self.devices.items():
                devices_list.append({
                    "device_id": device_id,
                    "type": info["type"],
                    "status": info["status"],
                    "location": info["location"]
                })
            
            return {
                "success": True,
                "devices": devices_list,
                "count": len(devices_list),
                "timestamp": datetime.now().isoformat(),
                "source": "Gateway Tools Phase 3"
            }
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return {"success": False, "error": str(e)}
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get current status of SiLA2 laboratory device"""
        try:
            if device_id not in self.devices:
                return {
                    "success": False,
                    "error": f"Device {device_id} not found",
                    "available_devices": list(self.devices.keys())
                }
            
            device = self.devices[device_id]
            return {
                "success": True,
                "device_id": device_id,
                "status": device["status"],
                "type": device["type"],
                "location": device["location"],
                "timestamp": datetime.now().isoformat(),
                "source": "Gateway Tools Phase 3"
            }
        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return {"success": False, "error": str(e)}
    
    def start_device_operation(self, device_id: str, operation: str, parameters: Dict = None) -> Dict[str, Any]:
        """Start operation on SiLA2 laboratory device"""
        try:
            if device_id not in self.devices:
                return {"success": False, "error": f"Device {device_id} not found"}
            
            if self.devices[device_id]["status"] != "ready":
                return {"success": False, "error": f"Device {device_id} is busy"}
            
            self.devices[device_id]["status"] = "running"
            return {
                "success": True,
                "device_id": device_id,
                "operation": operation,
                "parameters": parameters or {},
                "status": "started",
                "timestamp": datetime.now().isoformat(),
                "source": "Gateway Tools Phase 3"
            }
        except Exception as e:
            logger.error(f"Error starting operation: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_device_operation(self, device_id: str) -> Dict[str, Any]:
        """Stop current operation on SiLA2 device"""
        try:
            if device_id not in self.devices:
                return {"success": False, "error": f"Device {device_id} not found"}
            
            self.devices[device_id]["status"] = "ready"
            
            return {
                "success": True,
                "device_id": device_id,
                "status": "stopped",
                "timestamp": datetime.now().isoformat(),
                "source": "Gateway Tools Phase 3"
            }
        except Exception as e:
            logger.error(f"Error stopping operation: {e}")
            return {"success": False, "error": str(e)}

# Gateway Lambda handler
def lambda_handler(event, context):
    """AWS Lambda handler for Gateway tools"""
    try:
        tools = SiLA2GatewayTools()
        
        # Extract tool name and parameters from event
        tool_name = event.get('tool_name')
        parameters = event.get('parameters', {})
        
        # Route to appropriate tool method
        if tool_name == 'list_available_devices':
            result = tools.list_available_devices()
        elif tool_name == 'get_device_status':
            result = tools.get_device_status(parameters.get('device_id'))
        elif tool_name == 'start_device_operation':
            result = tools.start_device_operation(
                parameters.get('device_id'),
                parameters.get('operation'),
                parameters.get('parameters')
            )
        elif tool_name == 'stop_device_operation':
            result = tools.stop_device_operation(parameters.get('device_id'))
        else:
            result = {"success": False, "error": f"Unknown tool: {tool_name}"}
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    
    except Exception as e:
        logger.error(f"Gateway handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({"success": False, "error": str(e)})
        }