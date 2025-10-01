import streamlit as st
import os
from dotenv import load_dotenv
import base64

# Load environment variables from .env file for local development
load_dotenv()
from agents.medical_coordinator import MedicalCoordinator
from config_file import ENABLE_AUTHENTICATION, AWS_DEFAULT_REGION
import tools.device_status
import tools.pubmed_search
import tools.clinical_trials
from strands_tools import calculator, current_time

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Basic Authentication check
def check_authentication():
    if not ENABLE_AUTHENTICATION:
        return True
    
    # Get Basic Auth configuration from environment variables
    auth_type = os.getenv('AUTH_TYPE', 'basic')
    username = os.getenv('BASIC_AUTH_USERNAME')
    password = os.getenv('BASIC_AUTH_PASSWORD')
    
    if not username or not password:
        st.error("⚠️ Authentication credentials not configured. Please set BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD environment variables.")
        st.stop()
    
    if auth_type != 'basic':
        return True  # Skip auth if not basic auth
    
    # Check if already authenticated
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        # Add logout functionality in sidebar
        with st.sidebar:
            # Sanitize username display to prevent XSS
            safe_username = st.session_state.username.replace('<', '&lt;').replace('>', '&gt;')
            st.success(f"🔐 Logged in as: {safe_username}")
            if st.button("🚪 Logout", key="logout_btn"):
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        return True
    
    # Show login form
    st.title("🔐 Login Required")
    st.write("Please enter your credentials to access the Medical Device Management System.")
    
    with st.form("login_form"):
        input_username = st.text_input("Username")
        input_password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            # Sanitize inputs to prevent XSS
            clean_username = input_username.replace('<', '&lt;').replace('>', '&gt;') if input_username else ''
            if clean_username == username and input_password == password:
                st.session_state.authenticated = True
                st.session_state.username = clean_username
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
                st.stop()
    
    st.stop()
    return False

# Check authentication before proceeding
check_authentication()

# Add title on the page
st.title("🏥 Medical Device Management System")
st.write("AI-powered assistant for medical device monitoring, literature research, and clinical trials information.")

# Display authentication status
if ENABLE_AUTHENTICATION and 'username' in st.session_state:
    # Sanitize username display to prevent XSS
    safe_username = st.session_state.username.replace('<', '&lt;').replace('>', '&gt;')
    st.info(f"👤 **Authenticated User:** {safe_username}")
elif not ENABLE_AUTHENTICATION:
    st.warning("⚠️ **Development Mode:** Authentication disabled")

# Sample questions
st.subheader("Sample Questions:")
col1, col2 = st.columns(2)
with col1:
    if st.button("What's the status of device DEV001?"):
        st.session_state.sample_query = "What's the status of device DEV001?"
        st.rerun()
    if st.button("List all medical devices"):
        st.session_state.sample_query = "List all medical devices"
        st.rerun()
with col2:
    if st.button("Search PubMed for MRI safety protocols"):
        st.session_state.sample_query = "Search PubMed for MRI safety protocols"
        st.rerun()
    if st.button("Find clinical trials for cardiac devices"):
        st.session_state.sample_query = "Find clinical trials for cardiac devices"
        st.rerun()

# Initialize the medical coordinator agent (cached)
@st.cache_resource
def get_agent():
    return MedicalCoordinator(
        tools=[
            current_time,
            calculator,
            tools.device_status.get_device_status,
            tools.device_status.list_all_devices,
            tools.pubmed_search.search_pubmed,
            tools.clinical_trials.search_clinical_trials,
        ]
    )

if "agent" not in st.session_state:
    st.session_state.agent = get_agent()

# Display old chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.empty()  # Workaround for Streamlit container rendering issue in chat history
        if message.get("type") == "tool_use":
            st.code(message["content"])
        else:
            st.markdown(message["content"])

# Handle sample query selection
if "sample_query" in st.session_state:
    prompt = st.session_state.sample_query
    del st.session_state.sample_query
else:
    prompt = None

# Always render chat input
chat_prompt = st.chat_input("Ask about medical devices, literature, or clinical trials...")

# Process either sample query or chat input
if prompt or chat_prompt:
    if not prompt:
        prompt = chat_prompt
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Clear previous tool usage details
    if "details_placeholder" in st.session_state:
        st.session_state.details_placeholder.empty()
    
    # Display user message (sanitized to prevent XSS)
    with st.chat_message("user"):
        safe_prompt = prompt.replace('<', '&lt;').replace('>', '&gt;') if prompt else ''
        st.write(safe_prompt)

    # Prepare containers for response
    with st.chat_message("assistant"):
        st.session_state.details_placeholder = st.empty()  # Create a new placeholder
    
    # Clear previous output for new conversation
    st.session_state.output = []

    # Create the callback handler to display streaming responses
    def custom_callback_handler(**kwargs):
        def add_to_output(output_type, content, append = True):
            if len(st.session_state.output) == 0:
                st.session_state.output.append({"type": output_type, "content": content})
            else:
                last_item = st.session_state.output[-1]
                if last_item["type"] == output_type:
                    if append:
                        st.session_state.output[-1]["content"] += content
                    else:
                        st.session_state.output[-1]["content"] = content
                else:
                    st.session_state.output.append({"type": output_type, "content": content})

        with st.session_state.details_placeholder.container():
            # Process stream data
            if "data" in kwargs:
                add_to_output("data", kwargs["data"])
            elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
                tool_use_msg = "Using tool: " + kwargs["current_tool_use"]["name"] + " with args: " + str(kwargs["current_tool_use"]["input"])
                add_to_output("tool_use", tool_use_msg, append = False)
            elif "reasoningText" in kwargs:
                add_to_output("reasoning", kwargs["reasoningText"])

            # Display output
            for output_item in st.session_state.output:
                if output_item["type"] == "data":
                    st.markdown(output_item["content"])
                elif output_item["type"] == "tool_use":
                    st.code(output_item["content"])
                elif output_item["type"] == "reasoning":
                    st.markdown(output_item["content"])
    
    # Set callback handler into the agent
    st.session_state.agent.callback_handler = custom_callback_handler
    
    # Get response from agent
    response = st.session_state.agent(prompt)

    # When done, add assistant messages to chat history
    for output_item in st.session_state.output:
            st.session_state.messages.append({"role": "assistant", "type": output_item["type"] , "content": output_item["content"]})