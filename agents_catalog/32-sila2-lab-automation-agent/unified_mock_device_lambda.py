"""
統一Mock Device Lambda - Phase 3 Step 4 Enhanced
"""
import json
import logging
import os
import boto3
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SiLA2Response:
    @staticmethod
    def device_info(device_id: str, device_type: str, status: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'device_type': device_type,
            'status': status,
            'properties': properties,
            'timestamp': datetime.now().isoformat(),
            'sila2_compliant': True
        }
    
    @staticmethod
    def command_response(device_id: str, operation: str, success: bool, result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'operation': operation,
            'success': success,
            'status': 'completed' if success else 'failed',
            'result': result,
            'timestamp': datetime.now().isoformat(),
            'sila2_compliant': True
        }

class DeviceSimulator:
    def handle_request(self, action: str, device_id: str, event: dict) -> Dict[str, Any]:
        method = getattr(self, f"handle_{action}", None)
        if not method:
            return {'error': f'Unsupported action: {action}'}
        return method(device_id, event)

class EnhancedHPLCSimulator(DeviceSimulator):
    def handle_get_status(self, device_id: str, event: dict) -> Dict[str, Any]:
        properties = {
            'temperature': 25.0,
            'pressure': 150.0,
            'flow_rate': 1.0,
            'column_type': 'C18',
            'mobile_phase': 'ACN/H2O',
            'detector': 'UV-Vis',
            'injection_volume': 20,
            'wavelength': 254
        }
        return SiLA2Response.device_info(device_id, 'HPLC', 'ready', properties)
    
    def handle_start_analysis(self, device_id: str, event: dict) -> Dict[str, Any]:
        result = {
            'estimated_time': 1800,
            'method': event.get('method', 'standard'),
            'sample_volume': event.get('volume', 20),
            'run_id': f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'gradient_profile': 'linear',
            'detection_wavelength': event.get('wavelength', 254)
        }
        return SiLA2Response.command_response(device_id, 'start_analysis', True, result)

class EnhancedCentrifugeSimulator(DeviceSimulator):
    def handle_get_status(self, device_id: str, event: dict) -> Dict[str, Any]:
        properties = {
            'rpm': 3000,
            'temperature': 4.0,
            'remaining_time': 600,
            'rotor_type': 'fixed_angle',
            'max_rpm': 15000,
            'capacity': '24x1.5ml',
            'acceleration_profile': 'fast',
            'brake_setting': 'medium'
        }
        return SiLA2Response.device_info(device_id, 'Centrifuge', 'busy', properties)
    
    def handle_start_spin(self, device_id: str, event: dict) -> Dict[str, Any]:
        result = {
            'rpm': event.get('rpm', 3000),
            'duration': event.get('duration', 600),
            'temperature': event.get('temperature', 4.0),
            'acceleration': 'fast',
            'spin_id': f"SPIN_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'rcf_value': int(event.get('rpm', 3000) * 1.12 * 0.00001118),
            'brake_profile': event.get('brake', 'medium')
        }
        return SiLA2Response.command_response(device_id, 'start_spin', True, result)

class EnhancedPipetteSimulator(DeviceSimulator):
    def handle_get_status(self, device_id: str, event: dict) -> Dict[str, Any]:
        properties = {
            'tip_attached': True,
            'volume_range': '0.1-1000μL',
            'current_volume': 0,
            'tip_type': 'standard',
            'calibration_date': '2024-01-15',
            'accuracy': '±0.5%',
            'precision': '±0.3%',
            'channels': 8
        }
        return SiLA2Response.device_info(device_id, 'Pipette', 'ready', properties)
    
    def handle_aspirate(self, device_id: str, event: dict) -> Dict[str, Any]:
        volume = event.get('volume', 100)
        result = {
            'volume': volume,
            'position': event.get('position', 'A1'),
            'speed': event.get('speed', 'normal'),
            'actual_volume': volume * 0.998,
            'operation_id': f"ASP_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'tip_depth': event.get('tip_depth', 2),
            'pre_wet': event.get('pre_wet', False)
        }
        return SiLA2Response.command_response(device_id, 'aspirate', True, result)

