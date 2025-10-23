# Basic strands agent streaming example.
# To test locally, run `uv run agent.py` and then
# curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d '{"prompt": "Hello!"}'

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp import MCPClient
import os
import boto3
import threading

os.environ["BYPASS_TOOL_CONSENT"] = "true"

app = BedrockAgentCoreApp()

SOURCE_FILE = os.environ.get("SOURCE_FILE", "s3://<YOUR S3 BUCKET>/Sample_Filled_MedicalIntakeForm.pdf")

# AgentCore entry point
# Store conversation state per session - use thread-safe storage
conversation_cache = {}
cache_lock = threading.Lock()

@app.entrypoint
async def strands_agent_bedrock(payload):
    user_prompt = payload.get("prompt", "")
    session_id = payload.get("sessionId", "default")
    
    try:
        yield "🔍 Starting Intelligent Document Processing Agent...\n\n"
        
        # Check if this is a follow-up question
        is_followup = session_id in conversation_cache and "extracted_data" in conversation_cache[session_id]
        
        # Define local_file path (used for initial extraction)
        # Must be in /tmp since BDA MCP BASE_DIR is /tmp
        cached_file = "/tmp/Sample_Filled_MedicalIntakeForm.pdf"
        local_file = cached_file
        
        # Only process file if not a follow-up question
        if not is_followup:
            yield f"📁 Input file: {SOURCE_FILE}\n\n"
            
            # Check if file is already cached
            if os.path.exists(cached_file):
                yield f"✅ Using cached file: {local_file}\n\n"
            else:
                # Download file from S3 and cache it
                # Download file from S3 and cache it
                s3 = boto3.client('s3')
                
                try:
                    yield "⬇️ Downloading file from S3 (first time only)...\n\n"
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(cached_file), exist_ok=True)
                    
                    # Parse S3 URI to get bucket and key
                    s3_uri = SOURCE_FILE.replace("s3://", "")
                    bucket_name = s3_uri.split("/")[0]
                    object_key = "/".join(s3_uri.split("/")[1:])
                    
                    # Download to cache location so it persists across invocations
                    s3.download_file(bucket_name, object_key, cached_file)
                    yield f"✅ Downloaded and cached file to {local_file}\n\n"
                except Exception as s3_error:
                    yield f"❌ S3 download error: {str(s3_error)}\n\n"
                    return
            
            # Verify file exists before proceeding
            if not os.path.exists(local_file):
                yield f"❌ Error: File not found at {local_file}\n\n"
                return
        
        # Initialize Bedrock model
        bedrock_model = BedrockModel(
            #model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            temperature=0.2,
        )
        
        # Check if this is a follow-up question
        if is_followup:
            # Use cached data for follow-up questions
            yield "💬 Answering follow-up question...\n\n"
            extracted_data = conversation_cache[session_id]["extracted_data"]
            
            # Create agent without tools for follow-up questions
            chat_agent = Agent(
                system_prompt=(
                    f"""You are an AI assistant helping answer questions about a medical intake form.
                    
                    Here is the extracted data from the form:
                    {extracted_data}
                    
                    Answer the user's question based on this data. Be concise and direct."""
                ),
                model=bedrock_model,
            )
            
            response = chat_agent(user_prompt)
            yield "\n💬 Answer:\n\n"
            yield str(response)
        else:
            # Initial extraction - process the document
            # Initialize MCP client
            aws_bda_client = MCPClient(
                lambda: stdio_client(
                    StdioServerParameters(
                        command="uvx",
                        args=["awslabs.aws-bedrock-data-automation-mcp-server@latest"],
                        env={
                            "AWS_REGION": os.environ.get("AWS_REGION", "us-east-1"),
                            "AWS_BUCKET_NAME": SOURCE_FILE.replace("s3://", "").split("/")[0] if SOURCE_FILE.startswith("s3://") else "<YOUR S3 BUCKET NAME>",
                            "BASE_DIR": "/tmp",  # BDA MCP server base directory
                            "FASTMCP_LOG_LEVEL": "ERROR"
                        }
                    )
                )
            )
            
            yield "🔧 Connecting to BDA MCP server...\n\n"
            
            with aws_bda_client:
                tools = aws_bda_client.list_tools_sync()
                
                yield f"✅ Connected! Found {len(tools)} tools\n\n"
                yield "🤖 Extracting data from document...\n\n"
                
                idp_agent = Agent(
                    system_prompt=(
                        """You are an AI assistant with expertise in parsing handwritten notes and complex medical documents. 
                        Extract questions and answers provided by the user. 
                        For checkboxes, mark 'true' if the option is selected, 'false' otherwise.
                        Include confidence scores for each extracted data field.
                        Return results as JSON with confidence scores for each field."""
                    ),
                    model=bedrock_model,
                    tools=tools
                )
                
                response = idp_agent(f"Use {local_file} as input data and extract all information.")
                
                # Get the response text
                response_text = str(response)
                
                # Cache the extracted data for this session
                if session_id not in conversation_cache:
                    conversation_cache[session_id] = {}
                conversation_cache[session_id]["extracted_data"] = response_text
                
                yield "\n📊 Extraction Results:\n\n"
                
                # Try to clean up escaped JSON if present
                import re
                # Remove escaped quotes and newlines for cleaner display
                cleaned_response = response_text.replace('\\"', '"').replace('\\n', '\n')
                yield cleaned_response
        
    except Exception as e:
        import traceback
        yield f"❌ Error: {str(e)}\n"
        yield f"Traceback: {traceback.format_exc()}\n"


if __name__ == "__main__":
    app.run()
