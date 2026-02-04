"""SiLA2 Stream Client using generated client library"""
import sys
import os
import threading
import time
import logging
import asyncio

devices_path = os.path.join(os.path.dirname(__file__), 'devices_generated')
if not os.path.exists(devices_path):
    devices_path = os.path.join(os.path.dirname(__file__), '..', 'devices', 'generated')
sys.path.insert(0, devices_path)

from lab_devices.generated.client import Client
from data_buffer import DataBuffer
from event_handler import handle_sila2_event

logger = logging.getLogger(__name__)

class SiLA2StreamClient:
    def __init__(self, host: str, port: int, device_id: str, buffer: DataBuffer):
        self.host = host
        self.port = port
        self.device_id = device_id
        self.buffer = buffer
        self.running = False
        self.client = None
        
    def start_streaming(self):
        """Start streaming temperature data and events"""
        self.running = True
        temp_thread = threading.Thread(target=self._temperature_stream_loop, daemon=True)
        temp_thread.start()
        event_thread = threading.Thread(target=self._event_stream_loop, daemon=True)
        event_thread.start()
        logger.info(f"Started streaming for {self.device_id}")
        
    def _temperature_stream_loop(self):
        """Temperature streaming loop"""
        while self.running:
            try:
                if not self.client:
                    logger.info(f"Connecting to {self.host}:{self.port}")
                    self.client = Client(self.host, self.port, insecure=True)
                
                temp_subscription = self.client.TemperatureController.CurrentTemperature.subscribe()
                logger.info(f"Subscribed to temperature stream for {self.device_id}")
                
                for temp_value in temp_subscription:
                    if not self.running:
                        break
                    
                    try:
                        target_temp = self.client.TemperatureController.TargetTemperature.get()
                    except:
                        target_temp = 0.0
                    
                    try:
                        status = self.client.TemperatureController.HeatingStatus.get()
                        scenario_mode = status.ScenarioMode
                        elapsed_seconds = status.ElapsedSeconds
                    except:
                        scenario_mode = 'unknown'
                        elapsed_seconds = 0
                    
                    heating_status = "idle"
                    if target_temp > 0:
                        diff = abs(temp_value - target_temp)
                        if diff < 0.5:
                            heating_status = "completed"
                        else:
                            heating_status = "heating"
                    
                    temp_data = {
                        'current_temp': temp_value,
                        'target_temp': target_temp,
                        'heating_status': heating_status,
                        'scenario_mode': scenario_mode,
                        'elapsed_seconds': elapsed_seconds
                    }
                    
                    self.buffer.add_data(self.device_id, temp_data)
                    logger.debug(f"[{self.device_id}] {temp_value:.1f}°C -> {target_temp:.1f}°C ({heating_status}, {scenario_mode})")
                    
            except Exception as e:
                logger.error(f"Temperature stream error for {self.device_id}: {e}")
                if self.client:
                    self.client = None
                time.sleep(5)
    
    def _event_stream_loop(self):
        """Deprecated: Temperature reached detection now handled by sila2_bridge.py
        via SetTemperature IntermediateResponse monitoring (SiLA2 standard)"""
        logger.info(f"Event stream loop disabled for {self.device_id} - using IntermediateResponse monitoring")
        # Keep thread alive but do nothing
        while self.running:
            time.sleep(10)
                
    def stop(self):
        """Stop streaming"""
        self.running = False
        if self.client:
            self.client = None
