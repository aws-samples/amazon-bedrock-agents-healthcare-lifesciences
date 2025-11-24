"""
Lambda-based gRPC Device Handler - API Gateway Interface
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any

# gRPC imports
try:
    import grpc
    import sila2_basic_pb2 as sila2_pb
    import sila2_basic_pb2_grpc as sila2_grpc
    from grpc_mock_device_server import SiLA2DeviceService
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False

logger = logging.getLogger(__name__)

class LambdaGRPCDeviceHandler:
    """Lambda-based gRPC Device Handler for API Gateway"""
    
    def __init__(self):
        self.device_service = SiLA2DeviceService() if GRPC_AVAILABLE else None
    
    def handle_list_devices(self) -> Dict[str, Any]:
        """Handle device list request"""
        try:
            if not self.device_service:
                return {"success": False, "error": "gRPC service not available"}
            
            # Simulate gRPC call within Lambda
            request = sila2_pb.ListDevicesRequest()
            response = self.device_service.ListDevices(request, None)
            
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
                "source": "lambda_grpc"
            }
            
        except Exception as e:
            logger.error(f"Error in handle_list_devices: {e}")
            return {"success": False, "error": str(e)}
    
    def handle_get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Handle device info request"""
        try:
            if not self.device_service:
                return {"success": False, "error": "gRPC service not available"}
            
            # Simulate gRPC call within Lambda
            request = sila2_pb.DeviceInfoRequest(device_id=device_id)
            response = self.device_service.GetDeviceInfo(request, None)
            
            return {
                "success": True,
                "device_id": response.device_id,
                "status": response.status,
                "type": response.device_type,
                "properties": dict(response.properties),
                "timestamp": response.timestamp,
                "source": "lambda_grpc"
            }
            
        except Exception as e:
            logger.error(f"Error in handle_get_device_info: {e}")
            return {"success": False, "error": str(e)}
    
    def handle_execute_command(self, device_id: str, operation: str, parameters: Dict = None) -> Dict[str, Any]:
        """Handle command execution request"""
        try:
            if not self.device_service:
                return {"success": False, "error": "gRPC service not available"}
            
            # Simulate gRPC call within Lambda
            request = sila2_pb.CommandRequest(
                device_id=device_id,
                operation=operation,
                parameters=parameters or {}
            )
            response = self.device_service.ExecuteCommand(request, None)
            
            return {
                "success": response.success,
                "device_id": response.device_id,
                "operation": response.operation,
                "status": response.status,
                "result": dict(response.result),
                "timestamp": response.timestamp,
                "source": "lambda_grpc"
            }
            
        except Exception as e:
            logger.error(f"Error in handle_execute_command: {e}")
            return {"success": False, "error": str(e)}

def lambda_handler(event, context):
    """Lambda handler for API Gateway gRPC interface"""
    try:
        handler = LambdaGRPCDeviceHandler()
        
        # Parse API Gateway event
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        path_params = event.get('pathParameters') or {}
        
        # Parse body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                pass
        
        # Route handling
        if path == '/grpc/devices' and http_method == 'GET':
            result = handler.handle_list_devices()
        
        elif path.startswith('/grpc/device/') and http_method == 'GET':
            device_id = path_params.get('device_id')
            if not device_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'device_id required'})
                }
            result = handler.handle_get_device_info(device_id)
        
        elif path.startswith('/grpc/device/') and http_method == 'POST':
            device_id = path_params.get('device_id')
            operation = body.get('operation')
            parameters = body.get('parameters', {})
            
            if not all([device_id, operation]):
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'device_id and operation required'})
                }
            
            result = handler.handle_execute_command(device_id, operation, parameters)
        
        else:
            result = {'success': False, 'error': 'Invalid gRPC endpoint'}
        
        return {
            'statusCode': 200 if result.get('success') else 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Lambda gRPC handler error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': False, 'error': str(e)})
        }