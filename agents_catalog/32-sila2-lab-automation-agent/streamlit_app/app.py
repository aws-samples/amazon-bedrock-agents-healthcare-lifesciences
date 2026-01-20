import streamlit as st
import time
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import boto3
import json
import os

st.set_page_config(page_title="SiLA2 Lab Automation", layout="wide")

# Custom CSS for text wrapping
st.markdown("""
<style>
    pre {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }
    code {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧪 SiLA2 Lab Automation Demo")

if 'temperature_data' not in st.session_state:
    st.session_state.temperature_data = []

LAMBDA_FUNCTION = os.getenv('LAMBDA_FUNCTION_NAME', 'sila2-agentcore-invoker')
AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
MEMORY_ID = 'sila2_memory-GtKp0NHuqf'

lambda_client = boto3.client('lambda', region_name=AWS_REGION)

try:
    bedrock_agentcore = boto3.client('bedrock-agentcore', region_name=AWS_REGION)
    MEMORY_AVAILABLE = True
except:
    MEMORY_AVAILABLE = False

def invoke_agentcore_with_temperature(device_id, temperature):
    """Invoke AgentCore with temperature setting"""
    try:
        payload = {
            "action": "manual_control",
            "device_id": device_id,
            "query": f"Set temperature to {temperature}°C for device {device_id}"
        }
        
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            return body.get('response', 'No response')
        else:
            return f"Error: {result.get('body', 'Unknown error')}"
            
    except Exception as e:
        return f"Exception: {str(e)}"

def get_temperature_data():
    try:
        payload = {"action": "get_temperature_direct", "device_id": "hplc"}
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body']) if isinstance(result.get('body'), str) else result.get('body', {})
            data = body.get('data', {})
            if isinstance(data, dict) and 'data' in data:
                data_list = data['data']
            elif isinstance(data, list):
                data_list = data
            else:
                return None
            
            if data_list:
                latest = data_list[-1]
                return {
                    'timestamp': datetime.fromisoformat(latest['timestamp'].replace('Z', '+00:00')),
                    'temperature': latest['temperature'],
                    'target_temperature': latest['target_temperature'],
                    'elapsed_seconds': latest['elapsed_seconds'],
                    'scenario_mode': latest.get('scenario_mode', 'scenario_1'),
                    'heating_status': latest.get('heating_status', 'unknown')
                }
    except Exception as e:
        st.error(f"⚠️ Error: {e}")
    return None

def get_recent_session_ids_from_logs():
    """Get recent session IDs from CloudWatch Logs"""
    try:
        logs_client = boto3.client('logs', region_name=AWS_REGION)
        import time
        start_time = int((time.time() - 3600) * 1000)
        
        response = logs_client.filter_log_events(
            logGroupName='/aws/lambda/' + LAMBDA_FUNCTION,
            startTime=start_time,
            filterPattern='"Memory recorded"'
        )
        
        session_ids = []
        for event in response.get('events', []):
            message = event.get('message', '')
            if 'session=' in message:
                session_id = message.split('session=')[1].strip()
                if session_id and session_id not in session_ids:
                    session_ids.append(session_id)
        
        return session_ids
    except Exception as e:
        return []

def get_memory_events_with_id(memory_id):
    debug_info = {'status': 'starting'}
    
    if not MEMORY_AVAILABLE:
        return [], {'error': 'Memory SDK not available'}
    if not memory_id:
        return [], {'error': 'MEMORY_ID not set'}
    
    try:
        actor_id = "hplc"
        debug_info['actor_id'] = actor_id
        all_events = []
        all_session_ids = set()
        
        # 1. Get recent session IDs from CloudWatch Logs
        recent_session_ids = get_recent_session_ids_from_logs()
        debug_info['log_sessions_count'] = len(recent_session_ids)
        debug_info['log_session_ids'] = recent_session_ids[:5]
        all_session_ids.update(recent_session_ids)
        
        # 2. Get known sessions with list_sessions
        sessions_response = bedrock_agentcore.list_sessions(
            memoryId=memory_id,
            actorId=actor_id,
            maxResults=50
        )
        
        sessions = sessions_response.get('sessionSummaries', [])
        debug_info['list_sessions_count'] = len(sessions)
        for session in sessions:
            all_session_ids.add(session.get('sessionId'))
        
        debug_info['total_unique_sessions'] = len(all_session_ids)
        
        # 3. Get events from all sessions
        for session_id in all_session_ids:
            if not session_id:
                continue
            
            try:
                events_response = bedrock_agentcore.list_events(
                    memoryId=memory_id,
                    actorId=actor_id,
                    sessionId=session_id,
                    maxResults=50
                )
                
                for event in events_response.get('events', []):
                    content_text = ""
                    role = "unknown"
                    event_type = "unknown"
                    
                    if event.get('payload'):
                        for payload in event['payload']:
                            if 'conversational' in payload:
                                conv = payload['conversational']
                                role = conv.get('role', 'unknown')
                                if 'content' in conv and 'text' in conv['content']:
                                    content_text = conv['content']['text']
                                    if '🎯 Target Temperature Reached' in content_text or 'Temperature reached event' in content_text or "heating_status: 'completed'" in content_text or "heating_status: completed" in content_text:
                                        event_type = 'TEMPERATURE_REACHED'
                                    elif 'Periodic status check' in content_text:
                                        event_type = 'PERIODIC_STATUS'
                                    elif 'Set temperature' in content_text:
                                        event_type = 'MANUAL_CONTROL'
                                    break
                            elif 'toolUse' in payload:
                                tool_use = payload['toolUse']
                                role = 'tool_use'
                                event_type = 'TOOL_USE'
                                content_text = f"Tool: {tool_use.get('name', 'unknown')}\nInput: {json.dumps(tool_use.get('input', {}), indent=2)}"
                                break
                            elif 'toolResult' in payload:
                                tool_result = payload['toolResult']
                                role = 'tool_result'
                                event_type = 'TOOL_RESULT'
                                content_text = f"Tool: {tool_result.get('toolUseId', 'unknown')}\nStatus: {tool_result.get('status', 'unknown')}\nContent: {json.dumps(tool_result.get('content', []), indent=2)}"
                                break
                    
                    all_events.append({
                        'timestamp': event.get('eventTimestamp', datetime.now()),
                        'eventId': event.get('eventId', 'unknown'),
                        'actorId': actor_id,
                        'sessionId': session_id,
                        'role': role,
                        'event_type': event_type,
                        'content': content_text,
                        'raw': event
                    })
            except Exception as e:
                debug_info[f'session_{session_id[:20]}_error'] = str(e)
        
        all_events.sort(key=lambda x: x['timestamp'], reverse=True)
        debug_info['event_count'] = len(all_events)
        debug_info['session_count'] = len(all_session_ids)
        debug_info['latest_event_time'] = all_events[0]['timestamp'].isoformat() if all_events else 'N/A'
        return all_events[:50], debug_info
        
    except Exception as e:
        return [], {'error': str(e), 'traceback': str(e)}

def get_memory_events():
    return get_memory_events_with_id(MEMORY_ID)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Monitor", "🎛️ Control", "🧠 AI Memory", "📋 CloudWatch Logs"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📈 Real-time Temperature")
        
        latest_data = None
        try:
            latest_data = get_temperature_data()
        except Exception as e:
            st.error(f"⚠️ Failed to get temperature data: {e}")
        if latest_data:
            st.session_state.temperature_data.append(latest_data)
            
            if len(st.session_state.temperature_data) > 50:
                st.session_state.temperature_data = st.session_state.temperature_data[-50:]
        
        if st.session_state.temperature_data:
            df = pd.DataFrame(st.session_state.temperature_data)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['temperature'],
                mode='lines+markers',
                name='Temperature',
                line=dict(color='#FF6B6B', width=2)
            ))
            
            if df['target_temperature'].iloc[-1] > 0:
                fig.add_hline(
                    y=df['target_temperature'].iloc[-1],
                    line_dash="dash",
                    line_color="green",
                    annotation_text=f"Target: {df['target_temperature'].iloc[-1]}°C"
                )
            
            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="Temperature (°C)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            if len(df) >= 2:
                recent = df.iloc[-2:]
                temp_diff = recent.iloc[-1]['temperature'] - recent.iloc[0]['temperature']
                time_diff = (recent.iloc[-1]['timestamp'] - recent.iloc[0]['timestamp']).total_seconds() / 60
                rate = temp_diff / time_diff if time_diff > 0 else 0
                
                rate_color = "🟢" if rate >= 4.0 else "🟡" if rate >= 3.0 else "🔴"
                st.metric("Heating Rate", f"{rate_color} {rate:.2f}°C/min")
        else:
            st.info("Waiting for temperature data...")
    
    with col2:
        st.subheader("📊 Status")
        
        if latest_data:
            st.metric("Current", f"{latest_data['temperature']:.1f}°C")
            st.metric("Target", f"{latest_data['target_temperature']:.1f}°C")
            st.metric("Elapsed", f"{latest_data['elapsed_seconds']}s")
            
            st.write("**Heating Status:**")
            heating_status = latest_data.get('heating_status', 'unknown')
            if heating_status == 'idle':
                st.info("⚪ Idle")
            elif heating_status == 'heating':
                st.success("🔥 Heating")
            elif heating_status == 'completed':
                st.success("✅ Completed")
            else:
                st.warning(f"❓ {heating_status}")
            
            scenario = latest_data.get('scenario_mode', 'scenario_1')
            if scenario == 'scenario_1':
                st.info("🔵 Scenario 1 (5°C/min)")
            else:
                st.warning("🟡 Scenario 2 (2°C/min)")
            
            if latest_data['target_temperature'] > 25:
                progress = min((latest_data['temperature'] - 25) / (latest_data['target_temperature'] - 25), 1.0)
                st.progress(progress)
                st.caption(f"Progress: {progress*100:.1f}%")

with tab2:
    st.subheader("🎛️ Temperature Control")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        target_temp = st.slider(
            "Target Temperature (°C)",
            min_value=25,
            max_value=100,
            value=80,
            step=5,
            help="Set the target temperature for the HPLC device"
        )
        
        device_id = st.selectbox(
            "Device",
            options=["hplc"],
            index=0,
            help="Select the device to control"
        )
    
    with col2:
        st.write("**Current Settings:**")
        if latest_data:
            st.write(f"Current: {latest_data['temperature']:.1f}°C")
            st.write(f"Target: {latest_data['target_temperature']:.1f}°C")
        
        if st.button("🔥 Set Temperature", type="primary"):
            with st.spinner("Setting temperature..."):
                response = invoke_agentcore_with_temperature(device_id, target_temp)
                st.success(f"✅ Command sent!")
                st.write("**AI Response:**")
                st.write(response)
    
    st.divider()
    
    st.subheader("🤖 Custom Commands")
    custom_query = st.text_input(
        "Custom Query",
        placeholder="e.g., 'Analyze the current heating rate' or 'Stop the experiment'",
        help="Send a custom command to the AI agent"
    )
    
    if st.button("📤 Send Command") and custom_query:
        with st.spinner("Processing command..."):
            try:
                payload = {
                    "action": "manual_control",
                    "device_id": device_id,
                    "query": custom_query
                }
                
                response = lambda_client.invoke(
                    FunctionName=LAMBDA_FUNCTION,
                    InvocationType='RequestResponse',
                    Payload=json.dumps(payload)
                )
                
                result = json.loads(response['Payload'].read())
                
                if result.get('statusCode') == 200:
                    body = json.loads(result['body'])
                    st.success("✅ Command processed!")
                    st.write("**AI Response:**")
                    st.write(body.get('response', 'No response'))
                else:
                    st.error(f"❌ Error: {result.get('body', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"❌ Exception: {str(e)}")

with tab3:
    st.subheader("🧠 AI Memory & Decision History")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write(f"**Memory ID:** `{MEMORY_ID}`")
        st.write(f"**Region:** `{AWS_REGION}`")
    
    with col2:
        if st.button("🔄 Refresh Memory", type="primary"):
            st.rerun()
    
    memory_events, debug_info = get_memory_events()
    
    if 'error' in debug_info:
        st.error(f"❌ Error: {debug_info['error']}")
        with st.expander("🔍 Debug Info"):
            st.json(debug_info)
    else:
        st.success(f"✅ Sessions: {debug_info.get('session_count', 0)} | Events: {debug_info.get('event_count', 0)}")
        with st.expander("🔍 Debug Info"):
            st.json(debug_info)
    
    if memory_events:
        for i, event in enumerate(memory_events):
            timestamp = event['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            content = event['content']
            role = event.get('role', 'unknown')
            evt_type = event.get('event_type', 'unknown')
            
            if evt_type == 'TOOL_USE':
                icon = "🔧"
                event_type = "Tool Call"
            elif evt_type == 'TOOL_RESULT':
                icon = "📥"
                event_type = "Tool Result"
            elif evt_type == 'TEMPERATURE_REACHED':
                icon = "🔔"
                event_type = "Temperature Reached"
            elif evt_type == 'PERIODIC_STATUS':
                icon = "📊"
                event_type = "Periodic Status"
            elif evt_type == 'MANUAL_CONTROL':
                icon = "🎛️"
                event_type = "Manual Control"
            elif '🛑 Experiment Aborted' in content:
                icon = "🛑"
                event_type = "Experiment Aborted"
            elif role == 'user':
                icon = "👤"
                event_type = "User"
            elif role == 'assistant':
                icon = "🤖"
                event_type = "AI"
            else:
                icon = "💬"
                event_type = role.title()
            
            with st.expander(f"{icon} {timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {event_type}", expanded=(i<3)):
                st.write(f"**Actor:** {event['actorId']}")
                st.write(f"**Session:** {event['sessionId'][:50]}...")
                st.write(f"**Event ID:** {event['eventId'][:50]}...")
                
                if content:
                    st.write("**Content:**")
                    st.markdown(content)
                
                if st.checkbox(f"Show raw data", key=f"raw_{i}"):
                    st.json(event['raw'])
    else:
        st.info("💡 No memory events found. The system will record events during periodic monitoring and manual control.")

with tab4:
    st.subheader("📋 CloudWatch Logs - Agent Execution Details")
    
    LOG_GROUP = '/aws/bedrock-agentcore/runtimes/sila2_agent-5o08mC3jJ0-DEFAULT'
    LOG_STREAM = 'otel-rt-logs'
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**Log Group:** `{LOG_GROUP}`")
        st.write(f"**Log Stream:** `{LOG_STREAM}`")
    with col2:
        if st.button("🔄 Refresh Logs", type="primary", key="refresh_logs"):
            st.rerun()
    
    try:
        logs_client = boto3.client('logs', region_name=AWS_REGION)
        
        # Get recent log events
        import time
        response = logs_client.get_log_events(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM,
            startFromHead=False,
            limit=100
        )
        
        events = response.get('events', [])
        
        if events:
            st.success(f"✅ Found {len(events)} recent log entries")
            
            # Parse and display logs
            for i, event in enumerate(reversed(events[-50:])):
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message']
                
                # Parse JSON if possible
                try:
                    log_data = json.loads(message)
                    
                    # Extract key information
                    if 'body' in log_data:
                        body = log_data['body']
                        
                        # Detect tool calls
                        if 'get_temperature' in body:
                            icon = "🌡️"
                            title = "get_temperature()"
                        elif 'analyze_heating_rate' in body:
                            icon = "📈"
                            title = "analyze_heating_rate()"
                        elif 'abort_experiment' in body:
                            icon = "🛑"
                            title = "abort_experiment()"
                        elif 'Tool' in body or 'tool' in body:
                            icon = "🔧"
                            title = "Tool Call"
                        else:
                            icon = "📝"
                            title = "Log Entry"
                        
                        with st.expander(f"{icon} {timestamp.strftime('%H:%M:%S')} - {title}", expanded=(i<5)):
                            st.write(f"**Timestamp:** {timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                            
                            # Try to parse as JSON for better formatting
                            try:
                                body_json = json.loads(body)
                                st.json(body_json)
                            except:
                                # Display as wrapped text with line breaks
                                st.text_area("Content", body, height=200, disabled=True)
                    else:
                        with st.expander(f"📝 {timestamp.strftime('%H:%M:%S')} - Log", expanded=False):
                            st.json(log_data)
                except:
                    # Plain text log
                    if message.strip():
                        with st.expander(f"📝 {timestamp.strftime('%H:%M:%S')}", expanded=False):
                            st.text_area("Content", message, height=150, disabled=True)
        else:
            st.info("💡 No recent logs found")
            
    except Exception as e:
        st.error(f"❌ Error fetching logs: {e}")
        st.write("**Troubleshooting:**")
        st.write("- Verify the log group and stream names are correct")
        st.write("- Check IAM permissions for CloudWatch Logs access")

time.sleep(3)
st.rerun()