class EnhancedDeviceSimulator:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb') if os.getenv('AWS_REGION') else None
        self.registry_table = os.getenv('DEVICE_REGISTRY_TABLE', 'sila2-device-registry-dev')
        
    def get_device_registry(self) -> Dict[str, Any]:
        devices = [
            {'device_id': 'HPLC-01', 'device_type': 'HPLC', 'status': 'ready', 'location': 'Lab-A', 'vendor': 'Agilent'},
            {'device_id': 'CENTRIFUGE-01', 'device_type': 'Centrifuge', 'status': 'busy', 'location': 'Lab-B', 'vendor': 'Eppendorf'},
            {'device_id': 'PIPETTE-01', 'device_type': 'Pipette', 'status': 'ready', 'location': 'Lab-C', 'vendor': 'Gilson'}
        ]
        return {
            'devices': devices, 
            'count': len(devices), 
            'timestamp': datetime.now().isoformat(),
            'registry_mode': 'enhanced'
        }

class HPLCSimulator(DeviceSimulator):
    def handle_get_status(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'status': 'ready',
            'temperature': 25.0,
            'pressure': 150.0,
            'flow_rate': 1.0,
            'type': 'HPLC'
        }
    
    def handle_start_analysis(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'operation': 'analysis_started',
            'estimated_time': 1800,
            'status': 'running'
        }

class CentrifugeSimulator(DeviceSimulator):
    def handle_get_status(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'status': 'busy',
            'rpm': 3000,
            'temperature': 4.0,
            'remaining_time': 600,
            'type': 'Centrifuge'
        }
    
    def handle_start_spin(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'operation': 'spin_started',
            'rpm': event.get('rpm', 3000),
            'duration': event.get('duration', 600)
        }

class PipetteSimulator(DeviceSimulator):
    def handle_get_status(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'status': 'ready',
            'tip_attached': True,
            'volume_range': '0.1-1000μL',
            'type': 'Pipette'
        }
    
    def handle_aspirate(self, device_id: str, event: dict) -> Dict[str, Any]:
        return {
            'device_id': device_id,
            'operation': 'aspirate_completed',
            'volume': event.get('volume', 100),
            'position': event.get('position', 'A1')
        }

class UnifiedMockDeviceLambda:
    def __init__(self):
        self.enhanced_simulators = {
            'hplc': EnhancedHPLCSimulator(),
            'centrifuge': EnhancedCentrifugeSimulator(),
            'pipette': EnhancedPipetteSimulator()
        }
        
        self.device_simulators = {
            'hplc': HPLCSimulator(),
            'centrifuge': CentrifugeSimulator(),
            'pipette': PipetteSimulator()
        }
        
        self.enhanced_device = EnhancedDeviceSimulator()
        self.sila2_mode = os.getenv('SILA2_COMPLIANCE', 'true').lower() == 'true'
    
    def lambda_handler(self, event, context):
        try:
            if event.get('action') == 'list_devices':
                registry = self.enhanced_device.get_device_registry()
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'success': True,
                        'result': registry,
                        'enhanced_mode': True
                    })
                }
            
            if 'pathParameters' in event:
                device_type = event['pathParameters'].get('device_type')
                device_id = event['pathParameters'].get('device_id')
                action = event['pathParameters'].get('action')
            else:
                device_type = event.get('device_type')
                device_id = event.get('device_id')
                action = event.get('action')
            
            if not all([device_type, device_id, action]):
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Missing required parameters'})
                }
            
            simulators = self.enhanced_simulators if self.sila2_mode else self.device_simulators
            simulator = simulators.get(device_type.lower())
            
            if not simulator:
                return {
                    'statusCode': 404,
                    'body': json.dumps({'error': f'Device type {device_type} not supported'})
                }
            
            result = simulator.handle_request(action, device_id, event)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'result': result,
                    'enhanced_mode': self.sila2_mode,
                    'timestamp': datetime.now().isoformat()
                })
            }
            
        except Exception as e:
            logger.error(f"Lambda handler error: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }

unified_lambda = UnifiedMockDeviceLambda()
lambda_handler = unified_lambda.lambda_handler