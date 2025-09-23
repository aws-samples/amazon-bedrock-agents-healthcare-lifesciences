import json
import re
import time
import uuid
from typing import Dict, Iterator, List

import boto3
import streamlit as st
from streamlit.logger import get_logger

logger = get_logger(__name__)
logger.setLevel("INFO")

# Page config
st.set_page_config(
    page_title="Genomics Variant Analysis Agent",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Remove Streamlit deployment components
st.markdown(
    """
      <style>
        .stAppDeployButton {display:none;}
        #MainMenu {visibility: hidden;}
      </style>
    """,
    unsafe_allow_html=True,
)

HUMAN_AVATAR = "static/user-profile.svg"
AI_AVATAR = "static/gen-ai-dark.svg"


def fetch_agent_runtimes(region: str = "us-east-1") -> List[Dict]:
    """Fetch available agent runtimes from bedrock-agentcore-control"""
    try:
        client = boto3.client("bedrock-agentcore-control", region_name=region)
        response = client.list_agent_runtimes(maxResults=100)

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
        st.error(f"Error fetching agent runtimes: {e}")
        return []


def fetch_agent_runtime_versions(
    agent_runtime_id: str, region: str = "us-east-1"
) -> List[Dict]:
    """Fetch versions for a specific agent runtime"""
    try:
        client = boto3.client("bedrock-agentcore-control", region_name=region)
        response = client.list_agent_runtime_versions(agentRuntimeId=agent_runtime_id)

        # Filter only READY versions
        ready_versions = [
            version
            for version in response.get("agentRuntimes", [])
            if version.get("status") == "READY"
        ]

        # Sort by most recent update time (newest first)
        ready_versions.sort(key=lambda x: x.get("lastUpdatedAt", ""), reverse=True)

        return ready_versions
    except Exception as e:
        st.error(f"Error fetching agent runtime versions: {e}")
        return []


def extract_tool_responses_from_content(content: str) -> List[str]:
    """Extract tool responses from the content"""
    tool_responses = []
    
    # Split content by tool usage markers
    if "🔧 Using tool:" in content:
        sections = content.split("🔧 Using tool:")
        
        for i, section in enumerate(sections[1:], 1):  # Skip first section (before any tool)
            # Extract tool name
            lines = section.split('\n')
            tool_name = lines[0].strip() if lines else f"Tool {i}"
            
            # Look for structured data patterns after tool usage
            # This could be JSON, formatted text, or other structured output
            tool_output = ""
            capturing = False
            
            for line in lines[1:]:
                # Stop capturing when we hit the next response text
                if any(phrase in line.lower() for phrase in ['based on', 'the results show', 'analysis reveals']):
                    break
                    
                # Look for structured data indicators
                if any(indicator in line for indicator in ['{', 'Total', 'Count:', 'Results:', '|', 'Error:']):
                    capturing = True
                
                if capturing:
                    tool_output += line + '\n'
                    
                # Stop if we hit empty lines after capturing started
                if capturing and line.strip() == "":
                    break
            
            if tool_output.strip():
                tool_responses.append(f"Tool: {tool_name}\n{tool_output.strip()}")
    
    return tool_responses


def clean_response_text(text: str, show_thinking: bool = True) -> str:
    """Clean and format response text for better presentation"""
    if not text:
        return text

    # Handle the consecutive quoted chunks pattern
    # Pattern: "word1" "word2" "word3" -> word1 word2 word3
    text = re.sub(r'"\s*"', "", text)
    text = re.sub(r'^"', "", text)
    text = re.sub(r'"$', "", text)

    # Replace literal \n with actual newlines
    text = text.replace("\\n", "\n")

    # Replace literal \t with actual tabs
    text = text.replace("\\t", "\t")

    # Clean up multiple spaces
    text = re.sub(r" {3,}", " ", text)

    # Fix newlines that got converted to spaces
    text = text.replace(" \n ", "\n")
    text = text.replace("\n ", "\n")
    text = text.replace(" \n", "\n")

    # Handle numbered lists
    text = re.sub(r"\n(\d+)\.\s+", r"\n\1. ", text)
    text = re.sub(r"^(\d+)\.\s+", r"\1. ", text)

    # Handle bullet points
    text = re.sub(r"\n-\s+", r"\n- ", text)
    text = re.sub(r"^-\s+", r"- ", text)

    # Handle section headers
    text = re.sub(r"\n([A-Za-z][A-Za-z\s]{2,30}):\s*\n", r"\n**\1:**\n\n", text)

    # Clean up multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Clean up thinking
    if not show_thinking:
        text = re.sub(r"<thinking>.*?</thinking>", "", text)

    return text.strip()


def extract_text_from_response(data) -> str:
    """Extract text content from response data in various formats"""
    if isinstance(data, dict):
        # Handle format: {'role': 'assistant', 'content': [{'text': 'Hello!'}]}
        if "role" in data and "content" in data:
            content = data["content"]
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and "text" in content[0]:
                    return str(content[0]["text"])
                else:
                    return str(content[0])
            elif isinstance(content, str):
                return content
            else:
                return str(content)

        # Handle other common formats
        if "text" in data:
            return str(data["text"])
        elif "content" in data:
            content = data["content"]
            if isinstance(content, str):
                return content
            else:
                return str(content)
        elif "message" in data:
            return str(data["message"])
        elif "response" in data:
            return str(data["response"])
        elif "result" in data:
            return str(data["result"])

    return str(data)
def parse_streaming_chunk(chunk: str) -> str:
    """Parse individual streaming chunk and extract meaningful content"""
    logger.debug(f"parse_streaming_chunk: received chunk: {chunk}")
    logger.debug(f"parse_streaming_chunk: chunk type: {type(chunk)}")

    try:
        # Try to parse as JSON first
        if chunk.strip().startswith("{"):
            logger.debug("parse_streaming_chunk: Attempting JSON parse")
            data = json.loads(chunk)
            logger.debug(f"parse_streaming_chunk: Successfully parsed JSON: {data}")

            # Handle the specific format: {'role': 'assistant', 'content': [{'text': '...'}]}
            if isinstance(data, dict) and "role" in data and "content" in data:
                content = data["content"]
                if isinstance(content, list) and len(content) > 0:
                    first_item = content[0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        extracted_text = first_item["text"]
                        logger.debug(
                            f"parse_streaming_chunk: Extracted text: {extracted_text}"
                        )
                        return extracted_text
                    else:
                        return str(first_item)
                else:
                    return str(content)
            else:
                # Use the general extraction function for other formats
                return extract_text_from_response(data)

        # If not JSON, return the chunk as-is
        logger.debug("parse_streaming_chunk: Not JSON, returning as-is")
        return chunk
    except json.JSONDecodeError as e:
        logger.error(f"parse_streaming_chunk: JSON decode error: {e}")

        # Try to handle Python dict string representation (with single quotes)
        if chunk.strip().startswith("{") and "'" in chunk:
            logger.debug(
                "parse_streaming_chunk: Attempting to handle Python dict string"
            )
            try:
                # Try to convert single quotes to double quotes for JSON parsing
                # This is a simple approach - might need refinement for complex cases
                json_chunk = chunk.replace("'", '"')
                data = json.loads(json_chunk)
                logger.debug(
                    f"parse_streaming_chunk: Successfully converted and parsed: {data}"
                )

                # Handle the specific format
                if isinstance(data, dict) and "role" in data and "content" in data:
                    content = data["content"]
                    if isinstance(content, list) and len(content) > 0:
                        first_item = content[0]
                        if isinstance(first_item, dict) and "text" in first_item:
                            extracted_text = first_item["text"]
                            logger.debug(
                                f"parse_streaming_chunk: Extracted text from converted dict: {extracted_text}"
                            )
                            return extracted_text
                        else:
                            return str(first_item)
                    else:
                        return str(content)
                else:
                    return extract_text_from_response(data)
            except json.JSONDecodeError:
                logger.debug(
                    "parse_streaming_chunk: Failed to convert Python dict string"
                )
                pass

        # If all parsing fails, return the chunk as-is
        logger.debug("parse_streaming_chunk: All parsing failed, returning chunk as-is")
        return chunk


def invoke_agent_streaming(
    prompt: str,
    agent_arn: str,
    runtime_session_id: str,
    region: str = "us-east-1",
    show_tool: bool = True,
) -> Iterator[Dict]:
    """Invoke agent and yield streaming response chunks with tool tracking"""
    try:
        from botocore.config import Config
        config = Config(
            region_name=region,
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            read_timeout=900,
            connect_timeout=180
        )
        agentcore_client = boto3.client("bedrock-agentcore", config=config)

        boto3_response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            qualifier="DEFAULT",
            runtimeSessionId=runtime_session_id,
            payload=json.dumps({"prompt": prompt}),
        )

        logger.debug(f"contentType: {boto3_response.get('contentType', 'NOT_FOUND')}")

        if "text/event-stream" in boto3_response.get("contentType", ""):
            logger.debug("Using streaming response path")
            for line in boto3_response["response"].iter_lines(chunk_size=1):
                if line:
                    line = line.decode("utf-8")
                    logger.debug(f"Raw line: {line}")

                    if line.startswith("data: "):
                        line = line[6:]
                        try:
                            data = json.loads(line)
                            data = json.loads(data)

                            # Parse each chunk and display only what is relevant
                            if "data" in data:
                                content = data.get("data")
                                yield {"type": "text", "content": content}
                            elif "current_tool_use" in data:
                                tool_name = data["current_tool_use"]["name"]
                                tool_input = data["current_tool_use"]["input"]
                                logger.debug(f"TOOL NAME: {tool_name}")
                                logger.debug(f"TOOL INPUT: {tool_input}")
                                if show_tool:
                                    yield {"type": "tool_use", "name": tool_name, "input": tool_input}
                            elif "message" in data:
                                if "content" in data["message"]:
                                    for obj in data["message"]["content"]:
                                        if "toolResult" in obj:
                                            tool_result = obj["toolResult"]["content"][0]["text"]
                                            logger.debug(f"TOOL RESULT: {tool_result}")
                                            yield {"type": "tool_result", "content": tool_result}
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error: {e}")
                            # Fallback to old parsing method
                            parsed_chunk = parse_streaming_chunk(line)
                            if parsed_chunk.strip():
                                # Check if this chunk contains tool usage info
                                if "🔧 Using tool:" in parsed_chunk:
                                    # Extract tool name
                                    import re
                                    tool_match = re.search(r'🔧 Using tool: (\w+)', parsed_chunk)
                                    if tool_match and show_tool:
                                        yield {"type": "tool_use", "name": tool_match.group(1), "input": "See agent response"}
                                yield {"type": "text", "content": parsed_chunk}
                    else:
                        logger.debug(f"Line doesn't start with 'data: ', skipping: {line}")
        else:
            # Handle non-streaming response (existing logic)
            response_obj = boto3_response.get("response")
            if hasattr(response_obj, "read"):
                content = response_obj.read()
                if isinstance(content, bytes):
                    content = content.decode("utf-8")
                try:
                    response_data = json.loads(content)
                    if isinstance(response_data, dict):
                        if "result" in response_data:
                            actual_data = response_data["result"]
                        else:
                            actual_data = response_data
                        
                        if "role" in actual_data and "content" in actual_data:
                            content_list = actual_data["content"]
                            if isinstance(content_list, list) and len(content_list) > 0:
                                first_item = content_list[0]
                                if isinstance(first_item, dict) and "text" in first_item:
                                    yield {"type": "text", "content": first_item["text"]}
                                else:
                                    yield {"type": "text", "content": str(first_item)}
                            else:
                                yield {"type": "text", "content": str(content_list)}
                        else:
                            text = extract_text_from_response(actual_data)
                            yield {"type": "text", "content": text}
                    else:
                        yield {"type": "text", "content": str(response_data)}
                except json.JSONDecodeError:
                    yield {"type": "text", "content": content}

    except Exception as e:
        yield {"type": "text", "content": f"Error invoking agent: {e}"}


def main():
    st.logo("static/agentcore-service-icon.png", size="large")
    st.title("🧬 Genomics Variant Analysis Agent")

    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")

        # Region selection (moved up since it affects agent fetching)
        region = st.selectbox(
            "AWS Region",
            ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
            index=0,
        )

        # Agent selection - hardcoded for genomics agent
        st.subheader("Agent Selection")
        
        # Use the specific genomics agent - REPLACE WITH YOUR AGENT ARN
        agent_arn = "arn:aws:bedrock-agentcore:<YOUR_REGION>:<YOUR_ACCOUNT_ID>:runtime/<YOUR_AGENT_NAME>"
        
        st.info("🧬 **Genomics Variant Analysis Agent**")
        st.write("**Agent:** <YOUR_AGENT_NAME>")
        st.write(f"**Region:** {region}")
        
        with st.expander("View ARN"):
            st.code(agent_arn)
        if st.button("Refresh", key="refresh_agents", help="Refresh agent list"):
            st.rerun()

        # Runtime Session ID
        st.subheader("Session Configuration")

        # Initialize session ID in session state if not exists
        if "runtime_session_id" not in st.session_state:
            st.session_state.runtime_session_id = str(uuid.uuid4())

        # Session ID input with generate button
        runtime_session_id = st.text_input(
            "Runtime Session ID",
            value=st.session_state.runtime_session_id,
            help="Unique identifier for this runtime session",
        )

        if st.button("Refresh", help="Generate new session ID and clear chat"):
            st.session_state.runtime_session_id = str(uuid.uuid4())
            st.session_state.messages = []  # Clear chat messages when resetting session
            st.rerun()

        # Update session state if user manually changed the ID
        if runtime_session_id != st.session_state.runtime_session_id:
            st.session_state.runtime_session_id = runtime_session_id

        # Response formatting options
        st.subheader("Display Options")
        auto_format = st.checkbox(
            "Auto-format responses",
            value=True,
            help="Automatically clean and format responses",
        )
        show_raw = st.checkbox(
            "Show raw response",
            value=False,
            help="Display the raw unprocessed response",
        )
        show_tools = st.checkbox(
            "Show tools",
            value=True,
            help="Display tools used",
        )
        show_thinking = st.checkbox(
            "Show thinking",
            value=False,
            help="Display the AI thinking text",
        )

        # Clear chat button
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()

        # Sample questions
        st.divider()
        st.subheader("💡 Sample Questions")
        
        sample_questions = [
            "How many patients are in the present cohort?",
            "Analyze chromosome 17 variants in patient <SAMPLE_ID>?",
            "What's the frequency of chr13:32332591 in BRCA2 variant in this cohort and 1000 genome cohort(1000g)?",
            "Can you check how many variants are present for BRCA family of genes in patient '<SAMPLE_ID>'?",
            "Analyze patient <SAMPLE_ID> for risk stratification",
            "Which are the major drug related impactful variant pathway enriched in the patients?",
            "What are the key genomics aberrations linked with heart disease conditions in patient <SAMPLE_ID>?",
            "Analyze the patients cohort and provide a comprehensive clinical summary"
        ]
        
        for i, question in enumerate(sample_questions):
            if st.button(f"📝 {question}", key=f"sample_{i}", use_container_width=True):
                st.session_state["selected_question"] = question

        # Connection status
        st.divider()
        if agent_arn:
            st.success("✅ Agent selected and ready")
        else:
            st.error("❌ Please select an agent")
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"], avatar=message["avatar"]):
            st.markdown(message["content"])
            # Show elapsed time for assistant messages
            if message["role"] == "assistant" and "elapsed" in message:
                st.caption(f"⏱️ Response time: {message['elapsed']:.2f} seconds")
                
                # Show model execution logs for all assistant messages
                with st.expander("🔍 View Model Execution Logs"):
                    formatted_content = message["content"]
                    
                    # Extract explicit tool usage first
                    explicit_tools = []
                    if "🔧 Using tool:" in formatted_content:
                        tool_sections = formatted_content.split("🔧 Using tool:")
                        for j, section in enumerate(tool_sections[1:], 1):
                            tool_name = section.split('\n')[0].strip()
                            explicit_tools.append(f"**Tool {j}:** {tool_name}")
                    
                    if "📝 Tool input:" in formatted_content:
                        input_sections = formatted_content.split("📝 Tool input:")
                        for j, section in enumerate(input_sections[1:], 1):
                            input_part = section.split('...')[0].strip()
                            if input_part:
                                st.code(f"Tool Input {j}: {input_part}", language="json")
                    
                    # Show raw tool responses if available
                    if "tool_responses" in message and message["tool_responses"]:
                        st.markdown("**🔧 Raw Tool Responses:**")
                        for j, tool_response in enumerate(message["tool_responses"], 1):
                            with st.expander(f"Tool Response {j}"):
                                st.code(tool_response, language="text")
                    else:
                        # If no tool responses captured, show a message
                        if "🔧 Using tool:" in formatted_content:
                            st.info("**Note:** Tool was executed but raw response not captured in streaming. The agent processed the tool output and provided the summary above.")
                    
                    # Only show inferred execution if no explicit tools found
                    if not explicit_tools:
                        execution_info = []
                        content_lower = formatted_content.lower()
                        
                        # More specific keyword detection
                        if "query" in content_lower and ("database" in content_lower or "genomics" in content_lower):
                            execution_info.append("🔍 **Database Query Executed**")
                        if "analy" in content_lower and ("variant" in content_lower or "chromosome" in content_lower):
                            execution_info.append("📊 **Genomic Analysis Performed**")
                        if "chromosome" in content_lower and ("variant" in content_lower):
                            execution_info.append("🔬 **Chromosome-specific Processing**")
                        if ("patient" in content_lower or "sample" in content_lower) and "cohort" in content_lower:
                            execution_info.append("👤 **Cohort Data Processing**")
                        
                        # Display execution summary only if we have meaningful steps
                        if execution_info:
                            st.markdown("**Inferred Execution Steps:**")
                            for info in execution_info:
                                st.markdown(f"- {info}")
                    else:
                        # Show explicit tools
                        st.markdown("**Explicit Tool Usage:**")
                        for tool in explicit_tools:
                            st.info(tool)
                    
                    # Show processing time analysis
                    if "elapsed" in message:
                        processing_time = message["elapsed"]
                        if processing_time > 60:
                            st.error(f"🐌 Very slow: {processing_time:.1f}s - Large dataset processing")
                        elif processing_time > 30:
                            st.warning(f"⚠️ Complex analysis: {processing_time:.1f}s")
                        elif processing_time > 15:
                            st.info(f"ℹ️ Standard processing: {processing_time:.1f}s")
                        else:
                            st.success(f"✅ Quick response: {processing_time:.1f}s")
                    
                    # Show captured chunks for debugging
                    if "chunks" in message and message["chunks"]:
                        chunks = message["chunks"]
                        st.markdown(f"**Streaming Info:** {len(chunks)} chunks received")
                        
                        if st.checkbox("Show AgentCore Chunks", key=f"chunks_{i}"):
                            st.markdown("**Raw Streaming Chunks:**")
                            for j, chunk in enumerate(chunks[:10]):  # Show max 10 chunks
                                with st.expander(f"Chunk {j+1}"):
                                    try:
                                        # Try to parse as JSON
                                        import json
                                        if isinstance(chunk, str) and (chunk.strip().startswith('{') or chunk.strip().startswith('[')):
                                            parsed = json.loads(chunk)
                                            st.json(parsed)
                                        else:
                                            st.code(str(chunk), language="text")
                                    except:
                                        st.code(str(chunk), language="text")
                            
                            if len(chunks) > 10:
                                st.info(f"... and {len(chunks) - 10} more chunks")

    # Handle sample question selection
    if "selected_question" in st.session_state:
        prompt = st.session_state["selected_question"]
        del st.session_state["selected_question"]
        
        # Process the selected question
        if not agent_arn:
            st.error("Please select an agent in the sidebar first.")
        else:
            # Add user message to chat history
            st.session_state.messages.append(
                {"role": "user", "content": prompt, "avatar": HUMAN_AVATAR}
            )
            with st.chat_message("user", avatar=HUMAN_AVATAR):
                st.markdown(prompt)

            # Generate assistant response
            with st.chat_message("assistant", avatar=AI_AVATAR):
                message_placeholder = st.empty()
                start_time = time.time()  # Start timing
                chunk_buffer = ""

                try:
                    # Stream the response
                    captured_chunks = []
                    tool_responses = []
                    for chunk_data in invoke_agent_streaming(
                        prompt,
                        agent_arn,
                        st.session_state.runtime_session_id,
                        region,
                        show_tools,
                    ):
                        captured_chunks.append(chunk_data)
                        
                        if chunk_data["type"] == "text":
                            chunk = chunk_data["content"]
                            if not isinstance(chunk, str):
                                chunk = str(chunk)
                            chunk_buffer += chunk
                            
                            # Update display for every text chunk
                            if auto_format:
                                cleaned_response = clean_response_text(chunk_buffer, show_thinking)
                                message_placeholder.markdown(cleaned_response + " ▌")
                            else:
                                message_placeholder.markdown(chunk_buffer + " ▌")
                        
                        elif chunk_data["type"] == "tool_use" and show_tools:
                            container = st.container(border=True)
                            container.markdown(f"🔧 **{chunk_data['name']}**")
                            container.markdown(f"Tool input: {chunk_data['input']}")
                        
                        elif chunk_data["type"] == "tool_result":
                            tool_responses.append(chunk_data["content"])
                            if show_tools:
                                container = st.container(border=True)
                                container.markdown(f"🔧 Tool result:")
                                container.code(chunk_data["content"], language="text")

                        time.sleep(0.01)

                    # Calculate elapsed time
                    elapsed = time.time() - start_time

                    # Final response without cursor
                    if auto_format:
                        full_response = clean_response_text(chunk_buffer, show_thinking)
                    else:
                        full_response = chunk_buffer

                    # Try to extract tool results from the complete response
                    if "🔧 Using tool:" in chunk_buffer and not tool_responses:
                        # Look for the actual tool output in the agent's response
                        # This is a workaround since the streaming doesn't provide raw tool results
                        import re
                        
                        # Look for patterns that indicate tool results
                        patterns = [
                            r'Based on.*?results.*?(\d+.*?)(?:\.|$)',
                            r'The query.*?shows.*?(\d+.*?)(?:\.|$)',
                            r'Analysis.*?reveals.*?(\d+.*?)(?:\.|$)',
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, chunk_buffer, re.IGNORECASE | re.DOTALL)
                            if match:
                                result = match.group(1).strip()
                                # Clean up markdown formatting
                                result = re.sub(r'\*\*', '', result)
                                tool_responses.append(f"Extracted result: {result}")
                                break
                        
                        # If no pattern matched, add a generic message
                        if not tool_responses:
                            tool_responses.append("Tool executed successfully - see agent response for results")

                    message_placeholder.markdown(full_response)
                    
                    # Show response time
                    st.caption(f"⏱️ Response time: {elapsed:.2f} seconds")

                    # Show raw response in expander if requested
                    if show_raw:
                        with st.expander("View raw response"):
                            st.text(chunk_buffer)

                except Exception as e:
                    elapsed = time.time() - start_time
                    error_msg = f"❌ **Error:** {str(e)}"
                    message_placeholder.markdown(error_msg)
                    full_response = error_msg

            # Add assistant response to chat history
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response, "avatar": AI_AVATAR, "elapsed": elapsed, "raw_content": chunk_buffer, "chunks": captured_chunks, "tool_responses": tool_responses}
            )
            st.rerun()

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        if not agent_arn:
            st.error("Please select an agent in the sidebar first.")
            return

        # Add user message to chat history
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "avatar": HUMAN_AVATAR}
        )
        with st.chat_message("user", avatar=HUMAN_AVATAR):
            st.markdown(prompt)

        # Generate assistant response
        with st.chat_message("assistant", avatar=AI_AVATAR):
            message_placeholder = st.empty()
            start_time = time.time()  # Start timing
            chunk_buffer = ""
            tool_responses = []  # Initialize tool_responses

            try:
                # Stream the response
                captured_chunks = []
                tool_responses = []
                for chunk_data in invoke_agent_streaming(
                    prompt,
                    agent_arn,
                    st.session_state.runtime_session_id,
                    region,
                    show_tools,
                ):
                    captured_chunks.append(chunk_data)
                    
                    if chunk_data["type"] == "text":
                        chunk = chunk_data["content"]
                        logger.debug(f"MAIN LOOP: chunk type: {type(chunk)}")
                        logger.debug(f"MAIN LOOP: chunk content: {chunk}")

                        if not isinstance(chunk, str):
                            chunk = str(chunk)

                        chunk_buffer += chunk

                        # Update display for every text chunk
                        if auto_format:
                            cleaned_response = clean_response_text(chunk_buffer, show_thinking)
                            message_placeholder.markdown(cleaned_response + " ▌")
                        else:
                            message_placeholder.markdown(chunk_buffer + " ▌")
                    
                    elif chunk_data["type"] == "tool_use" and show_tools:
                        container = st.container(border=True)
                        container.markdown(f"🔧 **{chunk_data['name']}**")
                        container.markdown(f"Tool input: {chunk_data['input']}")
                    
                    elif chunk_data["type"] == "tool_result":
                        tool_responses.append(chunk_data["content"])
                        if show_tools:
                            container = st.container(border=True)
                            container.markdown(f"🔧 Tool result:")
                            container.code(chunk_data["content"], language="text")

                    time.sleep(0.01)

                # Calculate elapsed time
                elapsed = time.time() - start_time

                # Final response without cursor
                if auto_format:
                    full_response = clean_response_text(chunk_buffer, show_thinking)
                else:
                    full_response = chunk_buffer

                # Try to extract tool results from the complete response
                if "🔧 Using tool:" in chunk_buffer and not tool_responses:
                    # Look for the actual tool output in the agent's response
                    import re
                    
                    # Look for patterns that indicate tool results
                    patterns = [
                        r'Based on.*?results.*?(\d+.*?)(?:\.|$)',
                        r'The query.*?shows.*?(\d+.*?)(?:\.|$)', 
                        r'Analysis.*?reveals.*?(\d+.*?)(?:\.|$)',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, chunk_buffer, re.IGNORECASE | re.DOTALL)
                        if match:
                            result = match.group(1).strip()
                            # Clean up markdown formatting  
                            result = re.sub(r'\*\*', '', result)
                            tool_responses.append(f"Extracted result: {result}")
                            break
                    
                    # If no pattern matched, add a generic message
                    if not tool_responses:
                        tool_responses.append("Tool executed successfully - see agent response for results")

                message_placeholder.markdown(full_response)
                
                # Show response time
                st.caption(f"⏱️ Response time: {elapsed:.2f} seconds")

                # Show raw response in expander if requested
                if show_raw:
                    with st.expander("View raw response"):
                        st.text(chunk_buffer)

            except Exception as e:
                elapsed = time.time() - start_time
                error_msg = f"❌ **Error:** {str(e)}"
                message_placeholder.markdown(error_msg)
                full_response = error_msg

        # Add assistant response to chat history
        st.session_state.messages.append(
            {"role": "assistant", "content": full_response, "avatar": AI_AVATAR, "elapsed": elapsed, "raw_content": chunk_buffer, "chunks": captured_chunks, "tool_responses": tool_responses}
        )


if __name__ == "__main__":
    main()
