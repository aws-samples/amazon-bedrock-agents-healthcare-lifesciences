import streamlit as st
from botocore.config import Config
from boto3.session import Session
import uuid
import json
import os
import tempfile
import shutil
from io import BytesIO
from PIL import Image

class BedrockAgent:
    """BedrockAgent class for invoking an Anthropic AI agent.

    This class provides a wrapper for invoking an AI agent hosted on Anthropic's
    Bedrock platform. It handles authentication, session management, and tracing
    to simplify interacting with a Bedrock agent.

    Usage:

    agent = BedrockAgent()
    response, trace = agent.invoke_agent(input_text)

    The invoke_agent() method sends the input text to the agent and returns
    the agent's response text and trace information.

    Trace information includes the agent's step-by-step reasoning and any errors.
    This allows visibility into how the agent came up with the response.

    The class initializes session state and authentication on first run. It
    reuses the session for subsequent calls for continuity.

    Requires streamlit and boto3. Authentication requires credentials configured
    in secrets management.
    """
    def __init__(self, environmentName) -> None:
        if "BEDROCK_RUNTIME_CLIENT" not in st.session_state:
            st.session_state["BEDROCK_RUNTIME_CLIENT"] = Session().client(
                "bedrock-agent-runtime", config=Config(read_timeout=600)
            )

        if "SESSION_ID" not in st.session_state:
            st.session_state["SESSION_ID"] = str(uuid.uuid1())
        
        self.agent_id = (
            Session()
            .client("ssm")
            .get_parameter(
                Name=f"/streamlitapp/{environmentName}/AGENT_ID", WithDecryption=True
            )["Parameter"]["Value"]
        )
        self.agent_alias_id = (
            Session()
            .client("ssm")
            .get_parameter(
                Name=f"/streamlitapp/{environmentName}/AGENT_ALIAS_ID",
                WithDecryption=True,
            )["Parameter"]["Value"]
        )
       

        self.s3_bucket_name = (
            Session()
            .client("ssm")
            .get_parameter(
                Name=f"/streamlitapp/{environmentName}/S3_BUCKET_NAME",
                WithDecryption=True,
            )["Parameter"]["Value"]
        )

        
        self.temp_dir = tempfile.mkdtemp()


    def new_session(self):
        st.session_state["SESSION_ID"] = str(uuid.uuid1())

    def invoke_agent(self, input_text, trace):
        response_text = ""
        trace_text = ""
        step = 0
        files_generated = []

        try:
            response = st.session_state["BEDROCK_RUNTIME_CLIENT"].invoke_agent(
                inputText=input_text,
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=st.session_state["SESSION_ID"],
                enableTrace=True
            )

            for event in response["completion"]:
                if 'files' in event.keys():
                    files_generated.extend(self.process_files(event['files']))

                if "chunk" in event:
                    data = event["chunk"]["bytes"]
                    response_text = data.decode("utf8")

                elif "trace" in event:
                    trace_obj = event["trace"]["trace"]
                    
                    if "orchestrationTrace" in trace_obj:
                        trace_dump = json.dumps(trace_obj["orchestrationTrace"], indent=2)

                        if "rationale" in trace_obj["orchestrationTrace"]:
                            step += 1
                            trace_text += f'\n\n\n---------- Step {step} ----------\n\n\n{trace_obj["orchestrationTrace"]["rationale"]["text"]}\n\n\n'
                            trace.markdown(f'\n\n\n---------- Step {step} ----------\n\n\n{trace_obj["orchestrationTrace"]["rationale"]["text"]}\n\n\n')

                        # elif "modelInvocationInput" not in trace_obj["orchestrationTrace"]:
                        #     trace_text += "\n\n\n" + trace_dump + "\n\n\n"
                        #     trace.markdown("\n\n\n" + trace_dump + "\n\n\n")

                    elif "failureTrace" in trace_obj:
                        trace_text += "\n\n\n" + json.dumps(trace_obj["failureTrace"], indent=2) + "\n\n\n"
                        trace.markdown("\n\n\n" + json.dumps(trace_obj["failureTrace"], indent=2) + "\n\n\n")

                    elif "postProcessingTrace" in trace_obj:
                        step += 1
                        trace_text += f"\n\n\n---------- Step {step} ----------\n\n\n{json.dumps(trace_obj['postProcessingTrace']['modelInvocationOutput']['parsedResponse']['text'], indent=2)}\n\n\n"
                        trace.markdown(f"\n\n\n---------- Step {step} ----------\n\n\n{json.dumps(trace_obj['postProcessingTrace']['modelInvocationOutput']['parsedResponse']['text'], indent=2)}\n\n\n")

        except Exception as e:
            trace_text += f"Error during agent invocation: {str(e)}\n"
            trace.markdown(f"Error during agent invocation: {str(e)}")

        return response_text, trace_text, files_generated
        
    def list_png_files(self):
        try:
            self.s3_client = (
                Session()
                .client("s3"))
            prefix = 'nsclc_radiogenomics/PNG/'
            response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket_name, Prefix=prefix)
            return [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].lower().endswith('.png')]
        except Exception as e:
            st.error(f"Error listing image: {str(e)}")
            return None
    def list_graph_files(self):
        try:
            self.s3_client = Session().client("s3")
            prefix = 'graphs/'
            response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket_name, Prefix=prefix)
            
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

    def get_image_from_s3(self, file_key):
        try:
            self.s3_client = (
                Session()
                .client("s3"))
            response = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=file_key)
            image_content = response['Body'].read()
            image = Image.open(BytesIO(image_content))
            return image
        except Exception as e:
            st.error(f"Error fetching image from S3: {str(e)}")
            return None
    

    def process_files(self, files_event):
        files_list = files_event['files']
        processed_files = []
        for file in files_list:
            file_name = file['name']
            file_type = file['type']
            file_bytes = file['bytes']

            # Save the file
            file_path = os.path.join(self.temp_dir, file_name)
            with open(file_path, 'wb') as f:
                f.write(file_bytes)

            processed_files.append({
                'name': file_name,
                'type': file_type,
                'path': file_path
            })

        return processed_files
    def listActions(self):
    
        client = Session().client('bedrock-agent')

        response = client.list_agent_versions(
            agentId=self.agent_id
        )
        agentversions = []
        agentactiongroups = []

        for version in response['agentVersionSummaries']:
            if version['agentVersion'].isnumeric():
                agentversions.append([version['agentVersion']])

        latestversion = str(agentversions[-1][0])
            
        actionlist = client.list_agent_action_groups(
            agentId=self.agent_id,
            agentVersion=latestversion,
            maxResults=123

        )
        actiongroupsummary=actionlist['actionGroupSummaries']

        for actiongroup in actiongroupsummary:
            agentactiongroups.append(actiongroup['actionGroupName'])

        return agentactiongroups


    def cleanup_temp_files(self):
        shutil.rmtree(self.temp_dir)
        self.temp_dir = tempfile.mkdtemp()
     
    def get_s3_image(self, isKMplot: bool = False, invocation_id: str = None):
        if isKMplot and invocation_id:
            try:
                self.s3_client = Session().client("s3")
                s3_key = f'graphs/invocationID/{invocation_id}/KMplot.png'

                response = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=s3_key)
                image_content = response['Body'].read()

                temp_image_path = os.path.join(self.temp_dir, 'KMplot.png')
                with open(temp_image_path, 'wb') as f:
                    f.write(image_content)

                return {
                    'name': 'KMplot.png',
                    'type': 'image/png',
                    'path': temp_image_path
                }
            except self.s3_client.exceptions.NoSuchKey:
                return {"error": "No KM plot graphs found for this invocation ID."}
            except Exception as e:
                return {"error": f"Error fetching KM plot from S3: {str(e)}"}
        else:
            try:
                graph = self.list_graph_files()
                
                if not graph:  # If list_graph_files returns None or empty list
                    return {"error": "No graph files found in the graphs directory."}
                    
                if len(graph) == 0:
                    return {"error": "No graph files available."}
                    
                first_file = graph[0]
                self.s3_client = Session().client("s3")
                
                response = self.s3_client.get_object(Bucket=self.s3_bucket_name, Key=first_file)
                image_content = response['Body'].read()

                filename = os.path.basename(first_file)
                temp_image_path = os.path.join(self.temp_dir, filename)
                
                with open(temp_image_path, 'wb') as f:
                    f.write(image_content)

                return {
                    'name': filename,
                    'type': 'image/png',
                    'path': temp_image_path
                }
            except Exception as e:
                return {"error": f"Error fetching graph from S3: {str(e)}"}
