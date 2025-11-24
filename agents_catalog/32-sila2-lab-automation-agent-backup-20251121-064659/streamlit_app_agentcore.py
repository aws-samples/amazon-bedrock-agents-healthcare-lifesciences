"""
Streamlit UI for SiLA2 Lab Automation Agent - Phase 2 AgentCore
"""

import streamlit as st
import json
import subprocess
import os
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SiLA2 Lab Automation Agent",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'execution_history' not in st.session_state:
    st.session_state.execution_history = []

def add_to_history(action: str, result: str):
    """Add execution to history"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.execution_history.append({
        "time": timestamp,
        "action": action,
        "result": result
    })

def invoke_agentcore(prompt: str) -> dict:
    """Invoke AgentCore Runtime"""
    try:
        # Change to project directory
        os.chdir('/home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/32-sila2-lab-automation-agent')
        
        # Activate virtual environment and invoke
        cmd = f'source .venv/bin/activate && agentcore invoke \'{{"prompt": "{prompt}"}}\''
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Parse the response
            output = result.stdout
            if "Response:" in output:
                response_part = output.split("Response:")[1].strip()
                try:
                    response_json = json.loads(response_part)
                    return {"success": True, "data": response_json}
                except:
                    return {"success": True, "data": {"raw": response_part}}
            else:
                return {"success": True, "data": {"raw": output}}
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Main UI
st.title("🧪 SiLA2 Lab Automation Agent")
st.markdown("**Phase 2: AgentCore Gateway Integration**")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("🔧 Phase 2 Status")
    st.markdown("""
    - ✅ AgentCore Runtime: READY
    - ✅ Gateway Integration: Active
    - ✅ SiLA2 Tools: Available
    - ✅ Device Control: Operational
    """)
    
    st.markdown("---")
    st.subheader("📋 Available Devices")
    devices = ["HPLC-01", "CENTRIFUGE-01", "PIPETTE-01"]
    for device in devices:
        st.markdown(f"• {device}")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    # AgentCore Status
    st.subheader("🤖 AgentCore Runtime Status")
    
    if st.button("🔍 Check AgentCore Status", use_container_width=True):
        with st.spinner("Checking AgentCore status..."):
            try:
                os.chdir('/home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/32-sila2-lab-automation-agent')
                result = subprocess.run('source .venv/bin/activate && agentcore status', 
                                      shell=True, capture_output=True, text=True)
                if "READY" in result.stdout:
                    st.success("✅ AgentCore Runtime is READY")
                    add_to_history("Check AgentCore Status", "READY")
                else:
                    st.warning("⚠️ AgentCore Runtime status unclear")
                    st.code(result.stdout)
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")
    
    # Device Operations
    st.subheader("🎛️ SiLA2 Device Operations")
    
    # Quick device list
    if st.button("📋 List All Devices", use_container_width=True):
        with st.spinner("Listing SiLA2 devices..."):
            result = invoke_agentcore("List all available SiLA2 devices")
            if result["success"]:
                st.success("✅ Devices retrieved successfully!")
                response_data = result["data"].get("response", [])
                if response_data:
                    # Extract the actual response text
                    response_text = response_data[0] if response_data else "No response"
                    if isinstance(response_text, str) and response_text.startswith("b'"):
                        # Clean up the byte string format
                        response_text = response_text[2:-1].replace('\\\\n', '\n').replace('\\"', '"')
                    st.info(response_text)
                add_to_history("List All Devices", "Success")
            else:
                st.error(f"❌ Error: {result['error']}")
                add_to_history("List All Devices", "Failed")

    # Device selection and status
    col1a, col1b = st.columns([1, 1])
    with col1a:
        selected_device = st.selectbox(
            "Select Device",
            ["HPLC-01", "CENTRIFUGE-01", "PIPETTE-01"]
        )
    
    with col1b:
        if st.button("📊 Get Device Status", use_container_width=True):
            with st.spinner(f"Getting {selected_device} status..."):
                result = invoke_agentcore(f"Get status of {selected_device}")
                if result["success"]:
                    st.success("✅ Status retrieved!")
                    response_data = result["data"].get("response", [])
                    if response_data:
                        response_text = response_data[0] if response_data else "No response"
                        if isinstance(response_text, str) and response_text.startswith("b'"):
                            response_text = response_text[2:-1].replace('\\\\n', '\n').replace('\\"', '"')
                        st.info(response_text)
                    add_to_history(f"Get {selected_device} Status", "Success")
                else:
                    st.error(f"❌ Error: {result['error']}")
                    add_to_history(f"Get {selected_device} Status", "Failed")

    # Custom prompt
    st.subheader("💬 Custom Prompt")
    custom_prompt = st.text_area(
        "Enter your prompt:",
        value="What is the current status of all laboratory devices?",
        height=100
    )
    
    if st.button("🚀 Execute Prompt", use_container_width=True):
        if custom_prompt:
            with st.spinner("Processing prompt..."):
                result = invoke_agentcore(custom_prompt)
                if result["success"]:
                    st.success("✅ Prompt executed successfully!")
                    response_data = result["data"].get("response", [])
                    if response_data:
                        response_text = response_data[0] if response_data else "No response"
                        if isinstance(response_text, str) and response_text.startswith("b'"):
                            response_text = response_text[2:-1].replace('\\\\n', '\n').replace('\\"', '"')
                        with st.expander("📋 Response Details"):
                            st.write(response_text)
                    add_to_history("Custom Prompt", "Success")
                else:
                    st.error(f"❌ Error: {result['error']}")
                    add_to_history("Custom Prompt", "Failed")
        else:
            st.warning("Please enter a prompt")

    # Quick Actions
    st.subheader("⚡ Quick Actions")
    
    col2a, col2b, col2c = st.columns(3)
    with col2a:
        if st.button("🔍 Device Info", use_container_width=True):
            with st.spinner("Getting device information..."):
                result = invoke_agentcore(f"Tell me about the {selected_device} device")
                if result["success"]:
                    st.success("✅ Device info retrieved!")
                    add_to_history(f"Get {selected_device} Info", "Success")
                else:
                    st.error("❌ Failed to get device info")
    
    with col2b:
        if st.button("🌡️ Check Temperature", use_container_width=True):
            with st.spinner("Checking temperature..."):
                result = invoke_agentcore(f"What is the temperature of {selected_device}?")
                if result["success"]:
                    st.success("✅ Temperature checked!")
                    add_to_history(f"Check {selected_device} Temperature", "Success")
                else:
                    st.error("❌ Failed to check temperature")
    
    with col2c:
        if st.button("📈 System Status", use_container_width=True):
            with st.spinner("Getting system status..."):
                result = invoke_agentcore("Give me an overview of the laboratory system status")
                if result["success"]:
                    st.success("✅ System status retrieved!")
                    add_to_history("System Status", "Success")
                else:
                    st.error("❌ Failed to get system status")

with col2:
    # Execution History
    st.subheader("📋 Execution History")
    
    if st.button("🗑️ Clear History"):
        st.session_state.execution_history = []
        st.rerun()
    
    if st.session_state.execution_history:
        for entry in reversed(st.session_state.execution_history[-10:]):
            with st.container():
                st.markdown(f"**{entry['time']}**")
                st.markdown(f"🔸 {entry['action']}")
                if entry['result'] == "Success":
                    st.markdown("✅ Success")
                else:
                    st.markdown(f"❌ {entry['result']}")
                st.markdown("---")
    else:
        st.info("No execution history yet. Try some commands!")

# Footer
st.markdown("---")
st.markdown("**Phase 2 Status**: ✅ AgentCore Gateway Integration Complete")
st.markdown("*SiLA2 Lab Automation Agent - AWS Healthcare & Life Sciences Agents Toolkit*")