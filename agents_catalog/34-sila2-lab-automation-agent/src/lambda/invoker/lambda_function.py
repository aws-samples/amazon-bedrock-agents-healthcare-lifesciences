import json
import os
import boto3
import botocore.config
import logging
import requests
import time
import uuid
from datetime import datetime, timedelta
from bedrock_agentcore.memory import MemoryClient

# Disable boto3 debug logging for production
logging.basicConfig(level=logging.INFO)

RUNTIME_ARN = os.environ.get('AGENTCORE_RUNTIME_ARN')
MEMORY_ID = os.environ.get('AGENTCORE_MEMORY_ID')
SESSION_ID = os.environ.get('SESSION_ID', 'hplc_001')
BRIDGE_SERVER_URL = os.environ.get('BRIDGE_SERVER_URL', 'http://sila2-bridge-mcp.sila2-cluster.local:8080')

agent_core_client = boto3.client('bedrock-agentcore', region_name='us-west-2')

# Memory management using bedrock_agentcore SDK
MEMORY_SDK_AVAILABLE = True
memory_client = MemoryClient(region_name='us-west-2')

def record_to_memory(device_id, user_message, agent_response, session_id=None, session_title=None):
    """Common function for Memory recording"""
    if not MEMORY_ID or not MEMORY_SDK_AVAILABLE:
        print(f"[WARN] Memory recording skipped: MEMORY_ID={MEMORY_ID}, SDK_AVAILABLE={MEMORY_SDK_AVAILABLE}")
        return
    
    if not session_id:
        session_id = f"{device_id}-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    
    # Always use "hplc" as actor_id for consistency
    actor_id = "hplc"
    
    try:
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id=actor_id,
            session_id=session_id,
            messages=[
                (user_message, "USER"),
                (agent_response, "ASSISTANT")
            ]
        )
        print(f"[INFO] Memory recorded for session={session_id}")
    except Exception as e:
        print(f"[ERROR] Memory recording failed: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

def lambda_handler(event, context):
    # Detect SNS events
    if 'Records' in event:
        for record in event['Records']:
            if record.get('EventSource') == 'aws:sns':
                return handle_sns_event(event)
    
    action = event.get('action')
    
    if action in ['periodic', 'periodic_check']:
        return handle_periodic(event)
    elif action == 'manual_control':
        return handle_manual_control(event)
    elif action == 'get_history':
        return handle_get_history(event)
    elif action == 'get_temperature_direct':
        return handle_get_temperature_direct(event)
    
    return {"statusCode": 400, "body": json.dumps({"error": "Unknown action"})}

def handle_sns_event(event):
    """Process event messages via SNS"""
    print("[INFO] SNS event received")
    
    for record in event['Records']:
        if record.get('EventSource') != 'aws:sns':
            continue
        
        sns_message = json.loads(record['Sns']['Message'])
        event_type = sns_message.get('event_type')
        device_id = sns_message.get('device_id', 'hplc')
        
        print(f"[INFO] Event type: {event_type}, Device: {device_id}")
        
        if event_type in ['TemperatureReached', 'TEMPERATURE_REACHED']:
            # Notify AgentCore of target temperature reached
            current_temp = sns_message.get('value', 'N/A')
            
            # Get current status from Bridge API to confirm target temperature
            try:
                status_response = requests.get(
                    f"{BRIDGE_SERVER_URL}/api/status/{device_id}",
                    timeout=5
                )
                status_response.raise_for_status()
                status = status_response.json()
                target_temp = status.get('target_temperature', current_temp)
            except:
                target_temp = current_temp
            
            prompt = f"""🎯 Target Temperature Reached!

Device: {device_id}
Target: {target_temp}°C
Current: {current_temp}°C

The heating process has completed successfully. Please acknowledge this milestone."""
            
            try:
                payload = json.dumps({"prompt": prompt}).encode('utf-8')
                
                import botocore.config
                config = botocore.config.Config(
                    read_timeout=300,
                    connect_timeout=10,
                    retries={'max_attempts': 0}
                )
                
                agentcore_client = boto3.client('bedrock-agentcore', region_name='us-west-2', config=config)
                
                print(f"[INFO] Invoking AgentCore for event: {event_type}")
                
                session_id = f"{device_id}-temp-reached-{int(time.time())}-{uuid.uuid4().hex[:8]}"
                response = agentcore_client.invoke_agent_runtime(
                    agentRuntimeArn=RUNTIME_ARN,
                    runtimeSessionId=session_id,
                    payload=payload,
                    qualifier="DEFAULT"
                )
                
                response_body = response['response'].read()
                response_text = response_body.decode('utf-8') if isinstance(response_body, bytes) else response_body
                
                lines = response_text.strip().split('\n')
                agent_response = ""
                for line in lines:
                    if line.startswith('data: '):
                        agent_response += line[6:]
                
                print(f"[INFO] AgentCore response: {agent_response[:100]}...")
                
                # Record to Memory
                record_to_memory(
                    device_id=device_id,
                    user_message=f"Temperature reached event for device {device_id}: Target {target_temp}°C, Current {current_temp}°C",
                    agent_response=agent_response,
                    session_id=session_id,
                    session_title=f"🎯 Temperature Reached: {device_id}"
                )
                
                return {"statusCode": 200, "body": json.dumps({
                    "event_type": event_type,
                    "device_id": device_id,
                    "response": agent_response
                })}
                
            except Exception as e:
                print(f"[ERROR] AgentCore error: {e}")
                return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
        
        elif event_type == 'ExperimentAborted':
            # Handle experiment abort completion event
            abort_info = sns_message.get('value', {})
            
            prompt = f"""🛑 Experiment Aborted!

Device: {device_id}
Final Temperature: {abort_info.get('FinalTemperature')}°C
Reason: {abort_info.get('Reason')}
Success: {abort_info.get('Success')}
Timestamp: {abort_info.get('Timestamp')}

Please record this abort event to memory."""
            
            try:
                payload = json.dumps({"prompt": prompt}).encode('utf-8')
                
                import botocore.config
                config = botocore.config.Config(
                    read_timeout=300,
                    connect_timeout=10,
                    retries={'max_attempts': 0}
                )
                
                agentcore_client = boto3.client('bedrock-agentcore', region_name='us-west-2', config=config)
                
                print(f"[INFO] Invoking AgentCore for abort event")
                
                session_id = f"{device_id}-aborted-{int(time.time())}-{uuid.uuid4().hex[:8]}"
                response = agentcore_client.invoke_agent_runtime(
                    agentRuntimeArn=RUNTIME_ARN,
                    runtimeSessionId=session_id,
                    payload=payload,
                    qualifier="DEFAULT"
                )
                
                response_body = response['response'].read()
                response_text = response_body.decode('utf-8') if isinstance(response_body, bytes) else response_body
                
                lines = response_text.strip().split('\n')
                agent_response = ""
                for line in lines:
                    if line.startswith('data: '):
                        agent_response += line[6:]
                
                print(f"[INFO] AgentCore response: {agent_response[:100]}...")
                
                # Record to Memory
                record_to_memory(
                    device_id=device_id,
                    user_message=f"🛑 Experiment Aborted: Device {device_id}, Reason: {abort_info.get('Reason')}, Final Temperature: {abort_info.get('FinalTemperature')}°C",
                    agent_response=agent_response,
                    session_id=session_id
                )
                
                return {"statusCode": 200, "body": json.dumps({
                    "event_type": event_type,
                    "device_id": device_id,
                    "response": agent_response
                })}
                
            except Exception as e:
                print(f"[ERROR] AgentCore error: {e}")
                return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    
    return {"statusCode": 200, "body": json.dumps({"message": "No events processed"})}

def handle_periodic(event):
    """Periodic check: pass status + history data, decision fully delegated to AI"""
    device_id = event.get('device_id', 'hplc')
    device_session_id = f"{device_id}-{int(time.time())}-{uuid.uuid4().hex}"
    
    # 1. Get current status
    try:
        response = requests.get(
            f"{BRIDGE_SERVER_URL}/api/status/{device_id}",
            timeout=5
        )
        response.raise_for_status()
        status = response.json()
        print(f"[INFO] Status API response: {status}")
    except Exception as e:
        print(f"[ERROR] Failed to get status: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        status = {
            "heating_status": "unknown",
            "current_temp": 0,
            "target_temp": None,
            "scenario_mode": "unknown"
        }
    
    # 2. Get recent 2 data points
    try:
        response = requests.get(
            f"{BRIDGE_SERVER_URL}/api/history/{device_id}?minutes=5",
            timeout=5
        )
        response.raise_for_status()
        history_response = response.json()
        history_data = history_response.get('data', [])
        recent_two = history_data[-2:] if len(history_data) >= 2 else history_data
    except Exception as e:
        print(f"[ERROR] Failed to get history: {e}")
        recent_two = []
    
    # 3. Inform AI of situation (no decision instructions, data only)
    prompt = f"""Periodic status check for device {device_id}:

Current Status:
- Heating Status: {status.get('heating_status', 'unknown')}
- Current Temperature: {status.get('temperature', 0)}°C
- Target Temperature: {status.get('target_temperature', 'N/A')}°C
- Scenario Mode: {status.get('scenario_mode', 'unknown')}

Recent History (last 2 data points for heating rate calculation):
{json.dumps(recent_two, indent=2)}

Please analyze the situation and take appropriate action if needed."""
    
    try:
        payload = json.dumps({"prompt": prompt}).encode('utf-8')
        
        import botocore.config
        config = botocore.config.Config(
            read_timeout=300,
            connect_timeout=10,
            retries={'max_attempts': 0}
        )
        
        agentcore_client = boto3.client('bedrock-agentcore', region_name='us-west-2', config=config)
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            runtimeSessionId=device_session_id,
            payload=payload,
            qualifier="DEFAULT"
        )
        
        response_body = response['response'].read()
        response_text = response_body.decode('utf-8') if isinstance(response_body, bytes) else response_body
        
        lines = response_text.strip().split('\n')
        agent_response = ""
        for line in lines:
            if line.startswith('data: '):
                agent_response += line[6:]
        
        record_to_memory(
            device_id=device_id,
            user_message=prompt,
            agent_response=agent_response,
            session_id=device_session_id,
            session_title=f"📊 Periodic Status: {device_id}"
        )
        
        return {"statusCode": 200, "body": json.dumps({
            "response": agent_response
        })}
        
    except Exception as e:
        print(f"[ERROR] AgentCore error: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def handle_manual_control(event):
    """Manual control - via AgentCore"""
    device_id = event.get('device_id', 'hplc')
    query = event.get('query', '')
    
    device_session_id = f"device-{device_id}-session-{device_id}-00000000"
    
    try:
        payload = json.dumps({"prompt": query}).encode("utf-8")
        
        import botocore.config
        config = botocore.config.Config(
            read_timeout=300,
            connect_timeout=10,
            retries={'max_attempts': 0}
        )
        
        agentcore_client = boto3.client('bedrock-agentcore', region_name='us-west-2', config=config)
        
        print(f"[INFO] Invoking AgentCore Runtime: {RUNTIME_ARN}")
        print(f"[INFO] Device Session ID: {device_session_id}")
        
        import time
        start_time = time.time()
        print(f"[TIMING] Starting invoke_agent_runtime at {start_time}")
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            runtimeSessionId=device_session_id,
            payload=payload,
            qualifier="DEFAULT"
        )
        
        invoke_time = time.time() - start_time
        print(f"[TIMING] invoke_agent_runtime completed in {invoke_time:.2f}s")
        print(f"[INFO] AgentCore response received, reading body...")
        response_body = response['response'].read()
        
        response_text = response_body.decode('utf-8') if isinstance(response_body, bytes) else response_body
        
        lines = response_text.strip().split('\n')
        agent_response = ""
        for line in lines:
            if line.startswith('data: '):
                agent_response += line[6:]
        
        # Record to Memory
        record_to_memory(
            device_id=device_id,
            user_message=query,
            agent_response=agent_response,
            session_id=device_session_id,
            session_title=f"🎮 Manual Control: {device_id}"
        )
        
        return {"statusCode": 200, "body": json.dumps({"response": agent_response})}
        
    except Exception as e:
        print(f"[ERROR] AgentCore error: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def clear_and_initialize_memory_DEPRECATED(device_id, target_temp):
    """Memory initialization + experiment rule registration"""
    if not MEMORY_ID or not MEMORY_SDK_AVAILABLE:
        print(f"[WARN] MEMORY_ID not set or SDK not available")
        return
    
    # Shorten Session ID (100 character limit)
    session_id = f"hplc-session-{device_id[-8:]}" if len(device_id) > 8 else f"hplc-session-{device_id}"
    
    try:
        memory_client = MemoryClient(region_name='us-west-2')
        
        # Register experiment rules
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id=device_id[:50],  # 50 character limit
            session_id=session_id,
            messages=[
                (f"Experiment start: Set target temperature for device {device_id} to {target_temp}°C", "USER"),
                (f"Experiment rules memorized. Target temperature {target_temp}°C, expected heating rate 1.0°C/min or higher, below 0.5°C/min is considered abnormal.", "ASSISTANT")
            ]
        )
        
        print(f"[INFO] Experiment rules registered for {device_id} in session {session_id}")
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize memory: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

