"""
gRPC Mock Device Server - SiLA2 Protocol Implementation
"""
import grpc
from concurrent import futures
import logging
from datetime import datetime
import threading
import time

import sila2_basic_pb2 as sila2_pb
import sila2_basic_pb2_grpc as sila2_grpc

logger = logging.getLogger(__name__)

class SiLA2DeviceService(sila2_grpc.SiLA2DeviceServicer):
    """gRPC SiLA2 Device Service Implementation"""
    
    def __init__(self):
        self.devices = {
            "HPLC-01": {"type": "hplc", "location": "Lab-A", "status": "ready"},
            "CENTRIFUGE-01": {"type": "centrifuge", "location": "Lab-B", "status": "busy"},
            "PIPETTE-01": {"type": "pipette", "location": "Lab-A", "status": "ready"}
        }
    
    def ListDevices(self, request, context):
        """List all available devices"""
        devices = []
        for device_id, info in self.devices.items():
            device = sila2_pb.DeviceInfo(
                device_id=device_id,
                device_type=info["type"],
                status=info["status"],
                location=info["location"]
            )
            devices.append(device)
        
        return sila2_pb.ListDevicesResponse(
            devices=devices,
            count=len(devices),
            timestamp=datetime.now().isoformat()
        )
    
    def GetDeviceInfo(self, request, context):
        """Get device information"""
        device_id = request.device_id
        
        if device_id not in self.devices:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Device {device_id} not found")
            return sila2_pb.DeviceInfoResponse()
        
        device_info = self.devices[device_id]
        properties = self._get_device_properties(device_id, device_info["type"])
        
        return sila2_pb.DeviceInfoResponse(
            device_id=device_id,
            status=device_info["status"],
            device_type=device_info["type"],
            properties=properties,
            timestamp=datetime.now().isoformat()
        )
    
    def ExecuteCommand(self, request, context):
        """Execute device command"""
        device_id = request.device_id
        operation = request.operation
        parameters = dict(request.parameters)
        
        if device_id not in self.devices:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Device {device_id} not found")
            return sila2_pb.CommandResponse()
        
        device_info = self.devices[device_id]
        result = self._execute_operation(device_id, device_info["type"], operation, parameters)
        
        return sila2_pb.CommandResponse(
            device_id=device_id,
            operation=operation,
            success=result.get("success", True),
            status=result.get("status", "completed"),
            result=result.get("result", {}),
            timestamp=datetime.now().isoformat()
        )
    
    def _get_device_properties(self, device_id: str, device_type: str) -> dict:
        """Get device-specific properties"""
        if device_type == "hplc":
            return {
                "temperature": "25.0",
                "pressure": "150.0",
                "flow_rate": "1.0",
                "column": "C18"
            }
        elif device_type == "centrifuge":
            return {
                "rpm": "3000",
                "temperature": "4.0",
                "remaining_time": "600"
            }
        elif device_type == "pipette":
            return {
                "tip_attached": "true",
                "volume_range": "0.1-1000μL",
                "current_volume": "0"
            }
        return {}
    
    def _execute_operation(self, device_id: str, device_type: str, operation: str, parameters: dict) -> dict:
        """Execute device-specific operation"""
        if device_type == "hplc" and operation == "start_analysis":
            return {
                "success": True,
                "status": "running",
                "result": {
                    "method": parameters.get("method", "default"),
                    "estimated_time": "1800"
                }
            }
        elif device_type == "centrifuge" and operation == "start_spin":
            return {
                "success": True,
                "status": "spinning",
                "result": {
                    "rpm": parameters.get("rpm", "3000"),
                    "duration": parameters.get("duration", "600")
                }
            }
        elif device_type == "pipette" and operation == "aspirate":
            return {
                "success": True,
                "status": "completed",
                "result": {
                    "volume": parameters.get("volume", "100"),
                    "position": parameters.get("position", "A1")
                }
            }
        
        return {"success": False, "status": "unsupported_operation"}

class GRPCServer:
    """gRPC Server Manager"""
    
    def __init__(self, port=50051):
        self.port = port
        self.server = None
        self.running = False
    
    def start(self):
        """Start gRPC server"""
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        sila2_grpc.add_SiLA2DeviceServicer_to_server(SiLA2DeviceService(), self.server)
        self.server.add_insecure_port(f'[::]:{self.port}')
        self.server.start()
        self.running = True
        logger.info(f"gRPC server started on port {self.port}")
        return self.server
    
    def stop(self):
        """Stop gRPC server"""
        if self.server and self.running:
            self.server.stop(0)
            self.running = False
            logger.info("gRPC server stopped")
    
    def wait_for_termination(self):
        """Wait for server termination"""
        if self.server:
            self.server.wait_for_termination()

def start_grpc_server_background(port=50051):
    """Start gRPC server in background thread"""
    server_manager = GRPCServer(port)
    server = server_manager.start()
    
    def run_server():
        try:
            server_manager.wait_for_termination()
        except KeyboardInterrupt:
            server_manager.stop()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    
    return server_manager

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    server_manager = GRPCServer()
    try:
        server_manager.start()
        print("gRPC server running on port 50051...")
        server_manager.wait_for_termination()
    except KeyboardInterrupt:
        server_manager.stop()
        print("Server stopped")