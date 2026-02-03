"""Mock gRPC Server for Local Testing"""
import grpc
from concurrent import futures
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import sila2_basic_pb2
import sila2_basic_pb2_grpc
from datetime import datetime


class MockSiLA2Device(sila2_basic_pb2_grpc.SiLA2DeviceServicer):
    def __init__(self, device_id, device_type):
        self.device_id = device_id
        self.device_type = device_type
    
    def GetDeviceInfo(self, request, context):
        return sila2_basic_pb2.DeviceInfoResponse(
            device_id=self.device_id,
            status='ready',
            device_type=self.device_type,
            properties={'location': 'lab-1'},
            timestamp=datetime.now().isoformat()
        )
    
    def ExecuteCommand(self, request, context):
        return sila2_basic_pb2.CommandResponse(
            device_id=request.device_id,
            operation=request.operation,
            success=True,
            status='completed',
            result={'message': f'{request.operation} executed'},
            timestamp=datetime.now().isoformat()
        )
    
    def ListDevices(self, request, context):
        return sila2_basic_pb2.ListDevicesResponse(
            devices=[sila2_basic_pb2.DeviceInfo(
                device_id=self.device_id,
                device_type=self.device_type,
                status='ready',
                location='lab-1'
            )],
            count=1,
            timestamp=datetime.now().isoformat()
        )


def serve(port, device_id, device_type):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sila2_basic_pb2_grpc.add_SiLA2DeviceServicer_to_server(
        MockSiLA2Device(device_id, device_type), server
    )
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Mock {device_type} server started on port {port}")
    server.wait_for_termination()


if __name__ == '__main__':
    import threading
    
    devices = [
        (50051, 'hplc', 'HPLC'),
        (50052, 'centrifuge', 'Centrifuge'),
        (50053, 'pipette', 'Pipette')
    ]
    
    threads = []
    for port, device_id, device_type in devices:
        t = threading.Thread(target=serve, args=(port, device_id, device_type), daemon=True)
        t.start()
        threads.append(t)
    
    print("All mock servers running. Press Ctrl+C to stop.")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nShutting down...")
