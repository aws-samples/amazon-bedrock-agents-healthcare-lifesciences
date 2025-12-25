import streamlit as st
import grpc
import time
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'proto'))
from proto import sila2_streaming_pb2
from proto import sila2_streaming_pb2_grpc

st.set_page_config(
    page_title="SiLA2 Temperature Monitor",
    page_icon="🌡️",
    layout="wide"
)

st.title("🌡️ SiLA2 Temperature Monitoring Dashboard")

if 'temperature_data' not in st.session_state:
    st.session_state.temperature_data = []
if 'events' not in st.session_state:
    st.session_state.events = []
if 'last_event_time' not in st.session_state:
    st.session_state.last_event_time = None

@st.cache_resource
def get_grpc_channel():
    grpc_server = os.getenv('GRPC_SERVER', 'localhost:50051')
    return grpc.insecure_channel(grpc_server)

def stream_temperature_data():
    channel = get_grpc_channel()
    stub = sila2_streaming_pb2_grpc.SiLA2DeviceStub(channel)
    
    try:
        request = sila2_streaming_pb2.SubscribeRequest(device_id="hplc")
        for update in stub.SubscribeTemperature(request, timeout=10):
            return {
                'timestamp': datetime.fromisoformat(update.timestamp.replace('Z', '+00:00')),
                'temperature': update.temperature,
                'target_temperature': update.target_temperature,
                'elapsed_seconds': update.elapsed_seconds,
                'scenario_mode': update.scenario_mode
            }
    except grpc.RpcError as e:
        st.error(f"gRPC Error: {e}")
        return None

def check_events():
    channel = get_grpc_channel()
    stub = sila2_streaming_pb2_grpc.SiLA2DeviceStub(channel)
    
    try:
        request = sila2_streaming_pb2.EventRequest(device_id="hplc")
        for event in stub.SubscribeEvents(request, timeout=2):
            return {
                'type': event.event_type,
                'timestamp': datetime.fromisoformat(event.timestamp.replace('Z', '+00:00')).strftime('%H:%M:%S'),
                'temperature': event.temperature,
                'duration': event.duration_seconds
            }
    except:
        return None

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📈 Real-time Temperature Chart")
    
    latest_data = stream_temperature_data()
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
            name='Current Temperature',
            line=dict(color='red', width=3)
        ))
        
        if df['target_temperature'].iloc[-1] > 0:
            fig.add_hline(
                y=df['target_temperature'].iloc[-1],
                line_dash="dash",
                line_color="green",
                annotation_text=f"Target: {df['target_temperature'].iloc[-1]}°C"
            )
        
        fig.update_layout(
            title="Temperature vs Time",
            xaxis_title="Time",
            yaxis_title="Temperature (°C)",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Waiting for temperature data...")

with col2:
    st.subheader("📊 Device Status")
    
    if latest_data:
        st.metric("Current Temperature", f"{latest_data['temperature']:.1f}°C")
        st.metric("Target Temperature", f"{latest_data['target_temperature']:.1f}°C")
        st.metric("Elapsed Time", f"{latest_data['elapsed_seconds']}s")
        
        st.subheader("🎯 Scenario Mode")
        scenario = latest_data.get('scenario_mode', 'scenario_1')
        if scenario == 'scenario_1':
            st.info("🔵 Scenario 1 (Normal: 10°C/min)")
        else:
            st.warning("🟡 Scenario 2 (Slow: 2°C/min)")
        
        if latest_data['target_temperature'] > 25:
            progress = min((latest_data['temperature'] - 25) / (latest_data['target_temperature'] - 25), 1.0)
            st.progress(progress)
            st.caption(f"Progress: {progress*100:.1f}%")
    
    st.subheader("📋 Event Timeline")
    
    new_event = check_events()
    if new_event:
        event_key = f"{new_event['type']}_{new_event['timestamp']}"
        if st.session_state.last_event_time != event_key:
            st.session_state.events.append(new_event)
            st.session_state.last_event_time = event_key
            if len(st.session_state.events) > 10:
                st.session_state.events = st.session_state.events[-10:]
    
    if st.session_state.events:
        for event in st.session_state.events[-5:]:
            if event['type'] == 'TEMPERATURE_REACHED':
                st.success(f"✅ Target reached at {event['timestamp']} ({event['duration']}s)")
            elif event['type'] == 'HEATER_MALFUNCTION':
                st.error(f"⚠️ Heater malfunction at {event['timestamp']}")
    else:
        st.info("No events yet")

time.sleep(5)
st.rerun()
