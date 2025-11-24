"""
SiLA2 AgentCore Gateway Implementation
"""

import json
import logging
from typing import Dict, Any, List
from bedrock_agentcore.gateway import Gateway, Tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SiLA2Gateway(Gateway):
    """AgentCore Gateway for SiLA2 devices"""
    
    def __init__(self):
        super().__init__(
            name="sila2-lab-automation-gateway",
            description="SiLA2 Lab Automation Gateway for AgentCore",
            version="1.0.0"
        )
        self._register_tools()
    
    def _register_tools(self):
        """Register SiLA2 tools with the gateway"""
        
        # List available devices tool
        @self.tool(
            name="list_available_devices",
            description="List all available SiLA2 devices"
        )
        def list_available_devices() -> Dict[str, Any]:
            return self._list_available_devices()
        
        # Get device status tool
        @self.tool(
            name="get_device_status",
            description="Get status of a specific SiLA2 device",
            parameters={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier"
                    }
                },
                "required": ["device_id"]
            }
        )
        def get_device_status(device_id: str) -> Dict[str, Any]:
            return self._get_device_status(device_id)
        
        # Start device operation tool
        @self.tool(
            name="start_device_operation",
            description="Start an operation on a SiLA2 device",
            parameters={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier"
                    },
                    "operation": {
                        "type": "string",
                        "description": "Operation to start"
                    }
                },
                "required": ["device_id", "operation"]
            }
        )
        def start_device_operation(device_id: str, operation: str) -> Dict[str, Any]:
            return self._start_device_operation(device_id, operation)
        
        # Stop device operation tool
        @self.tool(
            name="stop_device_operation",
            description="Stop an operation on a SiLA2 device",
            parameters={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device identifier"
                    },
                    "operation_id": {
                        "type": "string",
                        "description": "Operation identifier to stop"
                    }
                },
                "required": ["device_id", "operation_id"]
            }
        )
        def stop_device_operation(device_id: str, operation_id: str) -> Dict[str, Any]:
            return self._stop_device_operation(device_id, operation_id)
    
    def _list_available_devices(self) -> Dict[str, Any]:
        """List all available SiLA2 devices"""
        try:
            devices = [
                {
                    "device_id": "HPLC-01",
                    "device_type": "HPLC",
                    "status": "ready",
                    "location": "Lab-A",
                    "gateway_source": "AgentCore Gateway"
                },
                {
                    "device_id": "CENTRIFUGE-01", 
                    "device_type": "Centrifuge",
                    "status": "busy",
                    "location": "Lab-B",
                    "gateway_source": "AgentCore Gateway"
                },
                {
                    "device_id": "PIPETTE-01",
                    "device_type": "Pipette",
                    "status": "ready",
                    "location": "Lab-A",
                    "gateway_source": "AgentCore Gateway"
                }
            ]
            
            return {
                "success": True,
                "devices": devices,
                "count": len(devices),
                "source": "AgentCore Gateway"
            }
            
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return {"error": str(e)}
    
    def _get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get status of a specific device"""
        try:
            if not device_id:
                return {"error": "device_id is required"}
            
            status = {
                "device_id": device_id,
                "status": "ready",
                "temperature": "25.0°C",
                "last_maintenance": "2025-01-15",
                "operational_hours": 1250,
                "gateway_source": "AgentCore Gateway",
                "protocol": "SiLA2"
            }
            
            return {
                "success": True,
                "device_status": status,
                "source": "AgentCore Gateway"
            }
            
        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return {"error": str(e)}
    
    def _start_device_operation(self, device_id: str, operation: str) -> Dict[str, Any]:
        """Start an operation on a device"""
        try:
            if not device_id:
                return {"error": "device_id is required"}
            if not operation:
                operation = "default_analysis"
            
            result = {
                "device_id": device_id,
                "operation": operation,
                "status": "started",
                "estimated_duration": "30 minutes",
                "operation_id": f"OP-{device_id}-GW-001",
                "gateway_source": "AgentCore Gateway",
                "protocol": "SiLA2"
            }
            
            return {
                "success": True,
                "operation_result": result,
                "source": "AgentCore Gateway"
            }
            
        except Exception as e:
            logger.error(f"Error starting operation: {e}")
            return {"error": str(e)}
    
    def _stop_device_operation(self, device_id: str, operation_id: str) -> Dict[str, Any]:
        """Stop an operation on a device"""
        try:
            if not device_id:
                return {"error": "device_id is required"}
            if not operation_id:
                return {"error": "operation_id is required"}
            
            result = {
                "device_id": device_id,
                "operation_id": operation_id,
                "status": "stopped",
                "reason": "user_requested_via_agentcore_gateway",
                "gateway_source": "AgentCore Gateway",
                "protocol": "SiLA2"
            }
            
            return {
                "success": True,
                "stop_result": result,
                "source": "AgentCore Gateway"
            }
            
        except Exception as e:
            logger.error(f"Error stopping operation: {e}")
            return {"error": str(e)}

# Create gateway instance
gateway = SiLA2Gateway()

if __name__ == "__main__":
    gateway.run()