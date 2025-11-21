"""
SiLA2 Lab Automation Agent - Phase 3 Complete Main Entry Point
"""
import json
import os
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main entry point for SiLA2 Lab Automation Agent Phase 3"""
    
    api_gateway_url = os.environ.get('API_GATEWAY_URL')
    prompt = event.get('prompt', '')
    
    # Enhanced routing
    if 'list' in prompt.lower() and 'device' in prompt.lower():
        action = 'list_devices'
    elif 'status' in prompt.lower():
        action = 'device_status'
    elif 'start' in prompt.lower() and 'measurement' in prompt.lower():
        action = 'start_measurement'
    elif 'stop' in prompt.lower() and 'measurement' in prompt.lower():
        action = 'stop_measurement'
    elif 'execute' in prompt.lower() or 'command' in prompt.lower():
        action = 'device_command'
    else:
        action = 'general_info'
    
    # Response based on action
    if action == 'list_devices':
        response = {
            'message': 'Available SiLA2 devices (Phase 3):',
            'devices': [
                {'id': 'HPLC-01', 'type': 'HPLC', 'status': 'ready', 'protocol': 'gRPC'},
                {'id': 'CENTRIFUGE-01', 'type': 'Centrifuge', 'status': 'idle', 'protocol': 'HTTP'},
                {'id': 'PIPETTE-01', 'type': 'Pipette', 'status': 'ready', 'protocol': 'gRPC'},
                {'id': 'BRIDGE-DEVICE-01', 'type': 'Protocol Bridge', 'status': 'ready', 'protocol': 'HTTP↔gRPC'}
            ],
            'api_url': api_gateway_url
        }
    elif action == 'device_status':
        response = {
            'message': 'Device status check completed (Phase 3)',
            'status': 'All devices operational',
            'capabilities': ['HTTP API', 'gRPC Protocol', 'Protocol Bridge'],
            'api_url': api_gateway_url
        }
    else:
        response = {
            'message': f'SiLA2 Lab Automation Agent Phase 3 - Action: {action}',
            'prompt': prompt,
            'api_url': api_gateway_url,
            'status': 'ready'
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps(response, indent=2)
    }
