"""
SiLA2 Gateway Tools for AgentCore Gateway
Phase 3: SiLA2プロトコル統合版
"""
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from sila2_client import SiLA2Client

logger = logging.getLogger(__name__)

class SiLA2GatewayTools:
    """Gateway tools for SiLA2 lab automation - Phase 3版"""
    
    def __init__(self):
        # Phase 3: SiLA2クライアント統合
        try:
            self.sila2_client = SiLA2Client()
            self.devices = {device['id']: device for device in self.sila2_client.discover_devices()}
        except Exception as e:
            logger.warning(f"SiLA2 client init failed, using fallback: {e}")
            self.sila2_client = None
            self.devices = {
                "HPLC-01": {"status": "ready", "type": "HPLC", "location": "Lab-A"},
                "CENTRIFUGE-01": {"status": "busy", "type": "Centrifuge", "location": "Lab-B"},
                "PIPETTE-01": {"status": "ready", "type": "Pipette", "location": "Lab-A"}
            }
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get current status of SiLA2 laboratory device - Phase 3版"""
        try:
            if device_id not in self.devices:
                return {
                    "success": False,
                    "error": f"Device {device_id} not found",
                    "available_devices": list(self.devices.keys())
                }
            
            # Phase 3: SiLA2クライアント使用
            if self.sila2_client:
                status = self.sila2_client.get_device_status(device_id)
                return {"success": True, **status}
            
            # Fallback
            device = self.devices[device_id]
            return {
                "success": True,
                "device_id": device_id,
                "status": device["status"],
                "type": device["type"],
                "location": device["location"],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return {"success": False, "error": str(e)}
    
    def start_device_operation(self, device_id: str, operation: str, parameters: Dict = None) -> Dict[str, Any]:
        """Start operation on SiLA2 laboratory device - Phase 3版"""
        try:
            if device_id not in self.devices:
                return {"success": False, "error": f"Device {device_id} not found"}
            
            # Phase 3: SiLA2クライアント使用
            if self.sila2_client:
                result = self.sila2_client.start_operation(device_id, operation)
                if 'error' in result:
                    return {"success": False, **result}
                return {"success": True, **result}
            
            # Fallback
            if self.devices[device_id]["status"] != "ready":
                return {"success": False, "error": f"Device {device_id} is busy"}
            
            self.devices[device_id]["status"] = "running"
            return {
                "success": True,
                "device_id": device_id,
                "operation": operation,
                "parameters": parameters or {},
                "status": "started",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error starting operation: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_device_operation(self, device_id: str) -> Dict[str, Any]:
        """Stop current operation on SiLA2 device"""
        try:
            if device_id not in self.devices:
                return {"success": False, "error": f"Device {device_id} not found"}
            
            self.devices[device_id]["status"] = "idle"
            
            return {
                "success": True,
                "device_id": device_id,
                "status": "stopped",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error stopping operation: {e}")
            return {"success": False, "error": str(e)}
    
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
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
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
        if tool_name == 'get_device_status':
            result = tools.get_device_status(parameters.get('device_id'))
        elif tool_name == 'start_device_operation':
            result = tools.start_device_operation(
                parameters.get('device_id'),
                parameters.get('operation'),
                parameters.get('parameters')
            )
        elif tool_name == 'stop_device_operation':
            result = tools.stop_device_operation(parameters.get('device_id'))
        elif tool_name == 'list_available_devices':
            result = tools.list_available_devices()
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