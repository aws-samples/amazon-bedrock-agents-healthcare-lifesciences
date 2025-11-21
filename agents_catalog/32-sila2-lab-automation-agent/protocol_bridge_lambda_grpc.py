"""
SiLA2 Protocol Bridge Lambda - Phase 3 with gRPC
HTTP ↔ gRPC変換、デバイスレジストリ、統合ハンドラー
"""
import json
import logging
import os
import requests
from typing import Dict, Any
from datetime import datetime

# gRPC imports
try:
    import grpc
    import sila2_basic_pb2 as sila2_pb
    import sila2_basic_pb2_grpc as sila2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    logging.warning("gRPC not available, using HTTP fallback only")

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

class GRPCProtocolBridge:
    """HTTP ↔ gRPC Protocol Bridge with gRPC support"""
    
    def __init__(self):
        self.mock_device_api = os.environ.get('MOCK_DEVICE_API_URL', '')
        self.grpc_endpoint = os.environ.get('GRPC_ENDPOINT', 'localhost:50051')
        self.timeout = 30
        self.grpc_channel = None
        self.grpc_stub = None
        
        # Initialize gRPC client if available
        if GRPC_AVAILABLE:
            self._init_grpc_client()
    
    def _init_grpc_client(self):
        """Initialize gRPC client"""
        try:
            # Try direct gRPC connection first
            self.grpc_channel = grpc.insecure_channel(self.grpc_endpoint)
            self.grpc_stub = sila2_grpc.SiLA2DeviceStub(self.grpc_channel)
            logger.info(f"gRPC client initialized for {self.grpc_endpoint}")
        except Exception as e:
            logger.warning(f"Direct gRPC connection failed, will use API Gateway: {e}")
            self.grpc_stub = None
    
    def convert_http_to_grpc(self, http_request: Dict[str, Any]) -> Dict[str, Any]:
        """HTTP リクエストをgRPC形式に変換"""
        try:
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
            http_response = {
                "success": grpc_response.get("success", True),
                "data": grpc_response.get("data", {}),
                "timestamp": datetime.now().isoformat()
            }
            return http_response
        except Exception as e:
            logger.error(f"gRPC to HTTP conversion error: {e}")
            return {"success": False, "error": str(e)}
    
    def _call_grpc_device(self, device_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call gRPC device service (direct or via API Gateway)"""
        try:
            # Try direct gRPC first
            if self.grpc_stub:
                return self._call_direct_grpc(device_id, request)
            
            # Fallback to API Gateway gRPC endpoint
            return self._call_api_gateway_grpc(device_id, request)
            
        except Exception as e:
            logger.error(f"gRPC call exception: {e}")
            return {"success": False, "error": str(e)}
    
    def _call_direct_grpc(self, device_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call direct gRPC service"""
        try:
            method = request.get("method", "GET")
            operation = request.get("operation")
            
            if method == "GET" and not operation:
                grpc_request = sila2_pb.DeviceInfoRequest(device_id=device_id)
                response = self.grpc_stub.GetDeviceInfo(grpc_request)
                
                return {
                    "success": True,
                    "device_id": response.device_id,
                    "status": response.status,
                    "type": response.device_type,
                    "properties": dict(response.properties),
                    "timestamp": response.timestamp,
                    "source": "direct_grpc"
                }
            
            elif operation:
                grpc_request = sila2_pb.CommandRequest(
                    device_id=device_id,
                    operation=operation,
                    parameters=request.get("parameters", {})
                )
                response = self.grpc_stub.ExecuteCommand(grpc_request)
                
                return {
                    "success": response.success,
                    "device_id": response.device_id,
                    "operation": response.operation,
                    "status": response.status,
                    "result": dict(response.result),
                    "timestamp": response.timestamp,
                    "source": "direct_grpc"
                }
            
            return {"success": False, "error": "Invalid gRPC request"}
            
        except grpc.RpcError as e:
            logger.error(f"Direct gRPC call error: {e}")
            return {"success": False, "error": f"gRPC error: {e.code()}"}
    
    def _call_api_gateway_grpc(self, device_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call API Gateway gRPC endpoint"""
        try:
            method = request.get("method", "GET")
            operation = request.get("operation")
            
            # Construct API Gateway gRPC URL
            grpc_api_url = self.mock_device_api.replace('/dev', '/dev/grpc')
            
            if method == "GET" and not operation:
                response = requests.get(
                    f"{grpc_api_url}/device/{device_id}",
                    timeout=self.timeout
                )
            elif operation:
                response = requests.post(
                    f"{grpc_api_url}/device/{device_id}",
                    json={"operation": operation, "parameters": request.get("parameters", {})},
                    timeout=self.timeout
                )
            else:
                return {"success": False, "error": "Invalid API Gateway gRPC request"}
            
            if response.status_code == 200:
                result = response.json()
                result["source"] = "api_gateway_grpc"
                return result
            else:
                return {"success": False, "error": f"API Gateway error: {response.status_code}"}
                
        except requests.RequestException as e:
            logger.error(f"API Gateway gRPC call error: {e}")
            return {"success": False, "error": str(e)}
    
    def route_to_device(self, device_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """デバイスへのリクエストルーティング"""
        try:
            device_info = DeviceRegistry.get_device_info(device_id)
            if not device_info:
                return {"success": False, "error": f"Device {device_id} not found"}
            
            # Try gRPC first if available (direct or API Gateway)
            if GRPC_AVAILABLE:
                try:
                    grpc_result = self._call_grpc_device(device_id, request)
                    if grpc_result.get("success"):
                        return grpc_result
                except Exception as e:
                    logger.warning(f"gRPC call failed, falling back to HTTP: {e}")
            
            # HTTP fallback
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
                        result = response.json()
                        result["source"] = "http"
                        return result
                
                except requests.RequestException as e:
                    logger.warning(f"HTTP API call failed: {e}")
            
            # Final fallback
            return {
                "success": True,
                "device_id": device_id,
                "device_type": device_info["type"],
                "status": "simulated",
                "timestamp": datetime.now().isoformat(),
                "source": "fallback"
            }
            
        except Exception as e:
            logger.error(f"Device routing error: {e}")
            return {"success": False, "error": str(e)}

class ProtocolBridgeLambdaGRPC:
    """Protocol Bridge Lambda with gRPC support"""
    
    def __init__(self):
        self.bridge = GRPCProtocolBridge()
    
    def handle_device_list(self) -> Dict[str, Any]:
        """デバイス一覧取得"""
        # Try gRPC first if available
        if GRPC_AVAILABLE:
            try:
                # Try direct gRPC
                if self.bridge.grpc_stub:
                    grpc_request = sila2_pb.ListDevicesRequest()
                    response = self.bridge.grpc_stub.ListDevices(grpc_request)
                    
                    devices = []
                    for device in response.devices:
                        devices.append({
                            "device_id": device.device_id,
                            "type": device.device_type,
                            "status": device.status,
                            "location": device.location
                        })
                    
                    return {
                        "success": True,
                        "devices": devices,
                        "count": response.count,
                        "timestamp": response.timestamp,
                        "source": "direct_grpc"
                    }
                
                # Try API Gateway gRPC
                elif self.bridge.mock_device_api:
                    grpc_api_url = self.bridge.mock_device_api.replace('/dev', '/dev/grpc')
                    response = requests.get(f"{grpc_api_url}/devices", timeout=self.bridge.timeout)
                    if response.status_code == 200:
                        result = response.json()
                        result["source"] = "api_gateway_grpc"
                        return result
                        
            except Exception as e:
                logger.warning(f"gRPC device list failed, using fallback: {e}")
        
        # HTTP/Local fallback
        devices = DeviceRegistry.list_all_devices()
        return {
            "success": True,
            "devices": devices,
            "count": len(devices),
            "timestamp": datetime.now().isoformat(),
            "source": "fallback"
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
        bridge_lambda = ProtocolBridgeLambdaGRPC()
        
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