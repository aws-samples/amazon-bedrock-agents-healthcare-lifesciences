"""gRPC Client for SiLA2 Mock Devices"""
import grpc
import os
from typing import Dict, Any
import sys

# Add proto directory to path
proto_dir = os.path.join(os.path.dirname(__file__), 'proto')
if os.path.exists(proto_dir):
    sys.path.insert(0, proto_dir)
else:
    # Fallback to parent directory for local development
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sila2_basic_pb2
import sila2_basic_pb2_grpc


class GrpcClient:
    def __init__(self):
        self.channels = {}
        self.stubs = {}
        try:
            self._init_connections()
        except Exception as e:
            print(f"Warning: Failed to initialize gRPC connections: {e}")
            print("Server will start but device connections may not work")
    
    def _init_connections(self):
        devices = {
            'hplc': os.getenv('HPLC_GRPC_URL', 'localhost:50051'),
            'centrifuge': os.getenv('CENTRIFUGE_GRPC_URL', 'localhost:50052'),
            'pipette': os.getenv('PIPETTE_GRPC_URL', 'localhost:50053')
        }
        
        for name, url in devices.items():
            try:
                self.channels[name] = grpc.insecure_channel(url)
                self.stubs[name] = sila2_basic_pb2_grpc.SiLA2DeviceStub(self.channels[name])
                print(f"Connected to {name} at {url}")
            except Exception as e:
                print(f"Warning: Failed to connect to {name} at {url}: {e}")
    
    def list_devices(self) -> Dict[str, Any]:
        devices = []
        for device_id in ['hplc', 'centrifuge', 'pipette']:
            stub = self.stubs.get(device_id)
            if stub:
                try:
                    request = sila2_basic_pb2.DeviceInfoRequest(device_id=device_id)
                    response = stub.GetDeviceInfo(request, timeout=2)
                    devices.append({
                        'id': response.device_id,
                        'type': response.device_type,
                        'status': response.status
                    })
                except Exception as e:
                    devices.append({'id': device_id, 'type': 'Unknown', 'status': 'offline', 'error': str(e)})
        return {'devices': devices}
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        stub = self.stubs.get(device_id)
        if not stub:
            return {'error': f'Device {device_id} not found'}
        
        try:
            request = sila2_basic_pb2.DeviceInfoRequest(device_id=device_id)
            response = stub.GetDeviceInfo(request, timeout=2)
            return {'device_id': response.device_id, 'status': response.status, 'type': response.device_type}
        except Exception as e:
            return {'error': str(e)}
    
    def execute_command(self, device_id: str, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        stub = self.stubs.get(device_id)
        if not stub:
            return {'error': f'Device {device_id} not found'}
        
        try:
            request = sila2_basic_pb2.CommandRequest(
                device_id=device_id,
                operation=command,
                parameters={k: str(v) for k, v in parameters.items()}
            )
            response = stub.ExecuteCommand(request, timeout=5)
            return {'success': response.success, 'status': response.status, 'result': dict(response.result)}
        except Exception as e:
            return {'error': str(e)}
