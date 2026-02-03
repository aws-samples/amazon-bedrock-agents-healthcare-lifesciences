from sila2.client import SilaClient
import logging
import time
import threading
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class SiLA2Bridge:
    def __init__(self, host='devices', port=50051):
        self.host = host
        self.port = port
        self.client = None
        self._connect()
    
    def _connect(self):
        """Connect with simple retry for demo"""
        for attempt in range(3):
            try:
                self.client = SilaClient(self.host, self.port, insecure=True)
                logger.info(f"Connected to SiLA2 server at {self.host}:{self.port}")
                return
            except Exception as e:
                if attempt < 2:
                    logger.warning(f"Connection attempt {attempt+1} failed, retrying...")
                    time.sleep(2)
                else:
                    logger.error(f"Failed to connect: {e}")
                    raise
    
    def list_devices(self):
        """List all devices"""
        return self.client.DeviceManagement.ListDevices()
    
    def get_device_info(self, device_id):
        """Get device information"""
        return self.client.DeviceManagement.GetDeviceInfo(DeviceId=device_id)
    
    def get_device_status(self, device_id):
        """Get device status"""
        return self.client.DeviceManagement.GetDeviceStatus(DeviceId=device_id)
    
    def set_temperature(self, target_temperature):
        """Set temperature and monitor progress (SiLA2 standard)"""
        command_instance = self.client.TemperatureController.SetTemperature(
            TargetTemperature=target_temperature
        )
        # Store command instance for later status queries
        if not hasattr(self, '_command_instances'):
            self._command_instances = {}
        self._command_instances[str(command_instance.execution_uuid)] = command_instance
        
        # Monitor IntermediateResponse in background thread (SiLA2 standard)
        thread = threading.Thread(
            target=self._monitor_temperature_progress,
            args=(command_instance, target_temperature),
            daemon=True
        )
        thread.start()
        
        return command_instance
    
    def _monitor_temperature_progress(self, command_instance, target_temperature):
        """Monitor SetTemperature IntermediateResponse for PercentComplete (SiLA2 standard)"""
        from event_handler import handle_sila2_event
        
        try:
            # Subscribe to intermediate responses (SiLA2 standard)
            subscription = command_instance.subscribe_to_intermediate_responses()
            
            for progress in subscription:
                percent = progress.Progress.PercentComplete
                current_temp = progress.Progress.CurrentTemperature
                elapsed = progress.Progress.ElapsedSeconds
                
                logger.debug(f"Temperature progress: {percent}% ({current_temp:.1f}°C)")
                
                # Temperature reached when PercentComplete == 100 (SiLA2 standard)
                if percent >= 100:
                    logger.info(f"Temperature reached: {current_temp:.1f}°C (PercentComplete: 100%)")
                    asyncio.run(handle_sila2_event('device-1', {
                        'event_type': 'TemperatureReached',
                        'value': {
                            'CurrentTemperature': current_temp,
                            'TargetTemperature': target_temperature,
                            'ElapsedSeconds': elapsed,
                            'PercentComplete': percent
                        }
                    }))
                    break
                    
        except Exception as e:
            logger.error(f"Failed to monitor temperature progress: {e}")
    
    def get_temperature_progress(self, command_uuid):
        """Get temperature setting progress (generator)"""
        return self.client.TemperatureController.SetTemperature_Info(command_uuid)
    
    def get_temperature_result(self, command_uuid):
        """Get final temperature result"""
        return self.client.TemperatureController.SetTemperature_Result(command_uuid)
    
    def get_current_temperature(self):
        """Get current temperature"""
        prop = self.client.TemperatureController.CurrentTemperature
        value = prop.get()
        return float(value) if value is not None else 0.0
    
    def subscribe_temperature(self):
        """Subscribe to temperature updates (returns first value for MCP compatibility)"""
        prop = self.client.TemperatureController.CurrentTemperature
        subscription = prop.subscribe()
        # Return first value for MCP (streaming not yet supported)
        first_value = next(subscription)
        return {"temperature": float(first_value), "note": "Streaming subscription active"}
    
    def get_heating_status(self):
        """Get heating status"""
        prop = self.client.TemperatureController.HeatingStatus
        value = prop.get()
        # Convert to dict if needed
        if hasattr(value, '__dict__'):
            return value.__dict__
        return value if isinstance(value, dict) else {'status': str(value)}
    
    def abort_experiment(self, reason="Manual abort"):
        """Abort experiment (SiLA2 Unobservable command - returns immediately)"""
        # AbortExperiment is Unobservable - returns result immediately
        result = self.client.TemperatureController.AbortExperiment()
        
        # Send completion event immediately
        thread = threading.Thread(
            target=self._send_abort_event,
            args=(reason,),
            daemon=True
        )
        thread.start()
        
        return result
    
    def _send_abort_event(self, reason):
        """Send abort completion event to SNS"""
        from event_handler import handle_sila2_event
        
        try:
            # Get current temperature as final temperature
            final_temp = self.get_current_temperature()
            
            logger.info(f"Abort completed, FinalTemp={final_temp}°C")
            
            # Send completion event to SNS → Lambda → AgentCore Memory
            asyncio.run(handle_sila2_event('device-1', {
                'event_type': 'ExperimentAborted',
                'value': {
                    'Success': True,
                    'FinalTemperature': final_temp,
                    'Reason': reason,
                    'Timestamp': datetime.now().isoformat()
                }
            }))
            
        except Exception as e:
            logger.error(f"Failed to send abort event: {e}")
    
    def get_task_status(self, task_id):
        """Get task status from stored command instance"""
        if not hasattr(self, '_command_instances'):
            return {"error": "No command instances found"}
        
        command_instance = self._command_instances.get(task_id)
        if not command_instance:
            return {"error": f"Command instance {task_id} not found"}
        
        return {
            "status": str(command_instance.status),
            "progress": command_instance.progress,
            "done": command_instance.done,
            "estimated_remaining_time": str(command_instance.estimated_remaining_time)
        }
    
    def get_task_info(self, task_id):
        """Get task information from stored command instance"""
        if not hasattr(self, '_command_instances'):
            return {"error": "No command instances found"}
        
        command_instance = self._command_instances.get(task_id)
        if not command_instance:
            return {"error": f"Command instance {task_id} not found"}
        
        return {
            "execution_uuid": str(command_instance.execution_uuid),
            "status": str(command_instance.status),
            "progress": command_instance.progress,
            "done": command_instance.done,
            "estimated_remaining_time": str(command_instance.estimated_remaining_time),
            "lifetime_of_execution": str(command_instance.lifetime_of_execution)
        }
