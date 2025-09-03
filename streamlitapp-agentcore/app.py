import streamlit as st
import random
import time
import boto3
import uuid
import math
from botocore.exceptions import EventStreamError
import json
import os
import tempfile
import sys
import argparse
import requests
import urllib.parse
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
temp_dir = tempfile.mkdtemp()

def get_environment():
    try:
        # Get arguments after the '--' separator in the streamlit command
        env_index = sys.argv.index('--env') + 1
        if env_index < len(sys.argv):
            return sys.argv[env_index]
        raise ValueError("No value found after --env parameter")
    except (ValueError, IndexError):
        raise ValueError("Environment parameter not found. Please provide --env parameter.")



environmentName = get_environment()

ssm_client = boto3.client('ssm')

agent_arn = (ssm_client.get_parameter(Name=f"/streamlitapp/{environmentName}/AGENT_ARN", WithDecryption=True)["Parameter"]["Value"])
           
s3_bucket_name = (ssm_client.get_parameter(Name=f"/streamlitapp/{environmentName}/S3_BUCKET_NAME",WithDecryption=True,)["Parameter"]["Value"])

def list_png_files():
        try:
            s3_client = boto3.client('s3')
            prefix = 'nsclc_radiogenomics/PNG/'
            response = s3_client.list_objects_v2(Bucket=s3_bucket_name, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].lower().endswith('.png')]
        except Exception as e:
            st.error(f"Error listing image: {str(e)}")
            return None
def list_graph_files():
    try:
        s3_client = boto3.client('s3')
        prefix = 'graphs/'
        response = s3_client.list_objects_v2(Bucket=s3_bucket_name, Prefix=prefix)
        
        # Get all PNG files with their LastModified timestamps
        # Exclude files that contain 'invocationID' in their path
        files = [(obj['Key'], obj['LastModified']) 
                for obj in response.get('Contents', []) 
                if obj['Key'].lower().endswith('.png') and 'invocationid' not in obj['Key'].lower()]
        
        # Sort by LastModified timestamp, most recent first
        sorted_files = sorted(files, key=lambda x: x[1], reverse=True)
        
        # Return just the keys in sorted order
        return [file[0] for file in sorted_files]
    except Exception as e:
        st.error(f"Error listing image: {str(e)}")
        return None

def get_image_from_s3(file_key):
    from io import BytesIO
    from PIL import Image
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=s3_bucket_name, Key=file_key)
        image_content = response['Body'].read()
        image = Image.open(BytesIO(image_content))
        return image
    except Exception as e:
        st.error(f"Error fetching image from S3: {str(e)}")
        return None
def get_s3_image(isKMplot: bool = False, invocation_id: str = None):
    
    if isKMplot and invocation_id:
        try:
            s3_client = boto3.client('s3')
            s3_key = f'graphs/invocationID/{invocation_id}/KMplot.png'

            response = s3_client.get_object(Bucket=s3_bucket_name, Key=s3_key)
            image_content = response['Body'].read()

            temp_image_path = os.path.join(temp_dir, 'KMplot.png')
            with open(temp_image_path, 'wb') as f:
                f.write(image_content)

            return {
                'name': 'KMplot.png',
                'type': 'image/png',
                'path': temp_image_path
            }
        except s3_client.exceptions.NoSuchKey:
            return {"error": "No KM plot graphs found for this invocation ID."}
        except Exception as e:
            return {"error": f"Error fetching KM plot from S3: {str(e)}"}
    else:
        try:
            graph = list_graph_files()
            
            if not graph:  # If list_graph_files returns None or empty list
                return {"error": "No graph files found in the graphs directory."}
                
            if len(graph) == 0:
                return {"error": "No graph files available."}
                
            first_file = graph[0]
            s3_client = boto3.client('s3')
            
            response = s3_client.get_object(Bucket=s3_bucket_name, Key=first_file)
            image_content = response['Body'].read()

            filename = os.path.basename(first_file)
            temp_image_path = os.path.join(temp_dir, filename)
            
            with open(temp_image_path, 'wb') as f:
                f.write(image_content)

            return {
                'name': filename,
                'type': 'image/png',
                'path': temp_image_path
            }
        except Exception as e:
            return {"error": f"Error fetching graph from S3: {str(e)}"}


def process_files(files_event):
    files_list = files_event['files']
    processed_files = []
    for file in files_list:
        file_name = file['name']
        file_type = file['type']
        file_bytes = file['bytes']

        # Save the file
        file_path = os.path.join(temp_dir, file_name)
        with open(file_path, 'wb') as f:
            f.write(file_bytes)

        processed_files.append({
            'name': file_name,
            'type': file_type,
            'path': file_path
        })

    return processed_files


def new_session():
    st.session_state["SESSION_ID"] = str(uuid.uuid1())

