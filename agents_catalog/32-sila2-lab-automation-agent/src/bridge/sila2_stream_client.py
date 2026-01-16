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
        """HeatingStatus property monitoring loop (SiLA2 standard)"""
        last_is_heating = None
        
        while self.running:
            try:
                if not self.client:
                    time.sleep(1)
                    continue
                
                # Subscribe to HeatingStatus property (SiLA2 standard)
                status_subscription = self.client.TemperatureController.HeatingStatus.subscribe()
                logger.info(f"Subscribed to HeatingStatus for {self.device_id}")
                
                for status_data in status_subscription:
                    if not self.running:
                        break
                    
                    is_heating = status_data.IsHeating
                    
                    # Detect heating→idle transition
                    if last_is_heating and not is_heating:
                        # Check if target temperature was reached
                        try:
                            current_temp = self.client.TemperatureController.CurrentTemperature.get()
                            target_temp = self.client.TemperatureController.TargetTemperature.get()
                            temp_diff = abs(current_temp - target_temp)
                            
                            # Only send TemperatureReached if within 0.5°C of target
                            if temp_diff < 0.5:
                                logger.info(f"[{self.device_id}] Temperature reached (IsHeating: true→false, {current_temp:.1f}°C ≈ {target_temp:.1f}°C)")
                                asyncio.run(handle_sila2_event(self.device_id, {
                                    'event_type': 'TemperatureReached',
                                    'value': {
                                        'IsHeating': status_data.IsHeating,
                                        'ElapsedSeconds': status_data.ElapsedSeconds,
                                        'ScenarioMode': status_data.ScenarioMode,
                                        'CurrentTemperature': current_temp,
                                        'TargetTemperature': target_temp
                                    }
                                }))
                            else:
                                logger.info(f"[{self.device_id}] Heating stopped but target not reached (IsHeating: true→false, {current_temp:.1f}°C vs {target_temp:.1f}°C)")
                        except Exception as e:
                            logger.error(f"Failed to check temperature: {e}")
                    
                    last_is_heating = is_heating
                    
            except Exception as e:
                logger.error(f"HeatingStatus monitoring error for {self.device_id}: {e}")
                time.sleep(5)
                
    def stop(self):
        """Stop streaming"""
        self.running = False
        if self.client:
            self.client = None
