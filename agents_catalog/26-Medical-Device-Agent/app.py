import streamlit as st


from agents.medical_coordinator import MedicalCoordinator
import tools.device_status
import tools.pubmed_search
import tools.clinical_trials
from strands_tools import calculator, current_time

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Authentication disabled for this deployment
if False:
    # Initialise CognitoAuthenticator
    authenticator = Auth.get_authenticator(secrets_manager_id, region)

    # Authenticate user, and stop here if not logged in
    is_logged_in = authenticator.login()
    if not is_logged_in:
        st.stop()

    def logout():
        authenticator.logout()

    with st.sidebar:
        st.text(f"Welcome,\n{authenticator.get_username()}")
        st.button("Logout", "logout_btn", on_click=logout)

# Add title on the page
st.title("Medical Device Management System")
st.write("AI-powered assistant for medical device monitoring, literature research, and clinical trials information.")

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
        st.empty()  # This forces the container to render without adding visible content (workaround for streamlit bug)
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
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)

    # Prepare containers for response
    with st.chat_message("assistant"):
        st.session_state.details_placeholder = st.empty()  # Create a new placeholder
    
    # Initialize strings to store streaming of model output
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
            current_streaming_tool_use = ""
            # Process stream data
            if "data" in kwargs:
                add_to_output("data", kwargs["data"])
            elif "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
                tool_use_id = kwargs["current_tool_use"].get("toolUseId")
                current_streaming_tool_use = "Using tool: " + kwargs["current_tool_use"]["name"] + " with args: " + str(kwargs["current_tool_use"]["input"])
                add_to_output("tool_use", current_streaming_tool_use, append = False)
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