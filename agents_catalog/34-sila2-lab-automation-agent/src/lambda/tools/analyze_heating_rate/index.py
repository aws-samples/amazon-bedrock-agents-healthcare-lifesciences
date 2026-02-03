import json
from datetime import datetime

def lambda_handler(event, context):
    """Calculate temperature rise rate - pure calculation only, decision delegated to AI"""
    
    # MCP format handling
    if 'jsonrpc' in event:
        params = event.get('params', {})
        arguments = params.get('arguments', {})
        device_id = arguments.get('device_id')
        history = arguments.get('history', [])
    else:
        device_id = event.get('device_id')
        history = event.get('history', [])
    
    # Need at least 2 points
    if len(history) < 2:
        result = {
            "error": "Need at least 2 data points",
            "heating_rate": 0.0,
            "message": f"Only {len(history)} point(s) provided"
        }
    else:
        # Use latest 2 points
        first_point = history[0]
        last_point = history[-1]
        
        # Calculate temperature difference
        temp_diff = last_point['temperature'] - first_point['temperature']
        
        # Calculate time difference (seconds → minutes)
        try:
            time_diff_seconds = (
                datetime.fromisoformat(last_point['timestamp'].replace('Z', '+00:00')) -
                datetime.fromisoformat(first_point['timestamp'].replace('Z', '+00:00'))
            ).total_seconds()
        except (KeyError, ValueError) as e:
            result = {
                "error": f"Invalid timestamp format: {str(e)}",
                "heating_rate": 0.0
            }
            return _format_response(event, result)
        
        time_diff_minutes = time_diff_seconds / 60.0
        
        # Calculate heating rate
        if time_diff_minutes > 0:
            heating_rate = temp_diff / time_diff_minutes
        else:
            heating_rate = 0.0
        
        result = {
            "device_id": device_id,
            "heating_rate": round(heating_rate, 2),
            "unit": "celsius_per_minute",
            "temp_diff": round(temp_diff, 2),
            "time_diff_seconds": round(time_diff_seconds, 1),
            "data_points": len(history)
        }
    
    return _format_response(event, result)

def _format_response(event, result):
    """Return response in MCP format or Direct format"""
    if 'jsonrpc' in event:
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [{"type": "text", "text": json.dumps(result)}]
            },
            "id": event.get('id', 1)
        }
    return result
