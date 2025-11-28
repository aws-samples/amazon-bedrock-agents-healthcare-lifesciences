#!/usr/bin/env python3
import grpc
from concurrent import futures
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'proto'))
import sila2_basic_pb2
import sila2_basic_pb2_grpc

class MockDeviceService(sila2_basic_pb2_grpc.SiLA2DeviceServicer):
    DEVICES = {
        'hplc': {
            'type': 'HPLC',
            'location': 'Lab-A',
            'props': {'temperature': '25', 'pressure': '150', 'flow_rate': '1.0'}
        },
        'centrifuge': {
            'type': 'Centrifuge',
            'location': 'Lab-B',
            'props': {'speed': '3000', 'temperature': '4', 'time': '10'}
        },
        'pipette': {
            'type': 'Pipette',
            'location': 'Lab-C',
            'props': {'volume': '100', 'speed': 'medium', 'tip_type': 'standard'}
        }
    }
    
    def ListDevices(self, request, context):
        devices = [
            sila2_basic_pb2.DeviceInfo(
                device_id=dev_id,
                device_type=dev['type'],
                status='ready',
                location=dev['location']
            )
            for dev_id, dev in self.DEVICES.items()
        ]
        return sila2_basic_pb2.ListDevicesResponse(
            devices=devices,
            count=len(devices),
            timestamp=datetime.now().isoformat()
        )
    
    def GetDeviceInfo(self, request, context):
        dev = self.DEVICES.get(request.device_id, self.DEVICES['hplc'])
        return sila2_basic_pb2.DeviceInfoResponse(
            device_id=request.device_id,
            status='ready',
            device_type=dev['type'],
            properties=dev['props'],
            timestamp=datetime.now().isoformat()
        )
    
    def ExecuteCommand(self, request, context):
        dev = self.DEVICES.get(request.device_id, self.DEVICES['hplc'])
        result = {'status': 'completed', 'device_type': dev['type']}
        result.update(request.parameters)
        
        return sila2_basic_pb2.CommandResponse(
            device_id=request.device_id,
            operation=request.operation,
            success=True,
            status='completed',
            result=result,
            timestamp=datetime.now().isoformat()
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    sila2_basic_pb2_grpc.add_SiLA2DeviceServicer_to_server(MockDeviceService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Mock Device Server started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
