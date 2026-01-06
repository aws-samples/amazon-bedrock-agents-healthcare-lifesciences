import grpc
import threading
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'proto'))
import sila2_streaming_pb2
import sila2_streaming_pb2_grpc

from data_buffer import DataBuffer
from event_handler import handle_sila2_event

class GRPCStreamClient:
    def __init__(self, grpc_server: str, device_id: str, buffer: DataBuffer):
        self.grpc_server = grpc_server
        self.device_id = device_id
        self.buffer = buffer
        self.running = False
        self.reconnect_delay = 5
        
    def start_streaming(self):
        self.running = True
        thread1 = threading.Thread(target=self._temperature_stream_loop, daemon=True)
        thread1.start()
        thread2 = threading.Thread(target=self._event_stream_loop, daemon=True)
        thread2.start()
        
    def _temperature_stream_loop(self):
        while self.running:
            channel = None
            try:
                channel = grpc.insecure_channel(self.grpc_server)
                stub = sila2_streaming_pb2_grpc.SiLA2DeviceStub(channel)
                request = sila2_streaming_pb2.SubscribeRequest(device_id=self.device_id)
                print(f"[Stream] Connecting to {self.grpc_server} for temperature...", flush=True)
                
                for response in stub.SubscribeTemperature(request):
                    if not self.running:
                        break
                    print(f"[Stream] Received temp={response.temperature:.1f}°C target={response.target_temperature:.1f}°C", flush=True)
                    
                    # heating_statusを推定
                    heating_status = "idle"
                    if response.target_temperature > 0:
                        if abs(response.temperature - response.target_temperature) < 0.5:
                            heating_status = "completed"
                        else:
                            heating_status = "heating"
                    
                    self.buffer.add_data(
                        device_id=self.device_id,
                        temperature_data={
                            'current_temp': response.temperature,
                            'target_temp': response.target_temperature,
                            'heating_status': heating_status,
                            'scenario_mode': response.scenario_mode,
                            'elapsed_seconds': response.elapsed_seconds
                        }
                    )
            except grpc.RpcError as e:
                print(f"[Stream] Temperature stream error: {e}, reconnecting in {self.reconnect_delay}s...", flush=True)
                time.sleep(self.reconnect_delay)
            except Exception as e:
                print(f"[Stream] Unexpected error: {e}, reconnecting in {self.reconnect_delay}s...", flush=True)
                time.sleep(self.reconnect_delay)
            finally:
                if channel:
                    channel.close()
    
    def _event_stream_loop(self):
        while self.running:
            channel = None
            try:
                channel = grpc.insecure_channel(self.grpc_server)
                stub = sila2_streaming_pb2_grpc.SiLA2DeviceStub(channel)
                request = sila2_streaming_pb2.EventRequest(device_id=self.device_id)
                print(f"[Stream] Connecting to {self.grpc_server} for events...", flush=True)
                
                for event in stub.SubscribeEvents(request):
                    if not self.running:
                        break
                    print(f"[Stream] Received event: {event.event_type}", flush=True)
                    asyncio.run(handle_sila2_event(
                        device_id=self.device_id,
                        event_data={
                            'event_type': event.event_type,
                            'value': event.temperature
                        }
                    ))
            except grpc.RpcError as e:
                print(f"[Stream] Event stream error: {e}, reconnecting in {self.reconnect_delay}s...", flush=True)
                time.sleep(self.reconnect_delay)
            except Exception as e:
                print(f"[Stream] Unexpected error: {e}, reconnecting in {self.reconnect_delay}s...", flush=True)
                time.sleep(self.reconnect_delay)
            finally:
                if channel:
                    channel.close()