# Streamed response emulator
def response_generator():
    
    session_id = st.session_state["SESSION_ID"]
    
    # Build message string (keep your existing logic)
    messagesStr = ""
    for m in st.session_state.messages:
        messagesStr = messagesStr + "role:" + m["role"] + " " + "content:" + m["content"] + "\n\n"
    
    # AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    region = session.region_name
    
    # AgentCore Runtime URL
    escaped_arn = urllib.parse.quote(agent_arn, safe="")
    url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_arn}/invocations"
    
    # Request payload
    payload = {"prompt": messagesStr}
    headers = {
        "Content-Type": "application/json",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
    }
    
    # Sign with AWS SDK
    request = AWSRequest(method='POST', url=url, data=json.dumps(payload), headers=headers)
    SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)
    
    try:
        response = requests.post(url, headers=dict(request.headers), data=request.body, timeout=100, stream=True)
        
        for line in response.iter_lines(chunk_size=1):
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    yield line[6:].replace('"', "")
                    
    except Exception as e:
        print(f"AgentCore error: {e}")
        raise e
    
st.set_page_config(layout="wide", page_title="Biomarker Agent")

# Custom CSS
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 4px;
    }
    .stTextInput > div > div > input {
        background-color: #f0f2f6;
    }
    
    /* Trace styling */
    .trace-header {
        background-color: rgb(248, 249, 250);
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 10px;
    }
    .trace-title {
        color: rgb(49, 51, 63);
        font-size: 1.2em;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .stExpander {
        background-color: white !important;
        border: 1px solid #e6e6e6 !important;
        border-radius: 8px !important;
        margin-bottom: 8px !important;
    }
    .step-header {
        display: flex;
        align-items: center;
        gap: 8px;
        color: rgb(49, 51, 63);
    }
    .trace-content {
        padding: 10px;
        background-color: #f8f9fa;
        border-radius: 4px;
        margin-top: 8px;
        white-space: pre-wrap;
        font-family: monospace;
    }
    
    /* Sample questions styling */
    details {
        border: 1px solid #aaa;
        border-radius: 4px;
        padding: .5em .5em 0;
        margin-bottom: 1em;
    }
    summary {
        font-weight: bold;
        margin: -.5em -.5em 0;
        padding: .5em;
        cursor: pointer;
    }
    details[open] {
        padding: .5em;
    }
    details[open] summary {
        border-bottom: 1px solid #aaa;
        margin-bottom: .5em;
    }
    .scrollable-content {
        max-height: 200px;
        overflow-y: auto;
        padding-right: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header('Image Controls')
    
    st.subheader("Biomarker Imaging Results")
    png_files = list_png_files()
    selected_file = st.selectbox('Select a file to view the imaging results:', png_files)
    load_image = st.checkbox('Load and display selected image')

    invocation_id = 1
    fetch_image = st.button("Fetch Chart")
    fetch_graph = st.button("Fetch Graphs")
    

# Main content
st.title("Biomarker Research Agent with Amazon Bedrock AgentCore")

col1, col2 = st.columns([6, 1])
with col2:
    st.link_button("Github 😎", "https://github.com/aws-samples/amazon-bedrock-agents-cancer-biomarker-discovery")

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

st.markdown(f"""
    <details>
        <summary>Click to sample expand questions</summary>
        <div class="scrollable-content">
            <ol>
                {"".join(f"<li>{q}</li>" for q in questions)}
            </ol>
        </div>
    </details>
""", unsafe_allow_html=True)
                    

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "SESSION_ID" not in st.session_state:
    new_session()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("How can I help ?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    
    response = ""
    with st.chat_message("assistant"):
        #print(st.session_state.messages)
        try:
            response = st.write_stream(response_generator())
        except Exception as e:
            print("Exception")
            print(e)
            pass
if 'selected_actions' in st.session_state:
    st.write("Currently selected actions:", ', '.join(st.session_state.selected_actions))

image_placeholder = st.empty()

# Handle image display
if selected_file and load_image:
    try:
        image = get_image_from_s3(selected_file)
        image_placeholder.image(image, caption=selected_file, use_column_width=True)
    except Exception as e:
        st.error(f"Unable loading image: {str(e)}")

elif fetch_image:
    s3_image = get_s3_image(isKMplot=True, invocation_id=invocation_id) 
    if s3_image and 'error' not in s3_image:  
        try:
            image_placeholder.image(s3_image['path'], caption=s3_image['name'], use_column_width=True)
        except Exception as e:
            st.error(f"Unable loading image: {str(e)}")
    else:
        error_msg = s3_image.get('error', "Failed to fetch image from S3.") if s3_image else "Failed to fetch image from S3."
        image_placeholder.error(error_msg)

elif fetch_graph:
    s3_image = get_s3_image(isKMplot=False)  
    if s3_image and 'error' not in s3_image: 
        try:
            image_placeholder.image(s3_image['path'], caption=s3_image['name'], use_column_width=True)
        except Exception as e:
            st.error(f"Unable loading image: {str(e)}")
    else:
        error_msg = s3_image.get('error', "Failed to fetch image from S3.") if s3_image else "Failed to fetch image from S3."
        image_placeholder.error(error_msg)
        
    # Add assistant response to chat history
    #st.session_state.messages.append({"role": "assistant", "content": response})
