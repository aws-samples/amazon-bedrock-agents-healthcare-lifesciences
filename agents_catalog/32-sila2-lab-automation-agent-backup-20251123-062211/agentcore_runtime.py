"""
AgentCore Runtime for SiLA2 Lab Automation Agent
"""
import json
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AgentCoreRuntime:
    """AgentCore Runtime for SiLA2 Lab Automation"""
    
    def __init__(self):
        self.gateway_tools_arn = os.environ.get('GATEWAY_TOOLS_ARN')
        self.protocol_bridge_arn = os.environ.get('PROTOCOL_BRIDGE_ARN')
        self.environment = os.environ.get('ENVIRONMENT', 'dev')
    
    def handle_agent_request(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle AgentCore agent request"""
        try:
            # Parse request
            request_type = event.get('requestType', 'unknown')
            payload = event.get('payload', {})
            
            if request_type == 'list_devices':
                return self.handle_list_devices(payload)
            elif request_type == 'device_status':
                return self.handle_device_status(payload)
            elif request_type == 'device_command':
                return self.handle_device_command(payload)
            elif request_type == 'start_measurement':
                return self.handle_start_measurement(payload)
            elif request_type == 'stop_measurement':
                return self.handle_stop_measurement(payload)
            else:
                return {
                    'success': False,
                    'error': f'Unknown request type: {request_type}',
                    'available_types': [
                        'list_devices', 'device_status', 'device_command',
                        'start_measurement', 'stop_measurement'
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error in handle_agent_request: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_list_devices(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list devices request"""
        return {
            'success': True,
            'action': 'list_devices',
            'devices': [
                {
                    'device_id': 'HPLC-01',
                    'type': 'HPLC',
                    'status': 'ready',
                    'location': 'Lab-A'
                },
                {
                    'device_id': 'CENTRIFUGE-01',
                    'type': 'Centrifuge',
                    'status': 'idle',
                    'location': 'Lab-B'
                },
                {
                    'device_id': 'PIPETTE-01',
                    'type': 'Pipette',
                    'status': 'ready',
                    'location': 'Lab-A'
                }
            ],
            'count': 3,
            'source': 'agentcore_runtime'
        }
    
    def handle_device_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle device status request"""
        device_id = payload.get('device_id', 'HPLC-01')
        
        device_statuses = {
            'HPLC-01': {
                'device_id': 'HPLC-01',
                'type': 'HPLC',
                'status': 'ready',
                'temperature': 25.0,
                'pressure': 150.0,
                'flow_rate': 1.0
            },
            'CENTRIFUGE-01': {
                'device_id': 'CENTRIFUGE-01',
                'type': 'Centrifuge',
                'status': 'idle',
                'speed': 0,
                'temperature': 20.0
            },
            'PIPETTE-01': {
                'device_id': 'PIPETTE-01',
                'type': 'Pipette',
                'status': 'ready',
                'volume': 0.0,
                'tip_attached': True
            }
        }
        
        return {
            'success': True,
            'action': 'device_status',
            **device_statuses.get(device_id, device_statuses['HPLC-01']),
            'source': 'agentcore_runtime'
        }
    
    def handle_device_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle device command request"""
        device_id = payload.get('device_id', 'HPLC-01')
        operation = payload.get('operation', 'status')
        parameters = payload.get('parameters', {})
        
        return {
            'success': True,
            'action': 'device_command',
            'device_id': device_id,
            'operation': operation,
            'parameters': parameters,
            'result': {
                'status': 'completed',
                'message': f'Command {operation} executed on {device_id}',
                'execution_time': 1.5
            },
            'source': 'agentcore_runtime'
        }
    
    def handle_start_measurement(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle start measurement request"""
        device_id = payload.get('device_id', 'HPLC-01')
        measurement_type = payload.get('measurement_type', 'analysis')
        parameters = payload.get('parameters', {})
        
        return {
            'success': True,
            'action': 'start_measurement',
            'device_id': device_id,
            'measurement_type': measurement_type,
            'parameters': parameters,
            'measurement_id': f'MEAS_{device_id}_{measurement_type}_001',
            'estimated_duration': 300,  # 5 minutes
            'status': 'started',
            'source': 'agentcore_runtime'
        }
    
    def handle_stop_measurement(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stop measurement request"""
        device_id = payload.get('device_id', 'HPLC-01')
        measurement_id = payload.get('measurement_id', 'MEAS_HPLC-01_analysis_001')
        
        return {
            'success': True,
            'action': 'stop_measurement',
            'device_id': device_id,
            'measurement_id': measurement_id,
            'status': 'stopped',
            'results': {
                'data_points': 150,
                'duration': 180,  # 3 minutes
                'quality': 'good'
            },
            'source': 'agentcore_runtime'
        }

def lambda_handler(event, context):
    """Lambda handler for AgentCore Runtime"""
    try:
        runtime = AgentCoreRuntime()
        
        # Parse API Gateway event
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        
        # Parse body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError:
                pass
        
        # Handle different endpoints
        if path == '/agentcore' and http_method == 'GET':
            result = {
                'success': True,
                'message': 'AgentCore Runtime for SiLA2 Lab Automation',
                'version': '1.0.0',
                'capabilities': [
                    'list_devices', 'device_status', 'device_command',
                    'start_measurement', 'stop_measurement'
                ],
                'environment': runtime.environment
            }
        
        elif path == '/agentcore' and http_method == 'POST':
            result = runtime.handle_agent_request(body)
        
        else:
            result = {
                'success': False,
                'error': 'Invalid AgentCore endpoint',
                'available_endpoints': [
                    'GET /agentcore - Runtime info',
                    'POST /agentcore - Agent requests'
                ]
            }
        
        return {
            'statusCode': 200 if result.get('success') else 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"AgentCore Runtime error: {e}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'success': False, 'error': str(e)})
        }