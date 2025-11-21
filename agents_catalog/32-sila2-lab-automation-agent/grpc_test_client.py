"""
gRPC Test Client for SiLA2 Protocol
"""
import grpc
import logging
from datetime import datetime

import sila2_basic_pb2 as sila2_pb
import sila2_basic_pb2_grpc as sila2_grpc

logger = logging.getLogger(__name__)

class SiLA2GRPCClient:
    """gRPC Client for SiLA2 Protocol Testing"""
    
    def __init__(self, endpoint="localhost:50051"):
        self.endpoint = endpoint
        self.channel = None
        self.stub = None
    
    def connect(self):
        """Connect to gRPC server"""
        try:
            self.channel = grpc.insecure_channel(self.endpoint)
            self.stub = sila2_grpc.SiLA2DeviceStub(self.channel)
            logger.info(f"Connected to gRPC server at {self.endpoint}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to gRPC server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from gRPC server"""
        if self.channel:
            self.channel.close()
            logger.info("Disconnected from gRPC server")
    
    def list_devices(self):
        """List all devices"""
        try:
            request = sila2_pb.ListDevicesRequest()
            response = self.stub.ListDevices(request)
            
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
                "timestamp": response.timestamp
            }
        except grpc.RpcError as e:
            logger.error(f"gRPC error in list_devices: {e}")
            return {"success": False, "error": str(e)}
    
    def get_device_info(self, device_id: str):
        """Get device information"""
        try:
            request = sila2_pb.DeviceInfoRequest(device_id=device_id)
            response = self.stub.GetDeviceInfo(request)
            
            return {
                "success": True,
                "device_id": response.device_id,
                "status": response.status,
                "type": response.device_type,
                "properties": dict(response.properties),
                "timestamp": response.timestamp
            }
        except grpc.RpcError as e:
            logger.error(f"gRPC error in get_device_info: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_command(self, device_id: str, operation: str, parameters: dict = None):
        """Execute device command"""
        try:
            request = sila2_pb.CommandRequest(
                device_id=device_id,
                operation=operation,
                parameters=parameters or {}
            )
            response = self.stub.ExecuteCommand(request)
            
            return {
                "success": response.success,
                "device_id": response.device_id,
                "operation": response.operation,
                "status": response.status,
                "result": dict(response.result),
                "timestamp": response.timestamp
            }
        except grpc.RpcError as e:
            logger.error(f"gRPC error in execute_command: {e}")
            return {"success": False, "error": str(e)}

def test_grpc_client():
    """Test gRPC client functionality"""
    print("=== gRPC Client Test ===")
    
    client = SiLA2GRPCClient()
    
    # Connect
    if not client.connect():
        print("Failed to connect to gRPC server")
        return
    
    try:
        # Test 1: List devices
        print("\n1. Testing list_devices...")
        result = client.list_devices()
        print(f"Result: {result}")
        
        if result.get("success") and result.get("devices"):
            device_id = result["devices"][0]["device_id"]
            
            # Test 2: Get device info
            print(f"\n2. Testing get_device_info for {device_id}...")
            result = client.get_device_info(device_id)
            print(f"Result: {result}")
            
            # Test 3: Execute command
            print(f"\n3. Testing execute_command for {device_id}...")
            result = client.execute_command(device_id, "start_analysis", {"method": "test"})
            print(f"Result: {result}")
        
    finally:
        client.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_grpc_client()