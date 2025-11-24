"""
SiLA2 Gateway Tools - Phase 3 Simplified版
HTTP呼び出しによるレイヤー分離実装
"""
import json
import logging
import requests
import os
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SiLA2GatewayToolsSimplified:
    """Simplified Gateway tools - HTTP呼び出し版"""
    
    def __init__(self):
        # Mock Device Lambda API endpoint (環境変数から取得)
        self.mock_device_api = os.environ.get('MOCK_DEVICE_API_URL', 'https://api-gateway-url/dev')
        self.timeout = 30
    
    def list_available_devices(self) -> Dict[str, Any]:
        """List all available SiLA2 laboratory devices"""
        try:
            # HTTP呼び出しでデバイス一覧取得
            try:
                response = requests.get(f"{self.mock_device_api}/devices", timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
            except requests.RequestException as e:
                logger.warning(f"HTTP call failed, using fallback: {e}")
            
            # Fallback: Mock devices
            devices = [
                {"device_id": "HPLC-01", "type": "HPLC", "status": "ready", "location": "Lab-A"},
                {"device_id": "CENTRIFUGE-01", "type": "Centrifuge", "status": "busy", "location": "Lab-B"},
                {"device_id": "PIPETTE-01", "type": "Pipette", "status": "ready", "location": "Lab-A"}
            ]
            
            return {
                "success": True,
                "devices": devices,
                "count": len(devices),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return {"success": False, "error": str(e)}
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get current status of SiLA2 laboratory device"""
        try:
            # HTTP呼び出しでデバイス状態取得
            try:
                response = requests.get(f"{self.mock_device_api}/device/{device_id}", timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
            except requests.RequestException as e:
                logger.warning(f"HTTP call failed, using fallback: {e}")
            
            # Fallback: Mock device data
            device_data = {
                "HPLC-01": {"status": "ready", "type": "HPLC", "temperature": 25.0, "pressure": 150.0},
                "CENTRIFUGE-01": {"status": "busy", "type": "Centrifuge", "rpm": 3000, "remaining_time": 600},
                "PIPETTE-01": {"status": "ready", "type": "Pipette", "tip_attached": True}
            }
            
            if device_id not in device_data:
                return {
                    "success": False,
                    "error": f"Device {device_id} not found",
                    "available_devices": list(device_data.keys())
                }
            
            result = device_data[device_id]
            result.update({
                "success": True,
                "device_id": device_id,
                "timestamp": datetime.now().isoformat()
            })
            
            return result
        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return {"success": False, "error": str(e)}
    
    def start_device_operation(self, device_id: str, operation: str, parameters: Dict = None) -> Dict[str, Any]:
        """Start operation on SiLA2 laboratory device"""
        try:
            # HTTP呼び出しでデバイス操作実行
            try:
                payload = {"operation": operation, "parameters": parameters or {}}
                response = requests.post(f"{self.mock_device_api}/device/{device_id}", 
                                       json=payload, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
            except requests.RequestException as e:
                logger.warning(f"HTTP call failed, using fallback: {e}")
            
            # Fallback: Simulation
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

# Lambda handler
def lambda_handler(event, context):
    """AWS Lambda handler for simplified Gateway tools"""
    try:
        tools = SiLA2GatewayToolsSimplified()
        
        tool_name = event.get('tool_name')
        parameters = event.get('parameters', {})
        
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