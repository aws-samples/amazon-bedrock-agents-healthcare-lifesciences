"""
SiLA2 Lab Automation Gateway - AgentCore Gateway Entry Point
"""
import json
import os
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Gateway entry point for SiLA2 Lab Automation"""
    
    api_gateway_url = os.environ.get('API_GATEWAY_URL')
    tool_name = event.get('tool_name', '')
    parameters = event.get('parameters', {})
    
    if tool_name == 'list_devices':
        response = {
            'success': True,
            'devices': [
                {'id': 'HPLC-01', 'type': 'HPLC', 'status': 'ready', 'source': 'Gateway'},
                {'id': 'CENTRIFUGE-01', 'type': 'Centrifuge', 'status': 'idle', 'source': 'Gateway'},
                {'id': 'PIPETTE-01', 'type': 'Pipette', 'status': 'ready', 'source': 'Gateway'}
            ],
            'count': 3,
            'source': 'AgentCore Gateway'
        }
    elif tool_name == 'device_status':
        device_id = parameters.get('device_id', 'unknown')
        response = {
            'success': True,
            'device_id': device_id,
            'status': 'ready',
            'type': 'SiLA2 Device',
            'source': 'AgentCore Gateway'
        }
    elif tool_name == 'start_operation':
        device_id = parameters.get('device_id', 'unknown')
        operation = parameters.get('operation', 'default')
        response = {
            'success': True,
            'device_id': device_id,
            'operation': operation,
            'status': 'started',
            'source': 'AgentCore Gateway'
        }
    else:
        response = {
            'success': False,
            'error': f'Unknown tool: {tool_name}',
            'available_tools': ['list_devices', 'device_status', 'start_operation'],
            'source': 'AgentCore Gateway'
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
