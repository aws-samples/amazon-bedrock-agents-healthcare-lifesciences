import json
import os
import boto3
import botocore.config
import logging
import requests
import time
import uuid
from datetime import datetime, timedelta

# Disable boto3 debug logging for production
logging.basicConfig(level=logging.INFO)

RUNTIME_ARN = os.environ.get('AGENTCORE_RUNTIME_ARN')
MEMORY_ID = os.environ.get('AGENTCORE_MEMORY_ID')
BRIDGE_SERVER_URL = os.environ.get('BRIDGE_SERVER_URL', 'http://sila2-bridge-mcp.sila2-cluster.local:8080')

agent_core_client = boto3.client('bedrock-agentcore', region_name='us-west-2')

# Memory management using bedrock_agentcore.memory
try:
    from bedrock_agentcore.memory import MemoryClient
    MEMORY_SDK_AVAILABLE = True
except ImportError:
    print("[WARN] bedrock_agentcore.memory not available, memory features disabled")
    MEMORY_SDK_AVAILABLE = False
    MemoryClient = None

def record_to_memory(device_id, user_message, agent_response):
    """Memory記録の共通関数"""
    if not MEMORY_ID or not MEMORY_SDK_AVAILABLE:
        print(f"[WARN] Memory recording skipped: MEMORY_ID={MEMORY_ID}, SDK_AVAILABLE={MEMORY_SDK_AVAILABLE}")
        return
    
    session_id = f"device-{device_id}-session-{device_id}-00000000"
    
    try:
        memory_client = MemoryClient(region_name='us-west-2')
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id=device_id[:50],
            session_id=session_id,
            messages=[
                (user_message, "USER"),
                (agent_response, "ASSISTANT")
            ]
        )
        print(f"[INFO] Memory recorded for {device_id}")
    except Exception as e:
        print(f"[ERROR] Memory recording failed: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

def lambda_handler(event, context):
    # SNSイベントの検出
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
    """SNS経由のeventメッセージ処理"""
    print("[INFO] SNS event received")
    
    for record in event['Records']:
        if record.get('EventSource') != 'aws:sns':
            continue
        
        sns_message = json.loads(record['Sns']['Message'])
        event_type = sns_message.get('event_type')
        device_id = sns_message.get('device_id', 'hplc')
        
        print(f"[INFO] Event type: {event_type}, Device: {device_id}")
        
        if event_type == 'TEMPERATURE_REACHED':
            # 目標温度到達をAgentCoreに通知
            device_session_id = f"device-{device_id}-session-{device_id}-00000000"
            
            target_temp = sns_message.get('target_temperature')
            current_temp = sns_message.get('current_temperature')
            
            prompt = f"""Target temperature reached!
Device: {device_id}
Target: {target_temp}°C
Current: {current_temp}°C

Please acknowledge this milestone."""
            
            try:
                payload = json.dumps({"input": {"prompt": prompt}})
                
                import botocore.config
                config = botocore.config.Config(
                    read_timeout=300,
                    connect_timeout=10,
                    retries={'max_attempts': 0}
                )
                
                agentcore_client = boto3.client('bedrock-agentcore', region_name='us-west-2', config=config)
                
                print(f"[INFO] Invoking AgentCore for event: {event_type}")
                
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
                
                print(f"[INFO] AgentCore response: {agent_response[:100]}...")
                
                # Memory記録
                record_to_memory(
                    device_id=device_id,
                    user_message=f"Event: {event_type} - Target: {target_temp}°C, Current: {current_temp}°C",
                    agent_response=agent_response
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
    """定期チェック: 状態+履歴データを渡し、判断はAIに完全委譲"""
    device_id = event.get('device_id', 'hplc')
    device_session_id = f"device-{device_id}-{int(time.time())}-{uuid.uuid4().hex}"
    
    # 1. 現在の状態取得
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
    
    # 2. 直近2つのデータポイント取得
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
    
    # 3. AIに状況を伝える (判断指示なし、データのみ)
    prompt = f"""Periodic status check for device {device_id}:

Current Status:
- Heating Status: {status.get('heating_status', 'unknown')}
- Current Temperature: {status.get('temperature', 0)}°C
- Target Temperature: {status.get('target_temperature', 'N/A')}°C
- Scenario Mode: {status.get('scenario_mode', 'unknown')}

Recent History (last 2 data points for heating rate calculation):
{json.dumps(recent_two, indent=2)}

Please assess the situation and decide:
1. Should you analyze the heating rate?
2. Is any action needed?"""
    
    try:
        payload = json.dumps({"input": {"prompt": prompt}})
        
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
        
        # Memory記録
        record_to_memory(
            device_id=device_id,
            user_message=prompt,
            agent_response=agent_response
        )
        
        return {"statusCode": 200, "body": json.dumps({
            "status": status,
            "history_count": len(recent_two),
            "response": agent_response
        })}
        
    except Exception as e:
        print(f"[ERROR] AgentCore error: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def handle_manual_control(event):
    """手動制御 - AgentCore経由"""
    device_id = event.get('device_id', 'hplc')
    query = event.get('query', '')
    
    device_session_id = f"device-{device_id}-session-{device_id}-00000000"
    
    try:
        payload = json.dumps({"input": {"prompt": query}})
        
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
        
        # Memory記録
        record_to_memory(
            device_id=device_id,
            user_message=query,
            agent_response=agent_response
        )
        
        return {"statusCode": 200, "body": json.dumps({"response": agent_response})}
        
    except Exception as e:
        print(f"[ERROR] AgentCore error: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

def clear_and_initialize_memory_DEPRECATED(device_id, target_temp):
    """Memory初期化 + 実験ルール登録"""
    if not MEMORY_ID or not MEMORY_SDK_AVAILABLE:
        print(f"[WARN] MEMORY_ID not set or SDK not available")
        return
    
    # Session IDを短縮 (100文字制限)
    session_id = f"hplc-session-{device_id[-8:]}" if len(device_id) > 8 else f"hplc-session-{device_id}"
    
    try:
        memory_client = MemoryClient(region_name='us-west-2')
        
        # 実験ルール登録
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id=device_id[:50],  # 50文字制限
            session_id=session_id,
            messages=[
                (f"実験開始: デバイス{device_id}の目標温度を{target_temp}°Cに設定", "USER"),
                (f"実験ルールを記憶しました。目標温度{target_temp}°C、期待昇温速度1.0°C/分以上、0.5°C/分未満は異常と判断します。", "ASSISTANT")
            ]
        )
        
        print(f"[INFO] Experiment rules registered for {device_id} in session {session_id}")
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize memory: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")

def ensure_experiment_rules_DEPRECATED(device_id):
    """実験ルール確認 (DEPRECATED)"""
    return True

def check_recent_manual_control_DEPRECATED(device_id, minutes=5):
    """過去指定分以内の手動制御をチェック (DEPRECATED)"""
    return False

def record_manual_control_DEPRECATED(device_id, command):
    """手動制御をMemoryに記録 (DEPRECATED)"""
    pass

def handle_get_history(event):
    """履歴取得 - AgentCore経由"""
    device_id = event.get('device_id', 'hplc')
    minutes = event.get('minutes', 5)
    query = f"Get temperature history for {device_id} for the last {minutes} minutes"
    
    device_session_id = f"device-{device_id}-session-{device_id}-00000000"
    
    try:
        payload = json.dumps({"input": {"prompt": query}})
        
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
    """Bridge Server APIから直接温度データを取得"""
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
