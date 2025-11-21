#!/usr/bin/env python3
"""
SiLA2 Lab Automation Agent - Phase 3 Streamlit Test UI
"""
import streamlit as st
import json
import subprocess
import os
from datetime import datetime

st.set_page_config(
    page_title="SiLA2 Lab Automation - Phase 3",
    page_icon="🧪",
    layout="wide"
)

if 'messages' not in st.session_state:
    st.session_state.messages = []

def invoke_agentcore(prompt: str) -> dict:
    """Invoke AgentCore Runtime with pyenv"""
    try:
        os.chdir('/home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/32-sila2-lab-automation-agent')
        
        cmd = f'''export PATH="$HOME/.pyenv/bin:$PATH" && eval "$(pyenv init -)" && eval "$(pyenv virtualenv-init -)" && agentcore invoke '{{"prompt": "{prompt}"}}\''''
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            output = result.stdout
            if "Response:" in output:
                response_part = output.split("Response:")[1].strip()
                try:
                    response_json = json.loads(response_part)
                    return {"success": True, "data": response_json, "raw_output": output}
                except:
                    return {"success": True, "data": {"raw": response_part}, "raw_output": output}
            return {"success": True, "data": {"raw": output}, "raw_output": output}
        else:
            return {"success": False, "error": result.stderr, "raw_output": result.stdout}
    except Exception as e:
        return {"success": False, "error": str(e), "raw_output": ""}

def format_response(response_data: dict) -> str:
    """Format AgentCore response for display"""
    if not response_data:
        return "No response data"
    
    # Extract response content
    response_list = response_data.get("response", [])
    if response_list:
        response_text = response_list[0]
        # Clean up byte string format
        if isinstance(response_text, str) and response_text.startswith("b'"):
            response_text = response_text[2:-1].replace('\\\\n', '\n').replace('\\"', '"')
        return response_text
    
    # Fallback to raw data
    return str(response_data.get("raw", "No content"))

def display_response_details(result: dict):
    """Display detailed response information"""
    if result["success"]:
        data = result["data"]
        
        # Main response
        formatted_response = format_response(data)
        st.markdown(formatted_response)
        
        # Response details in expander
        with st.expander("📋 Response Details"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Response Metadata")
                if "ResponseMetadata" in data:
                    metadata = data["ResponseMetadata"]
                    st.json({
                        "RequestId": metadata.get("RequestId", "N/A"),
                        "HTTPStatusCode": metadata.get("HTTPStatusCode", "N/A"),
                        "RetryAttempts": metadata.get("RetryAttempts", "N/A")
                    })
                
                st.subheader("Session Info")
                st.json({
                    "RuntimeSessionId": data.get("runtimeSessionId", "N/A")[:20] + "..." if data.get("runtimeSessionId") else "N/A",
                    "StatusCode": data.get("statusCode", "N/A"),
                    "ContentType": data.get("contentType", "N/A")
                })
            
            with col2:
                st.subheader("Raw Response")
                if "raw_output" in result:
                    st.text_area("Full Output", result["raw_output"], height=200)
                
                st.subheader("Trace Info")
                if "traceId" in data:
                    st.code(data["traceId"][:50] + "..." if len(data["traceId"]) > 50 else data["traceId"])
    else:
        st.error(f"❌ Error: {result['error']}")
        if "raw_output" in result and result["raw_output"]:
            with st.expander("Debug Output"):
                st.text_area("Raw Output", result["raw_output"], height=150)

def execute_quick_test(prompt_text):
    """Execute quick test and display results"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Add user message
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt_text,
        "timestamp": timestamp
    })
    
    # Execute command
    result = invoke_agentcore(prompt_text)
    
    # Format and add assistant response
    if result["success"]:
        formatted_content = format_response(result["data"])
    else:
        formatted_content = f"Error: {result['error']}"
    
    response_time = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({
        "role": "assistant", 
        "content": formatted_content,
        "timestamp": response_time,
        "details": result
    })

# UI
st.title("🧪 SiLA2 Lab Automation Agent")
st.markdown("**Phase 3: AgentCore Runtime Test**")

# Sidebar
with st.sidebar:
    st.header("🔧 Phase 3 Status")
    st.success("✅ AgentCore Runtime: READY")
    st.success("✅ BedrockAgentCoreApp: Active")
    st.success("✅ SiLA2 Tools: Available")
    
    st.markdown("---")
    st.subheader("📋 Test Devices")
    for device in ["HPLC-01", "CENTRIFUGE-01", "PIPETTE-01"]:
        st.markdown(f"• {device}")

# Main interface
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat Interface")
    
    # Display messages
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"**👤 User:** {msg['content']}")
        else:
            st.markdown(f"**🤖 Assistant:** {msg['content']}")
        st.caption(f"⏰ {msg['timestamp']}")
        
        # Show details for assistant messages
        if msg["role"] == "assistant" and "details" in msg:
            with st.expander("🔍 View Details", expanded=False):
                details = msg["details"]
                if details["success"]:
                    data = details["data"]
                    st.json({
                        "Status": data.get("statusCode", "N/A"),
                        "Session": data.get("runtimeSessionId", "N/A")[:20] + "..." if data.get("runtimeSessionId") else "N/A",
                        "Request ID": data.get("ResponseMetadata", {}).get("RequestId", "N/A")
                    })
                else:
                    st.error(f"Error: {details['error']}")
        
        st.markdown("---")

    # Command input
    prompt = st.text_input("Enter command:", key="command_input")
    if st.button("Send") and prompt:
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        st.session_state.messages.append({
            "role": "user", 
            "content": prompt,
            "timestamp": timestamp
        })
        
        st.markdown(f"**👤 User:** {prompt}")
        st.caption(f"⏰ {timestamp}")
        
        st.markdown("**🤖 Assistant:**")
        with st.spinner("Processing..."):
            result = invoke_agentcore(prompt)
        
        # Display response with details
        display_response_details(result)
        
        response_time = datetime.now().strftime("%H:%M:%S")
        st.caption(f"⏰ {response_time}")
        st.markdown("---")
        
        # Store formatted response in session
        if result["success"]:
            formatted_content = format_response(result["data"])
        else:
            formatted_content = f"Error: {result['error']}"
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": formatted_content,
            "timestamp": response_time,
            "details": result
        })

with col2:
    st.subheader("🎮 Quick Tests")
    
    if st.button("📋 List Devices", use_container_width=True):
        execute_quick_test("List all available SiLA2 devices")
        st.experimental_rerun()
    
    if st.button("🔍 Check HPLC", use_container_width=True):
        execute_quick_test("Get status of HPLC-01")
        st.experimental_rerun()
    
    if st.button("🌀 Check Centrifuge", use_container_width=True):
        execute_quick_test("Check CENTRIFUGE-01 status")
        st.experimental_rerun()
    
    if st.button("❓ Help", use_container_width=True):
        execute_quick_test("What can you do?")
        st.experimental_rerun()
    
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.messages = []
        st.experimental_rerun()

st.markdown("---")
st.markdown("**Agent**: `sila2_runtime_new-s8iJWs4hOY` | **Status**: ✅ Ready")