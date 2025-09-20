import streamlit as st
import json
import time
import uuid
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
import pandas as pd
from typing import Any, Generator, Dict, List
import subprocess
import tempfile
import os
from datetime import datetime

class GenomicsAgentUI:
    def __init__(self):
        self.region = "<YOUR_REGION>"
        self._init_session_state()
        self._init_agentcore_runtime()
        
    def _init_agentcore_runtime(self):
        """Initialize direct AgentCore connection"""
        try:
            # Your deployed AgentCore endpoint
            self.agentcore_endpoint = "arn:aws:bedrock-agentcore:<YOUR_REGION>:<YOUR_ACCOUNT_ID>:runtime/<YOUR_AGENT_ID>"
            
            # Use boto3 session for auth
            import boto3
            self.session = boto3.Session()
            self.credentials = self.session.get_credentials()
            
            st.session_state["aws_authenticated"] = True
            st.session_state["client_initialized"] = True
            return True
        except Exception as e:
            st.error(f"❌ Failed to initialize AgentCore connection: {str(e)}")
            return False

    def invoke_agent_with_context(self, prompt: str) -> Generator[Dict, None, None]:
        """Invoke AgentCore with conversation context"""
        try:
            context_prompt = self._build_context_prompt(prompt)
            payload = {"prompt": context_prompt}
            
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_file:
                temp_filename = temp_file.name
            
            try:
                cmd = [
                    "aws", "bedrock-agentcore", "invoke-agent-runtime",
                    "--agent-runtime-arn", self.agentcore_endpoint,
                    "--payload", json.dumps(payload),
                    "--region", self.region,
                    "--cli-read-timeout", "600",
                    "--cli-connect-timeout", "120",
                    temp_filename
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=360)
                
                if result.returncode == 0:
                    with open(temp_filename, 'r') as f:
                        output = f.read()
                    
                    if output.strip():
                        for line in output.strip().split('\n'):
                            if line.startswith('data: '):
                                data_content = line[6:]
                                try:
                                    parsed_content = json.loads(data_content)
                                    yield {"type": "response", "content": parsed_content}
                                except json.JSONDecodeError:
                                    yield {"type": "response", "content": data_content}
                    else:
                        yield {"type": "error", "content": "No response received from AgentCore"}
                else:
                    yield {"type": "error", "content": f"AWS CLI Error: {result.stderr}"}
                    
            except subprocess.TimeoutExpired:
                yield {"type": "error", "content": "Request timed out"}
            finally:
                if os.path.exists(temp_filename):
                    os.unlink(temp_filename)
                
        except Exception as e:
            yield {"type": "error", "content": f"Error: {str(e)}"}

    def _init_session_state(self):
        """Initialize session state variables with persistence"""
        if "session_id" not in st.session_state:
            st.session_state["session_id"] = str(uuid.uuid4())
        if "messages" not in st.session_state:
            st.session_state["messages"] = []
        if "conversation_context" not in st.session_state:
            st.session_state["conversation_context"] = []
        if "execution_logs" not in st.session_state:
            st.session_state["execution_logs"] = []
        if "aws_authenticated" not in st.session_state:
            st.session_state["aws_authenticated"] = False
        if "client_initialized" not in st.session_state:
            st.session_state["client_initialized"] = False

    def display_chat_history(self):
        """Display chat messages from history with execution logs"""
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    if message.get("error", False):
                        st.error(message["content"])
                    else:
                        st.markdown(message["content"])
                    
                    # Show execution time
                    if "elapsed" in message:
                        st.caption(f"⏱️ Response time: {message['elapsed']:.2f} seconds")
                    
                    # Show execution logs if available
                    if "execution_logs" in message and message["execution_logs"]:
                        with st.expander("🔍 View Execution Trace", expanded=False):
                            self.display_execution_logs(message["execution_logs"])
                else:
                    st.markdown(message["content"])

    def display_execution_logs(self, logs: List[Dict]):
        """Display execution logs including CloudWatch logs and model traces"""
        if not logs:
            st.info("No execution logs available for this response.")
            return
        
        for i, log in enumerate(logs):
            log_type = log.get("type", "unknown")
            
            if log_type == "cloudwatch_log":
                with st.expander(f"📋 CloudWatch Log {i+1}", expanded=False):
                    if "log_data" in log:
                        st.json(log["log_data"])
                    else:
                        st.code(log.get("message", ""), language="text")
                    st.caption(f"🕒 {log.get('timestamp', '')}")
            
            elif log_type == "model_trace":
                with st.expander(f"🧠 Model Trace {i+1}", expanded=False):
                    trace_data = log.get("trace_data", {})
                    
                    # Show tool calls
                    if "toolUse" in trace_data:
                        st.markdown("**🔧 Tool Usage:**")
                        st.json(trace_data["toolUse"])
                    
                    # Show reasoning
                    if "reasoning" in trace_data:
                        st.markdown("**💭 Model Reasoning:**")
                        st.markdown(trace_data["reasoning"])
                    
                    # Show raw trace
                    st.markdown("**📊 Raw Trace:**")
                    st.json(trace_data)
            
            else:
                # Fallback for other log types
                content = log.get("content", "")
                timestamp = log.get("timestamp", "")
                st.info(f"ℹ️ {content}")
                if timestamp:
                    st.caption(f"🕒 {timestamp}")
            
            if i < len(logs) - 1:
                st.divider()

    def process_user_message(self, prompt: str):
        """Process a user message with session context and execution logging"""
        # Add user message
        user_message = {
            "role": "user", 
            "content": prompt,
            "timestamp": datetime.now().isoformat(),
            "session_id": st.session_state["session_id"]
        }
        st.session_state.messages.append(user_message)
        
        # Add to conversation context for session persistence
        st.session_state.conversation_context.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get assistant response with execution logging
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            trace_placeholder = st.empty()
            start_time = time.time()
            
            message_placeholder.markdown("🧬 Genomics Agent is analyzing your query...")
            
            accumulated_response = ""
            execution_logs = []
            is_error = False
            
            for chunk in self.invoke_agent_with_context(prompt):
                chunk_type = chunk.get("type", "response")
                chunk_content = chunk.get("content", "")
                
                if chunk_type == "response":
                    if isinstance(chunk_content, str):
                        accumulated_response += chunk_content
                    else:
                        accumulated_response += str(chunk_content)
                    
                    if accumulated_response.startswith("❌") or "error" in accumulated_response.lower():
                        is_error = True
                        message_placeholder.error(accumulated_response)
                    else:
                        message_placeholder.markdown(f"{accumulated_response}▌")
                
                elif chunk_type == "cloudwatch_log":
                    log_entry = {
                        "type": "cloudwatch_log",
                        "log_data": chunk.get("log_data"),
                        "message": chunk.get("message"),
                        "timestamp": chunk.get("timestamp", datetime.now().isoformat())
                    }
                    execution_logs.append(log_entry)
                
                elif chunk_type == "model_trace":
                    log_entry = {
                        "type": "model_trace",
                        "trace_data": chunk.get("trace_data", {}),
                        "timestamp": datetime.now().isoformat()
                    }
                    execution_logs.append(log_entry)
                
                elif chunk_type == "error":
                    is_error = True
                    accumulated_response = chunk_content
                    message_placeholder.error(accumulated_response)
                    
                    log_entry = {
                        "type": "error",
                        "content": chunk_content,
                        "timestamp": datetime.now().isoformat()
                    }
                    execution_logs.append(log_entry)
                    break
                
                time.sleep(0.02)
            
            elapsed = time.time() - start_time
            
            # Final display
            if is_error:
                message_placeholder.error(accumulated_response)
            else:
                message_placeholder.markdown(accumulated_response)
            
            # Clear the trace placeholder
            trace_placeholder.empty()
            
            # Add assistant message to history with execution logs
            assistant_message = {
                "role": "assistant",
                "content": accumulated_response,
                "elapsed": elapsed,
                "error": is_error,
                "execution_logs": execution_logs,
                "timestamp": datetime.now().isoformat(),
                "session_id": st.session_state["session_id"]
            }
            st.session_state.messages.append(assistant_message)
            
            # Add to conversation context
            st.session_state.conversation_context.append({
                "role": "assistant",
                "content": accumulated_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Store logs separately for analysis
            st.session_state.execution_logs.extend(execution_logs)

    def _build_context_prompt(self, current_prompt: str) -> str:
        """Build context-aware prompt with conversation history"""
        if not st.session_state.conversation_context:
            return current_prompt
        
        # Get last few exchanges for context (limit to prevent token overflow)
        recent_context = st.session_state.conversation_context[-4:]  # Last 2 exchanges
        
        if not recent_context:
            return current_prompt
        
        context_str = "Previous conversation in this session:\n"
        for ctx in recent_context:
            role = ctx["role"].title()
            content = ctx["content"][:300] + "..." if len(ctx["content"]) > 300 else ctx["content"]
            context_str += f"{role}: {content}\n"
        
        context_str += f"\nCurrent question: {current_prompt}"
        context_str += "\n\nPlease provide a response that considers the previous conversation context when relevant."
        
        return context_str

def render_sidebar():
    """Render the sidebar with agent information and sample questions"""
    with st.sidebar:
        st.title("🔬 Agent Configuration")
        
        # Session information
        st.subheader("🔗 Session Details")
        st.write("**Session ID:**")
        st.code(st.session_state["session_id"][:8] + "...", language="text")
        st.write("**Messages in Session:**", len(st.session_state.messages))
        st.write("**Context Entries:**", len(st.session_state.conversation_context))
        
        # Show session persistence status
        if len(st.session_state.conversation_context) > 0:
            st.success("✅ Session context active")
        else:
            st.info("ℹ️ New session - no context yet")
        
        # Agent information
        st.subheader("📊 Connection Details")
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.session_state.get("aws_authenticated", False):
                st.success("✅")
            else:
                st.error("❌")
        with col2:
            st.write("AWS Authentication")
        
        if st.session_state.get("aws_authenticated", False):
            st.write("**Region:**", "<YOUR_REGION>")
            st.write("**Agent ID:**")
            st.code("vcf_agent_supervisor-9Y2ejKDXJE", language="text")
        
        st.markdown("---")
        
        # Execution logs summary
        if st.session_state.execution_logs:
            st.subheader("🔍 Execution Summary")
            log_count = len(st.session_state.execution_logs)
            st.metric("Total Log Entries", log_count)
            
            # Count different types of logs
            trace_count = sum(1 for log in st.session_state.execution_logs if log.get("type") == "trace")
            error_count = sum(1 for log in st.session_state.execution_logs if log.get("type") == "error")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Traces", trace_count)
            with col2:
                st.metric("Errors", error_count)
        
        st.markdown("---")
        
        # Sample questions
        st.subheader("💡 Sample Questions")
        
        sample_questions = [
            ("👥", "How many patients are in the present cohort?"),
            ("🧬", "Analyze chromosome 17 variants in patient NA21144?"),
            ("✅", "Whats the frequency of chr13:32332591 in BRCA2 variant in this cohort and 1000 genome cohort(1000g)?"),
            ("🔬", "Can you check howmany variants are present for BRCA family of genes in patient 'NA21144' and any clinical significance need to be known?"),
            ("📊", "Analyze patient NA21135 for risk stratification"),
            ("💊", "which are the major drug related impactful variant pathway enriched in the patients in the cohort and tell me the allele frequecy reported here and 1000 genome(1000g)?"),
            ("⚠️", "What are the key genomics aberrations linked with heart disease conditions in patient NA21135"),
            ("🧪", "Analyze the patients cohort and provide a comprehensive clinical summary including: individual risk stratification, population-level insights, shared pathogenic variants, personalized medicine recommendations, and clinical prioritization for genetic counseling. And let me know how do you assess the risk and prioritization?")
        ]
        
        for i, (emoji, question) in enumerate(sample_questions):
            if st.button(f"{emoji} {question}", key=f"sample_{i}", use_container_width=True):
                st.session_state["selected_question"] = question
        
        st.markdown("---")
        
        # Session management
        st.subheader("🔄 Session Management")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state["messages"] = []
                st.session_state["execution_logs"] = []
                st.rerun()
        
        with col2:
            if st.button("🔄 New Session", use_container_width=True):
                st.session_state["messages"] = []
                st.session_state["conversation_context"] = []
                st.session_state["execution_logs"] = []
                st.session_state["session_id"] = str(uuid.uuid4())
                st.rerun()

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Genomics Store Agent",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.2rem;
        opacity: 0.9;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .chat-input-container {
        position: sticky;
        bottom: 0;
        background: white;
        padding: 1rem 0;
        border-top: 1px solid #e0e0e0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize the UI
    genomics_ui = GenomicsAgentUI()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🧬 Genomics Variant Analysis Agent</h1>
        <p>Deeper insights on your patients Variant Call File</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render sidebar
    render_sidebar()
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Check AWS authentication
        if not st.session_state.get("aws_authenticated", False):
            st.error("🔐 **AWS Authentication Required**")
            st.markdown("""
            Please ensure your AWS credentials are configured:
            - Use `aws configure` to set up credentials
            - Set environment variables `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
            - Use IAM roles if running on EC2/ECS
            - Ensure you have permissions for `bedrock-agent-runtime:InvokeAgent`
            """)
            return
        
        # Chat interface
        st.markdown("### 💬 Chat Interface")
        
        # Display chat history
        if st.session_state.messages:
            genomics_ui.display_chat_history()
        else:
            st.info("👋 **Welcome to the Genomics Variant Agent!**\n\n✨ I can help you analyze genomic variants, clinical significance, patient risk stratification, and more. Try asking a question!")
    
    with col2:
        # Quick stats
        st.markdown("### 📈 Session Stats")
        if st.session_state.messages:
            user_messages = [m for m in st.session_state.messages if m["role"] == "user"]
            assistant_messages = [m for m in st.session_state.messages if m["role"] == "assistant"]
            
            st.metric("Questions Asked", len(user_messages))
            st.metric("Responses Generated", len(assistant_messages))
            st.metric("Execution Logs", len(st.session_state.execution_logs))
            
            if assistant_messages:
                avg_time = sum(m.get("elapsed", 0) for m in assistant_messages) / len(assistant_messages)
                st.metric("Avg Response Time", f"{avg_time:.1f}s")
        
        # Session context info
        st.markdown("### 🔗 Context Status")
        context_count = len(st.session_state.conversation_context)
        if context_count > 0:
            st.success(f"✅ **Active Session**\n\n{context_count} context entries\n\nYour conversation history is being used to provide better contextual responses.")
        else:
            st.info("ℹ️ **New Session**\n\nNo conversation context yet. Start chatting to build context for better responses!")
    
    # Handle sample question selection
    if "selected_question" in st.session_state:
        genomics_ui.process_user_message(st.session_state["selected_question"])
        del st.session_state["selected_question"]
        st.rerun()
    
    # Chat input (sticky at bottom)
    st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
    if prompt := st.chat_input("Ask about genomic variants, clinical significance, patient analysis, or risk stratification..."):
        genomics_ui.process_user_message(prompt)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p>🧬 <strong>Enhanced Genomics Store Agent</strong> | Session Persistence & Execution Traces</p>
        <p><em>Powered by AWS HealthOmics, Bedrock AgentCore & Streamlit</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
