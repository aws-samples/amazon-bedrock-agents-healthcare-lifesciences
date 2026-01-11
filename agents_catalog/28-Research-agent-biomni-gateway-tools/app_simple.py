"""Simple Streamlit app without OAuth for testing"""
import sys
import streamlit as st
from bedrock_agentcore import BedrockAgentCoreClient

# Parse agent name
agent_name = "researchappAgent"
for arg in sys.argv:
    if arg.startswith("--agent="):
        agent_name = arg.split("=")[1]

st.set_page_config(layout="wide")
st.title("Research Agent with Biomni Gateway")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask Research Agent questions!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        try:
            # Use OAuth token (mock for now - will use Cognito token)
            client = BedrockAgentCoreClient(region_name="us-west-2")
            
            response = client.invoke_agent_runtime(
                agentName=agent_name,
                sessionId=st.session_state.session_id,
                inputText=prompt,
                bearerToken="test"  # This needs real OAuth token
            )
            
            assistant_response = ""
            for event in response:
                if "chunk" in event:
                    chunk_text = event["chunk"].get("bytes", b"").decode("utf-8")
                    assistant_response += chunk_text
            
            st.markdown(assistant_response)
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
