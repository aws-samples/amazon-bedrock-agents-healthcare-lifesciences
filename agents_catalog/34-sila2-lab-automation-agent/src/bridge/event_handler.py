import boto3
import json
import os
from datetime import datetime

sns_client = boto3.client('sns')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

async def handle_sila2_event(device_id: str, event_data: dict):
    """Send SiLA2 event to SNS"""
    if not SNS_TOPIC_ARN:
        print("SNS_TOPIC_ARN not configured, skipping event publish")
        return
    
    message = {
        'device_id': device_id,
        'event_type': event_data['event_type'],
        'value': event_data.get('value'),
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=json.dumps(message),
            Subject=f"SiLA2 Event: {event_data['event_type']}"
        )
        print(f"Published event to SNS: {event_data['event_type']}")
    except Exception as e:
        print(f"Failed to publish to SNS: {e}")
