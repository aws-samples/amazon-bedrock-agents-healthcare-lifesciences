"""
Simple Mock Device Lambda for testing
"""
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Lambda handler for mock device operations"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request body if it exists
        body = {}
        if 'body' in event and event['body']:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        
        action = body.get('action', 'unknown')
        device_id = body.get('device_id', 'unknown')
        
        logger.info(f"Action: {action}, Device ID: {device_id}")
        
        # Mock device responses
        if action == 'list':
            response_data = {
                'devices': [
                    {'id': 'HPLC-01', 'type': 'hplc', 'status': 'ready'},
                    {'id': 'CENTRIFUGE-01', 'type': 'centrifuge', 'status': 'busy'},
                    {'id': 'PIPETTE-01', 'type': 'pipette', 'status': 'ready'}
                ]
            }
        elif action == 'status':
            response_data = {
                'device_id': device_id,
                'status': 'ready',
                'temperature': 25.0,
                'timestamp': '2025-11-21T03:00:00Z'
            }
        elif action == 'command':
            command = body.get('command', 'unknown')
            response_data = {
                'device_id': device_id,
                'command': command,
                'result': f'Command {command} executed successfully',
                'status': 'completed'
            }
        else:
            response_data = {
                'error': f'Unknown action: {action}'
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }