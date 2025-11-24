"""
SiLA2 Protocol Bridge Lambda - Phase 3
HTTP ↔ gRPC変換、デバイスレジストリ、統合ハンドラー
"""
import json
import logging
import os
import requests
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DeviceRegistry:
    """統合デバイスレジストリ"""
    
    DEVICE_CONFIG = {
        "HPLC-01": {
            "type": "hplc",
            "location": "Lab-A", 
            "port": 50051,
            "features": ["analysis", "status", "temperature_control"]
        },
        "CENTRIFUGE-01": {
            "type": "centrifuge",
            "location": "Lab-B",
            "port": 50052, 
            "features": ["spin", "status", "temperature_control"]
        },
        "PIPETTE-01": {
            "type": "pipette",
            "location": "Lab-A",
            "port": 50053,
            "features": ["aspirate", "dispense", "status"]
        }
    }
    
    @classmethod
    def get_device_info(cls, device_id: str) -> Dict[str, Any]:
        return cls.DEVICE_CONFIG.get(device_id, {})
    
    @classmethod
    def list_all_devices(cls) -> list:
        return [
            {"device_id": device_id, **info}
            for device_id, info in cls.DEVICE_CONFIG.items()
        ]

class ProtocolBridge:
    """HTTP ↔ gRPC Protocol Bridge"""
    
    def __init__(self):
        self.mock_device_api = os.environ.get('MOCK_DEVICE_API_URL', '')
        self.timeout = 30
    
    def convert_http_to_grpc(self, http_request: Dict[str, Any]) -> Dict[str, Any]:
        """HTTP リクエストをgRPC形式に変換"""
        try:
            # HTTP → gRPC変換ロジック (簡略化)
            grpc_request = {
                "method": http_request.get("method", "GET"),
                "device_id": http_request.get("device_id"),
                "operation": http_request.get("operation"),
                "parameters": http_request.get("parameters", {}),
                "timestamp": datetime.now().isoformat()
            }
            return grpc_request
        except Exception as e:
            logger.error(f"HTTP to gRPC conversion error: {e}")
            return {}
    
    def convert_grpc_to_http(self, grpc_response: Dict[str, Any]) -> Dict[str, Any]:
        """gRPC レスポンスをHTTP形式に変換"""
        try:
            # gRPC → HTTP変換ロジック (簡略化)
            http_response = {
                "success": grpc_response.get("success", True),
                "data": grpc_response.get("data", {}),
                "timestamp": datetime.now().isoformat()
            }
            return http_response
        except Exception as e:
            logger.error(f"gRPC to HTTP conversion error: {e}")
            return {"success": False, "error": str(e)}
    
    def route_to_device(self, device_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """デバイスへのリクエストルーティング"""
        try:
            device_info = DeviceRegistry.get_device_info(device_id)
            if not device_info:
                return {"success": False, "error": f"Device {device_id} not found"}
            
            # Mock Device API呼び出し
            if self.mock_device_api:
                try:
                    if request.get("method") == "GET":
                        response = requests.get(
                            f"{self.mock_device_api}/device/{device_id}",
                            timeout=self.timeout
                        )
                    else:
                        response = requests.post(
                            f"{self.mock_device_api}/device/{device_id}",
                            json=request,
                            timeout=self.timeout
                        )
                    
                    if response.status_code == 200:
                        return response.json()
                
                except requests.RequestException as e:
                    logger.warning(f"Device API call failed: {e}")
            
            # Fallback response
            return {
                "success": True,
                "device_id": device_id,
                "device_type": device_info["type"],
                "status": "simulated",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Device routing error: {e}")
            return {"success": False, "error": str(e)}

class ProtocolBridgeLambda:
    """Protocol Bridge Lambda メインクラス"""
    
    def __init__(self):
        self.bridge = ProtocolBridge()
    
    def handle_device_list(self) -> Dict[str, Any]:
        """デバイス一覧取得"""
        devices = DeviceRegistry.list_all_devices()
        return {
            "success": True,
            "devices": devices,
            "count": len(devices),
            "timestamp": datetime.now().isoformat()
        }
    
    def handle_device_request(self, device_id: str, method: str, body: Dict = None) -> Dict[str, Any]:
        """デバイスリクエスト処理"""
        try:
            # HTTP → gRPC変換
            http_request = {
                "method": method,
                "device_id": device_id,
                "operation": body.get("operation") if body else None,
                "parameters": body.get("parameters", {}) if body else {}
            }
            
            grpc_request = self.bridge.convert_http_to_grpc(http_request)
            
            # デバイスルーティング
            grpc_response = self.bridge.route_to_device(device_id, grpc_request)
            
            # gRPC → HTTP変換
            http_response = self.bridge.convert_grpc_to_http(grpc_response)
            
            return http_response
            
        except Exception as e:
            logger.error(f"Device request handling error: {e}")
            return {"success": False, "error": str(e)}

def lambda_handler(event, context):
    """Lambda エントリーポイント"""
    try:
        bridge_lambda = ProtocolBridgeLambda()
        
        # API Gateway event parsing
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        path_params = event.get('pathParameters') or {}
        
        # Body parsing
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                pass
        
        # Route handling
        if path == '/devices' and http_method == 'GET':
            result = bridge_lambda.handle_device_list()
        
        elif path.startswith('/device/') and path_params.get('device_id'):
            device_id = path_params['device_id']
            result = bridge_lambda.handle_device_request(device_id, http_method, body)
        
        else:
            result = {'success': False, 'error': 'Invalid endpoint'}
        
        return {
            'statusCode': 200 if result.get('success') else 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Protocol Bridge Lambda error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': False, 'error': str(e)})
        }