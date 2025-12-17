#!/usr/bin/env python3
import grpc
from concurrent import futures
import sys
import os
from datetime import datetime
import uuid
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'proto'))
import sila2_basic_pb2
import sila2_basic_pb2_grpc

class TaskManager:
    def __init__(self):
        self.tasks = {}
    
    def start_task(self, device_id, command, params):
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {"progress": 0, "status": "running", "message": "Task started"}
        threading.Thread(target=self._run_task, args=(task_id,), daemon=True).start()
        return task_id
    
    def get_task_status(self, task_id):
        return self.tasks.get(task_id, {"progress": 0, "status": "not_found", "message": "Task not found"})
    
    def _run_task(self, task_id):
        for i in range(0, 101, 10):
            self.tasks[task_id] = {"progress": i, "status": "running", "message": f"Processing {i}%"}
            time.sleep(2.0)
        self.tasks[task_id] = {"progress": 100, "status": "completed", "message": "Task completed"}

class MockDeviceService(sila2_basic_pb2_grpc.SiLA2DeviceServicer):
    def __init__(self):
        self.task_manager = TaskManager()
    
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
        
        # Handle task operations
        if request.operation == 'start_task':
            command = request.parameters.get('command', 'unknown')
            params = {k: v for k, v in request.parameters.items() if k != 'command'}
            task_id = self.task_manager.start_task(request.device_id, command, params)
            return sila2_basic_pb2.CommandResponse(
                device_id=request.device_id,
                operation=request.operation,
                success=True,
                status='running',
                result={'task_id': task_id, 'status': 'running'},
                timestamp=datetime.now().isoformat()
            )
        elif request.operation == 'get_task_status':
            task_id = request.parameters.get('task_id', '')
            status = self.task_manager.get_task_status(task_id)
            return sila2_basic_pb2.CommandResponse(
                device_id=request.device_id,
                operation=request.operation,
                success=True,
                status=status['status'],
                result={'progress': str(status['progress']), 'status': status['status'], 'message': status['message']},
                timestamp=datetime.now().isoformat()
            )
        
        # Handle property get operations
        if request.operation.startswith('get_'):
            prop_name = request.operation[4:]  # Remove 'get_' prefix
            if prop_name in dev['props']:
                return sila2_basic_pb2.CommandResponse(
                    device_id=request.device_id,
                    operation=request.operation,
                    success=True,
                    status='completed',
                    result={'value': dev['props'][prop_name], 'unit': 'C' if prop_name == 'temperature' else ''},
                    timestamp=datetime.now().isoformat()
                )
        
        # Handle property set operations
        if request.operation.startswith('set_'):
            prop_name = request.operation[4:]  # Remove 'set_' prefix
            if prop_name in dev['props']:
                dev['props'][prop_name] = request.parameters.get('value', dev['props'][prop_name])
                return sila2_basic_pb2.CommandResponse(
                    device_id=request.device_id,
                    operation=request.operation,
                    success=True,
                    status='completed',
                    result={'value': dev['props'][prop_name], 'message': f'{prop_name} set successfully'},
                    timestamp=datetime.now().isoformat()
                )
        
        # Normal command execution
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
    service = MockDeviceService()
    sila2_basic_pb2_grpc.add_SiLA2DeviceServicer_to_server(service, server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Mock Device Server started on port 50051")
    print("TaskManager initialized")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
