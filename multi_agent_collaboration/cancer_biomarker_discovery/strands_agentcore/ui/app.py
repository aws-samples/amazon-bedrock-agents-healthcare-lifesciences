import streamlit as st
import time
import boto3
import uuid
import re
from botocore.exceptions import EventStreamError
import json
import os
import tempfile
import sys
import traceback
from typing import Iterator, Optional
from streamlit.logger import get_logger

temp_dir = tempfile.mkdtemp()

logger = get_logger(__name__)
logger.setLevel("INFO")

def find_s3_bucket_name_by_suffix(name_suffix: str) -> Optional[str]:
    """Find S3 bucket name by name suffix"""
    client = boto3.client('s3')
    
    response = client.list_buckets()
    for bucket in response['Buckets']:
        if bucket['Name'].endswith(name_suffix):
            return bucket['Name']
    return None

# Get AWS region
session = boto3.Session()
region = session.region_name

# Define variables for agent usage metrics
input_tokens = 0
output_tokens = 0
latency = 0

ssm_client = boto3.client('ssm')

# Retrieve bucket information
s3_bucket_name = find_s3_bucket_name_by_suffix('-agent-build-bucket')
if not s3_bucket_name:
    print("Error: S3 bucket with suffix '-agent-build-bucket' not found!")

def fetch_agent_runtimes():
        try:
            agentcore_client = boto3.client('bedrock-agentcore-control', region_name=region)
            response = agentcore_client.list_agent_runtimes(maxResults=50)

            # Filter only READY agents and sort by name
            ready_agents = [
                agent
                for agent in response.get("agentRuntimes", [])
                if agent.get("status") == "READY"
            ]

            # Sort by most recent update time (newest first)
            ready_agents.sort(key=lambda x: x.get("lastUpdatedAt", ""), reverse=True)

            return ready_agents
        except Exception as e:
            st.error(f"Error fetching agent runtimes: {str(e)}")
            return None

def list_png_files():
        try:
            s3_client = boto3.client('s3')
            prefix = 'nsclc_radiogenomics/PNG/'
            response = s3_client.list_objects_v2(Bucket=s3_bucket_name, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].lower().endswith('.png')]
        except Exception as e:
            st.error(f"Error listing image: {str(e)}")
            return None


def fetch_s3_image(bucket: str, key: str) -> Optional[bytes]:
    """Download an image from S3 and return its bytes."""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Error fetching image from S3: s3://{bucket}/{key} - {e}")
        return None

def display_s3_images_from_text(text: str):
    """Extract S3 image paths from text and display them inline."""
    for match in re.finditer(r's3://([^/\s]+)/(\S+\.(?:png|jpg|jpeg|gif))', text, re.IGNORECASE):
        bucket, key = match.group(1), match.group(2)
        image_data = fetch_s3_image(bucket, key)
        if image_data:
            st.image(image_data, caption=os.path.basename(key), width="stretch")

def display_subject_images(text: str):
    """Extract subject IDs from tool results and display matching medical images inline."""
    # Match R01-083 style IDs anywhere in the text (covers JSON, escaped quotes, plain text)
    subject_ids = list(set(re.findall(r'R\d+-\d+', text)))
    if not subject_ids:
        return
    png_files = list_png_files() or []
    for subject_id in subject_ids:
        matching = [f for f in png_files if subject_id in f]
        for file_key in matching:
            image_data = fetch_s3_image(s3_bucket_name, file_key)
            if image_data:
                st.image(image_data, caption=f"{subject_id} - {os.path.basename(file_key)}", width="stretch")

def new_session():
    st.session_state["SESSION_ID"] = str(uuid.uuid1())

def invoke_agent_streaming(
    prompt: str,
    agent_arn: str,
    session_id: str,
    region: str
) -> Iterator[str]:   
    
    # Retrieve agentcore client with extended timeout for long-running agent calls
    from botocore.config import Config
    client = boto3.client(
        'bedrock-agentcore',
        region_name=region,
        config=Config(read_timeout=300)
    )

    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            runtimeSessionId=session_id,
            qualifier="DEFAULT",
            payload=json.dumps({"prompt": prompt})
        )

        # Handle streaming response
        for line in response["response"].iter_lines(chunk_size=1):
            if line:
                line = line.decode("utf-8")
                logger.debug(f"Raw line: {line}")

                if line.startswith("data: "):
                    line = line[6:]
                    data = json.loads(line)
                    data = json.loads(data)

                    # Parse each chunk and display only what is relevant
                    if "data" in data:
                        yield { 'text': data.get("data") }
                    elif "current_tool_use" in data:
                        # Yield as streaming tool — the UI will update in-place
                        yield { 'tool_streaming': data["current_tool_use"] }
                    elif "event" in data:
                        logger.debug(f"EVENT: {data.get('event')}")
                    elif "message" in data:
                        if "content" in data["message"]:
                            for obj in data["message"]["content"]:
                                if "toolResult" in obj:
                                    yield { 'tool': obj }
                                    logger.debug(f"TOOL RESULT: {obj['toolResult']['content'][0]['text']}")
                        logger.debug(f"MESSAGE: {data.get('message')}")
                    elif "result" in data:
                        logger.debug(f"RESULT: {data.get('result')}")
                        yield { 'metric': data }
                else:
                    logger.debug(f"Line doesn't start with 'data: ', skipping: {line}")
                
    except Exception as e:
        print(f"AgentCore error: {e}")
        raise e
    