def ensure_experiment_rules_DEPRECATED(device_id):
    """Check experiment rules (DEPRECATED)"""
    return True

def check_recent_manual_control_DEPRECATED(device_id, minutes=5):
    """Check manual control within specified minutes (DEPRECATED)"""
    return False

def record_manual_control_DEPRECATED(device_id, command):
    """Record manual control to Memory (DEPRECATED)"""
    pass

def handle_get_history(event):
    """Get history - via AgentCore"""
    device_id = event.get('device_id', 'hplc')
    minutes = event.get('minutes', 5)
    query = f"Get temperature history for {device_id} for the last {minutes} minutes"
    
    device_session_id = f"device-{device_id}-session-{device_id}-00000000"
    
    try:
        payload = json.dumps({"prompt": query}).encode("utf-8")
        
        import botocore.config
        config = botocore.config.Config(
            read_timeout=300,
            connect_timeout=10,
            retries={'max_attempts': 0}
        )
        
        agentcore_client = boto3.client('bedrock-agentcore', region_name='us-west-2', config=config)
        
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            runtimeSessionId=device_session_id,
            payload=payload,
            qualifier="DEFAULT"
        )
        
        response_body = response['response'].read()
        response_text = response_body.decode('utf-8') if isinstance(response_body, bytes) else response_body
        
        lines = response_text.strip().split('\n')
        agent_response = ""
        for line in lines:
            if line.startswith('data: '):
                agent_response += line[6:]
        
        return {"statusCode": 200, "body": json.dumps({"response": agent_response})}
        
    except Exception as e:
        print(f"[ERROR] AgentCore error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def handle_get_temperature_direct(event):
    """Get temperature data directly from Bridge Server API"""
    device_id = event.get('device_id', 'hplc')
    
    try:
        response = requests.get(
            f"{BRIDGE_SERVER_URL}/api/history/{device_id}",
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return {"statusCode": 200, "body": json.dumps({"data": data})}
    except Exception as e:
        print(f"[ERROR] Bridge Server API error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e), "data": []})}
