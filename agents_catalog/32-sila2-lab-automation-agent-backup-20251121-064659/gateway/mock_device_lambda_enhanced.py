"""
Enhanced Mock Device Lambda - Phase 3
API Gateway対応、詳細デバイスシミュレーション
"""
import json
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DeviceRegistry:
    """デバイス登録管理"""
    
    DEVICES = {
        "HPLC-01": {"type": "hplc", "location": "Lab-A", "status": "ready"},
        "CENTRIFUGE-01": {"type": "centrifuge", "location": "Lab-B", "status": "busy"},
        "PIPETTE-01": {"type": "pipette", "location": "Lab-A", "status": "ready"}
    }
    
    @classmethod
    def get_device_info(cls, device_id: str) -> Dict[str, Any]:
        return cls.DEVICES.get(device_id, {})
    
    @classmethod
    def list_devices(cls) -> list:
        return [
            {"device_id": device_id, **info}
            for device_id, info in cls.DEVICES.items()
        ]

class HPLCSimulator:
    """HPLC詳細シミュレーター"""
    
    @staticmethod
    def get_status(device_id: str) -> Dict[str, Any]:
        return {
            "device_id": device_id,
            "status": "ready",
            "type": "HPLC",
            "temperature": 25.0,
            "pressure": 150.0,
            "flow_rate": 1.0,
            "column": "C18",
            "mobile_phase": "ACN/H2O"
        }
    
    @staticmethod
    def start_analysis(device_id: str, parameters: dict) -> Dict[str, Any]:
        return {
            "device_id": device_id,
            "operation": "analysis_started",
            "method": parameters.get("method", "default"),
            "estimated_time": 1800,
            "status": "running"
        }

class CentrifugeSimulator:
    """遠心分離機詳細シミュレーター"""
    
    @staticmethod
    def get_status(device_id: str) -> Dict[str, Any]:
        return {
            "device_id": device_id,
            "status": "busy",
            "type": "Centrifuge",
            "rpm": 3000,
            "temperature": 4.0,
            "remaining_time": 600,
            "rotor_type": "fixed_angle"
        }
    
    @staticmethod
    def start_spin(device_id: str, parameters: dict) -> Dict[str, Any]:
        return {
            "device_id": device_id,
            "operation": "spin_started",
            "rpm": parameters.get("rpm", 3000),
            "duration": parameters.get("duration", 600),
            "temperature": parameters.get("temperature", 4.0)
        }

class PipetteSimulator:
    """ピペット詳細シミュレーター"""
    
    @staticmethod
    def get_status(device_id: str) -> Dict[str, Any]:
        return {
            "device_id": device_id,
            "status": "ready",
            "type": "Pipette",
            "tip_attached": True,
            "volume_range": "0.1-1000μL",
            "current_volume": 0
        }
    
    @staticmethod
    def aspirate(device_id: str, parameters: dict) -> Dict[str, Any]:
        return {
            "device_id": device_id,
            "operation": "aspirate_completed",
            "volume": parameters.get("volume", 100),
            "position": parameters.get("position", "A1"),
            "speed": parameters.get("speed", "normal")
        }

class MockDeviceLambdaEnhanced:
    """Enhanced Mock Device Lambda"""
    
    def __init__(self):
        self.simulators = {
            "hplc": HPLCSimulator(),
            "centrifuge": CentrifugeSimulator(),
            "pipette": PipetteSimulator()
        }
    
    def handle_list_devices(self) -> Dict[str, Any]:
        """デバイス一覧取得"""
        devices = DeviceRegistry.list_devices()
        return {
            "success": True,
            "devices": devices,
            "count": len(devices),
            "timestamp": datetime.now().isoformat()
        }
    
    def handle_device_status(self, device_id: str) -> Dict[str, Any]:
        """デバイス状態取得"""
        device_info = DeviceRegistry.get_device_info(device_id)
        if not device_info:
            return {"success": False, "error": f"Device {device_id} not found"}
        
        simulator = self.simulators.get(device_info["type"])
        if not simulator:
            return {"success": False, "error": f"Simulator for {device_info['type']} not found"}
        
        status = simulator.get_status(device_id)
        status.update({"success": True, "timestamp": datetime.now().isoformat()})
        return status
    
    def handle_device_operation(self, device_id: str, operation: str, parameters: dict = None) -> Dict[str, Any]:
        """デバイス操作実行"""
        device_info = DeviceRegistry.get_device_info(device_id)
        if not device_info:
            return {"success": False, "error": f"Device {device_id} not found"}
        
        simulator = self.simulators.get(device_info["type"])
        if not simulator:
            return {"success": False, "error": f"Simulator for {device_info['type']} not found"}
        
        # 操作実行
        method = getattr(simulator, operation, None)
        if not method:
            return {"success": False, "error": f"Operation {operation} not supported"}
        
        result = method(device_id, parameters or {})
        result.update({"success": True, "timestamp": datetime.now().isoformat()})
        return result

def lambda_handler(event, context):
    """Lambda エントリーポイント - API Gateway対応"""
    try:
        mock_device = MockDeviceLambdaEnhanced()
        
        # API Gateway event parsing
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        path_params = event.get('pathParameters') or {}
        query_params = event.get('queryStringParameters') or {}
        
        # Body parsing
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                pass
        
        # Route handling
        if path == '/devices' and http_method == 'GET':
            result = mock_device.handle_list_devices()
        
        elif path.startswith('/device/') and http_method == 'GET':
            device_id = path_params.get('device_id')
            if not device_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'device_id required'})
                }
            result = mock_device.handle_device_status(device_id)
        
        elif path.startswith('/device/') and http_method == 'POST':
            device_id = path_params.get('device_id')
            operation = body.get('operation')
            parameters = body.get('parameters', {})
            
            if not all([device_id, operation]):
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'device_id and operation required'})
                }
            
            result = mock_device.handle_device_operation(device_id, operation, parameters)
        
        else:
            result = {'success': False, 'error': 'Invalid endpoint'}
        
        return {
            'statusCode': 200 if result.get('success') else 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': False, 'error': str(e)})
        }