st.set_page_config(layout="wide", page_title="Biomarker Agent", menu_items={"Get help": None, "Report a Bug": None, "About": None})

# Custom CSS
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("Agent Selection")

    # Fetch available agents
    with st.spinner("Loading available agents..."):
        available_agents = fetch_agent_runtimes()

    if available_agents:
        name_to_arn = {item['agentRuntimeName']: item['agentRuntimeArn'] for item in available_agents}
        selected_agent_name = st.selectbox('Select an agent runtime:', list(name_to_arn.keys()))
        selected_agent_arn = name_to_arn[selected_agent_name]

        # Clear chat when agent changes
        if st.session_state.get("current_agent") != selected_agent_name:
            st.session_state["current_agent"] = selected_agent_name
            st.session_state["messages"] = []
            new_session()
    else:
        st.error("No agent runtimes found or error loading agents")

    if st.button("New Chat"):
        st.session_state["messages"] = []
        new_session()
        st.rerun()

    # Response formatting options
    st.header("Display Options")
    show_tools = st.checkbox(
        "Show tools",
        value=True,
        help="Display tools used",
    )
    show_metrics = st.checkbox(
        "Show metrics",
        value=False,
        help="Display metrics used",
    )

    st.divider()
    st.link_button("GitHub", "https://github.com/aws-samples/amazon-bedrock-agents-cancer-biomarker-discovery")

# Main content
st.title("Biomarker Research Agent with Amazon Bedrock AgentCore")

# Sample questions
questions = [
    "How many patients with diagnosis age greater than 50 years and what are their smoking status",
    "What is the average age of patients diagnosed with Adenocarcinoma",
    "Can you search pubmed for evidence around the effects of biomarker use in oncology on clinical trial failure risk",
    "Can you search pubmed for FDA approved biomarkers for non small cell lung cancer",
    "What is the best gene biomarker (lowest p value) with overall survival for patients that have undergone chemotherapy, graph the top 5 biomarkers in a bar chart",
    "Show me a Kaplan Meier chart for biomarker with name 'gdf15' for chemotherapy patients by grouping expression values less than 10 and greater than 10",
    "According to literature evidence, what metagene cluster does gdf15 belong to",
    "According to literature evidence, what properties of the tumor are associated with metagene 19 activity and EGFR pathway",
    "Can you compute the imaging biomarkers for the 2 patients with the lowest gdf15 expression values",
    "Can you highlight the elongation and sphericity of the tumor with these patients ? can you depict the images of them"
]

with st.expander("Sample questions"):
    for i, q in enumerate(questions, 1):
        st.markdown(f"{i}. {q}")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "SESSION_ID" not in st.session_state:
    new_session()

if "agent_running" not in st.session_state:
    st.session_state.agent_running = False

session_id = st.session_state["SESSION_ID"]

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "user" in message["role"]:
            st.markdown(message["content"])
        else:
            content = message["content"]
            try:
                # Pre-process: deduplicate consecutive tool chunks, keeping only the last per run
                deduplicated = []
                for chunk in content:
                    if "tool" in chunk and "toolResult" not in chunk.get("tool", {}):
                        # Replace previous consecutive tool chunk (streaming accumulation)
                        if deduplicated and "tool" in deduplicated[-1] and "toolResult" not in deduplicated[-1].get("tool", {}):
                            deduplicated[-1] = chunk
                        else:
                            deduplicated.append(chunk)
                    else:
                        deduplicated.append(chunk)

                accumulated_text = ""
                for chunk in deduplicated:
                    if "tool" in chunk:
                        if accumulated_text:
                            st.markdown(accumulated_text)
                            accumulated_text = ""
                        if "toolResult" in chunk["tool"]:
                            tool_result = chunk["tool"]["toolResult"]["content"][0]["text"]
                            if show_tools:
                                with st.container(border=True):
                                    st.markdown(f"🔧 Tool result: {tool_result}")
                            display_s3_images_from_text(tool_result)
                            display_subject_images(tool_result)
                        elif show_tools:
                            with st.container(border=True):
                                st.markdown(f"🔧 **{chunk['tool']['name']}**")
                                tool_input = chunk["tool"]["input"]
                                if isinstance(tool_input, dict):
                                    st.markdown(f"Tool input: {json.dumps(tool_input, indent=2)}")
                                else:
                                    try:
                                        tool_input_json = json.loads(tool_input)
                                        st.markdown(f"Tool input: {json.dumps(tool_input_json, indent=2)}")
                                    except Exception:
                                        st.markdown(f"Tool input: {tool_input}")
                    elif "metric" in chunk and show_metrics:
                        if accumulated_text:
                            st.markdown(accumulated_text)
                            accumulated_text = ""
                        input_tokens = chunk["metric"]["result"]["metrics"]["accumulated_usage"]["inputTokens"]
                        output_tokens = chunk["metric"]["result"]["metrics"]["accumulated_usage"]["outputTokens"]
                        latency = chunk["metric"]["result"]["metrics"]["accumulated_metrics"]["latencyMs"]
                        with st.container(border=True):
                            st.markdown("📊 Metrics")
                            st.markdown("Total Input Tokens: " + str(input_tokens))
                            st.markdown("Total Output Tokens: " + str(output_tokens))
                            st.markdown("Total Latency: " + str(latency) + "ms")
                    elif "text" in chunk:
                        accumulated_text += chunk["text"]
                if accumulated_text:
                    st.markdown(accumulated_text)
                    display_subject_images(accumulated_text)
            except Exception:
                print("Error rendering chat history")
                traceback.print_exc()
                st.markdown(message["content"])


