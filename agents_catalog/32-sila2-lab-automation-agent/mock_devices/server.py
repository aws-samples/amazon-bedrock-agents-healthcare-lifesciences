#!/usr/bin/env python3
import grpc
from concurrent import futures
import sys
import os
from datetime import datetime
import uuid
import threading
import time
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'proto'))
import sila2_basic_pb2
import sila2_basic_pb2_grpc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'proto'))
import sila2_streaming_pb2
import sila2_streaming_pb2_grpc

from temperature_controller import TemperatureController

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

class MockDeviceService(sila2_basic_pb2_grpc.SiLA2DeviceServicer):
    def __init__(self):
        self.task_manager = TaskManager()
        self.temperature_controller = TemperatureController()
    
    def ListDevices(self, request, context):
        devices = [
            sila2_basic_pb2.DeviceInfo(
                device_id=dev_id,
                device_type=dev['type'],
                status='ready',
                location=dev['location']
            )
            for dev_id, dev in DEVICES.items()
        ]
        return sila2_basic_pb2.ListDevicesResponse(
            devices=devices,
            count=len(devices),
            timestamp=datetime.now().isoformat()
        )
    
    def GetDeviceInfo(self, request, context):
        dev = DEVICES.get(request.device_id, DEVICES['hplc'])
        return sila2_basic_pb2.DeviceInfoResponse(
            device_id=request.device_id,
            status='ready',
            device_type=dev['type'],
            properties=dev['props'],
            timestamp=datetime.now().isoformat()
        )
    
    def ExecuteCommand(self, request, context):
        dev = DEVICES.get(request.device_id, DEVICES['hplc'])
        
        if request.operation == 'start_task':
            command = request.parameters.get('command', 'unknown')
            params = {k: v for k, v in request.parameters.items() if k != 'command'}
            print(f"[START_TASK] device={request.device_id}, command={command}, params={params}", flush=True)
            
            # Handle SetTemperature command (both formats)
            if command in ['SetTemperature', 'set_temperature']:
                # Support both 'target_temperature' and 'temperature' parameter names
                target = float(params.get('target_temperature') or params.get('temperature', 25))
                print(f"[TEMPERATURE] Setting target to {target}°C", flush=True)
                self.temperature_controller.toggle_scenario()
                self.temperature_controller.set_temperature(target)
                DEVICES[request.device_id]['props']['temperature'] = str(target)
            
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
        
        if request.operation.startswith('get_'):
            prop_name = request.operation[4:]
            if prop_name == 'temperature':
                current = self.temperature_controller.get_current_temperature()
                DEVICES[request.device_id]['props']['temperature'] = str(current)
                return sila2_basic_pb2.CommandResponse(
                    device_id=request.device_id,
                    operation=request.operation,
                    success=True,
                    status='completed',
                    result={'value': str(current), 'unit': 'C'},
                    timestamp=datetime.now().isoformat()
                )
            elif prop_name in dev['props']:
                return sila2_basic_pb2.CommandResponse(
                    device_id=request.device_id,
                    operation=request.operation,
                    success=True,
                    status='completed',
                    result={'value': dev['props'][prop_name], 'unit': ''},
                    timestamp=datetime.now().isoformat()
                )
        
        if request.operation.startswith('set_'):
            prop_name = request.operation[4:]
            if prop_name == 'temperature':
                target = float(request.parameters.get('value', 25))
                self.temperature_controller.toggle_scenario()
                self.temperature_controller.set_temperature(target)
                DEVICES[request.device_id]['props']['temperature'] = str(target)
                return sila2_basic_pb2.CommandResponse(
                    device_id=request.device_id,
                    operation=request.operation,
                    success=True,
                    status='heating',
                    result={'value': str(target), 'message': 'Heating started'},
                    timestamp=datetime.now().isoformat()
                )
            elif prop_name in dev['props']:
                dev['props'][prop_name] = request.parameters.get('value', dev['props'][prop_name])
                return sila2_basic_pb2.CommandResponse(
                    device_id=request.device_id,
                    operation=request.operation,
                    success=True,
                    status='completed',
                    result={'value': dev['props'][prop_name], 'message': f'{prop_name} set successfully'},
                    timestamp=datetime.now().isoformat()
                )
        
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

class SiLA2StreamingService(sila2_streaming_pb2_grpc.SiLA2DeviceServicer):
    def __init__(self, temperature_controller):
        self.temperature_controller = temperature_controller
    
    async def SubscribeTemperature(self, request, context):
        device_id = request.device_id
        
        while True:
            temp = self.temperature_controller.get_current_temperature()
            target = self.temperature_controller.target_temp or 0.0
            elapsed = 0
            start_time = ""
            
            if self.temperature_controller.start_time:
                elapsed = int(time.time() - self.temperature_controller.start_time)
                start_time = datetime.fromtimestamp(self.temperature_controller.start_time).isoformat()
            
            yield sila2_streaming_pb2.TemperatureUpdate(
                device_id=device_id,
                temperature=temp,
                target_temperature=target,
                elapsed_seconds=elapsed,
                start_time=start_time,
                timestamp=datetime.utcnow().isoformat(),
                scenario_mode=self.temperature_controller.scenario_mode
            )
            
            await asyncio.sleep(5)
    
    async def SubscribeEvents(self, request, context):
        device_id = request.device_id
        last_target_reached = False
        malfunction_emitted = False
        
        while True:
            target_reached = self.temperature_controller.check_target_reached()
            
            if target_reached and not last_target_reached:
                duration = 0
                if self.temperature_controller.start_time:
                    duration = int(time.time() - self.temperature_controller.start_time)
                
                print(f"[EVENT] TEMPERATURE_REACHED: {self.temperature_controller.get_current_temperature():.1f}°C in {duration}s", flush=True)
                
                yield sila2_streaming_pb2.DeviceEvent(
                    device_id=device_id,
                    event_type="TEMPERATURE_REACHED",
                    temperature=self.temperature_controller.get_current_temperature(),
                    target_temperature=self.temperature_controller.target_temp,
                    duration_seconds=duration,
                    timestamp=datetime.utcnow().isoformat()
                )
                
                self.temperature_controller.stop_heating()
                
                last_target_reached = True
                malfunction_emitted = False
            elif not target_reached:
                last_target_reached = False
            
            if (self.temperature_controller.scenario_mode == "scenario_2" and 
                self.temperature_controller.is_heating and
                self.temperature_controller.start_time and
                not malfunction_emitted):
                
                elapsed = time.time() - self.temperature_controller.start_time
                if elapsed > 300:
                    yield sila2_streaming_pb2.DeviceEvent(
                        device_id=device_id,
                        event_type="HEATER_MALFUNCTION",
                        temperature=self.temperature_controller.get_current_temperature(),
                        expected_rate=10.0,
                        actual_rate=self.temperature_controller.get_heating_rate(),
                        timestamp=datetime.utcnow().isoformat()
                    )
                    malfunction_emitted = True
            
            await asyncio.sleep(1)

async def serve():
    server = grpc.aio.server()
    
    mock_service = MockDeviceService()
    sila2_basic_pb2_grpc.add_SiLA2DeviceServicer_to_server(mock_service, server)
    
    streaming_service = SiLA2StreamingService(mock_service.temperature_controller)
    sila2_streaming_pb2_grpc.add_SiLA2DeviceServicer_to_server(streaming_service, server)
    
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    
    await server.start()
    print("Mock Device Server started on port 50051", flush=True)
    print("gRPC Streaming enabled", flush=True)
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())