# Accept user input
def on_submit():
    st.session_state.agent_running = True

prompt = st.chat_input("How can I help?", disabled=st.session_state.agent_running, on_submit=on_submit)

if prompt:
    # Add user message to chat history
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        chunk_buffer = []

        try:
            # Stream the response
            full_text = ""
            text_placeholder = st.empty()

            tool_placeholder = None
            tool_container = None

            spinner_placeholder = st.empty()
            spinner_placeholder.status("Thinking...", state="running")

            for chunk in invoke_agent_streaming(prompt, selected_agent_arn, session_id, region):
                logger.debug(f"received chunk ({type(chunk)}): {chunk}")
                spinner_placeholder.empty()

                if "tool_streaming" in chunk:
                    tool_data = chunk["tool_streaming"]
                    # Save final version to buffer (replace previous streaming chunks)
                    chunk_buffer = [c for c in chunk_buffer if "tool_streaming" not in c]
                    chunk_buffer.append({"tool": tool_data})
                    if show_tools:
                        # Flush accumulated text before showing tool
                        if full_text:
                            text_placeholder.markdown(full_text)
                            full_text = ""
                            text_placeholder = st.empty()
                        # Create container once, then update placeholder in-place
                        if tool_container is None:
                            tool_container = st.container(border=True)
                            with tool_container:
                                st.markdown(f"🔧 **{tool_data['name']}**")
                                tool_placeholder = st.empty()
                        tool_input = tool_data["input"]
                        if isinstance(tool_input, dict):
                            tool_placeholder.markdown(f"Tool input: {json.dumps(tool_input, indent=2)}")
                        else:
                            try:
                                tool_input_json = json.loads(tool_input)
                                tool_placeholder.markdown(f"Tool input: {json.dumps(tool_input_json, indent=2)}")
                            except Exception:
                                tool_placeholder.markdown(f"Tool input: {tool_input}")
                    continue

                # Non-tool chunk: reset tool placeholder for next tool
                if tool_container is not None:
                    tool_container = None
                    tool_placeholder = None
                    text_placeholder = st.empty()

                # Add chunk to buffer
                chunk_buffer.append(chunk)

                if "text" in chunk:
                    full_text += chunk["text"]
                    text_placeholder.markdown(full_text + "▌")
                elif "tool" in chunk:
                    # Tool results (not streaming tool_use)
                    if full_text:
                        text_placeholder.markdown(full_text)
                        full_text = ""
                        text_placeholder = st.empty()
                    if "toolResult" in chunk["tool"]:
                        tool_result = chunk["tool"]["toolResult"]["content"][0]["text"]
                        if show_tools:
                            with st.container(border=True):
                                st.markdown(f"🔧 Tool result: {tool_result}")
                        display_s3_images_from_text(tool_result)
                        display_subject_images(tool_result)
                    text_placeholder = st.empty()
                elif "metric" in chunk and show_metrics:
                    # Flush accumulated text before showing metrics
                    if full_text:
                        text_placeholder.markdown(full_text)
                        full_text = ""
                        text_placeholder = st.empty()
                    input_tokens = chunk["metric"]["result"]["metrics"]["accumulated_usage"]["inputTokens"]
                    output_tokens = chunk["metric"]["result"]["metrics"]["accumulated_usage"]["outputTokens"]
                    latency = chunk["metric"]["result"]["metrics"]["accumulated_metrics"]["latencyMs"]
                    with st.container(border=True):
                        st.markdown("📊 Metrics")
                        st.markdown("Total Input Tokens: " + str(input_tokens))
                        st.markdown("Total Output Tokens: " + str(output_tokens))
                        st.markdown("Total Latency: " + str(latency) + "ms")

            # Render final text without cursor
            if full_text:
                text_placeholder.markdown(full_text)
                display_subject_images(full_text)

            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": chunk_buffer})

        except Exception as e:
            error_response = "Sorry, I encountered an error. Please try again."
            message_placeholder.markdown(error_response)
            st.session_state.messages.append({"role": "assistant", "content": error_response})
            print("Error during agent streaming")
            traceback.print_exc()
        finally:
            st.session_state.agent_running = False
            st.rerun()
