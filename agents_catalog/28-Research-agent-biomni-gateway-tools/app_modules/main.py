import sys
import streamlit as st
from .auth import AuthManager
from .chat import ChatManager
from .styles import apply_custom_styles
from .agent_discovery import AgentDiscovery


def main():
    """Main application entry point"""
    # Parse command line arguments
    agent_name = "default"
    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg.startswith("--agent="):
                agent_name = arg.split("=")[1]

    # Configure page
    st.set_page_config(layout="wide")

    # Apply custom styles
    apply_custom_styles()

    # Initialize managers
    auth_manager = AuthManager()
    chat_manager = ChatManager(agent_name)

    # Handle OAuth callback
    auth_manager.handle_oauth_callback()

    # Check authentication status
    if auth_manager.is_authenticated():
        # Authenticated user interface
        render_authenticated_interface(auth_manager, chat_manager)
    else:
        # Login interface
        render_login_interface(auth_manager)


def render_authenticated_interface(
    auth_manager: AuthManager, chat_manager: ChatManager
):
    """Render the interface for authenticated users"""
    # Get user info and tokens
    tokens = auth_manager.get_tokens()
    user_claims = auth_manager.get_user_claims()
    
    # Sidebar - Agent Selection
    st.sidebar.title("🤖 Agent Selection")
    
    # Initialize agent discovery
    region = st.session_state.get("region", "us-east-1")
    agent_discovery = AgentDiscovery(region=region)
    
    # Fetch available agents
    with st.sidebar:
        with st.spinner("Loading available agents..."):
            available_agents = agent_discovery.fetch_agent_runtimes()
        
        if available_agents:
            # Create dropdown options
            agent_options = {
                agent_discovery.format_agent_display_name(agent): agent
                for agent in available_agents
            }
            
            # Get current agent ARN if set
            current_arn = st.session_state.get("agent_arn")
            
            # Find current selection index
            default_index = 0
            if current_arn:
                for idx, agent in enumerate(available_agents):
                    if agent_discovery.get_agent_arn(agent) == current_arn:
                        default_index = idx
                        break
            
            # Agent selection dropdown
            selected_display_name = st.selectbox(
                "Select Agent Runtime",
                options=list(agent_options.keys()),
                index=default_index,
                help="Choose an AgentCore runtime to interact with"
            )
            
            selected_agent = agent_options[selected_display_name]
            selected_arn = agent_discovery.get_agent_arn(selected_agent)
            
            # Update session state if agent changed
            if st.session_state.get("agent_arn") != selected_arn:
                st.session_state["agent_arn"] = selected_arn
                st.session_state["messages"] = []  # Clear chat history
                st.rerun()
            
            # Show agent details
            with st.expander("Agent Details"):
                st.write(f"**Name:** {selected_agent.get('agentRuntimeName', 'N/A')}")
                st.write(f"**ID:** {selected_agent.get('agentRuntimeId', 'N/A')}")
                st.write(f"**Version:** {selected_agent.get('agentRuntimeVersion', 'N/A')}")
                st.write(f"**Status:** {selected_agent.get('status', 'N/A')}")
        else:
            st.warning("No READY agent runtimes found in your account.")
            st.info("Please deploy an AgentCore runtime first.")
    
    # Sidebar - Session Info
    st.sidebar.markdown("---")
    st.sidebar.title("📋 Session Info")
    
    with st.sidebar.expander("Access Tokens"):
        st.code(auth_manager.cookies.get("tokens"))
    
    with st.sidebar.expander("Agent ARN"):
        st.code(st.session_state.get("agent_arn", "Not selected"))
    
    with st.sidebar.expander("Session ID"):
        st.code(st.session_state.get("session_id", "Not initialized"))
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        auth_manager.logout()

    # Main content
    st.title("Research Agent with Biomni Gateway")
    st.markdown(
        """
        <hr style='border:1px solid #298dff;'>
        """,
        unsafe_allow_html=True,
    )
    
    # Check if agent is selected
    if not st.session_state.get("agent_arn"):
        st.warning("⚠️ Please select an agent from the sidebar to start chatting.")
        return
    
    # Display chat history
    chat_manager.display_chat_history()

    # Chat input
    if prompt := st.chat_input("Ask Research Agent questions!"):
        chat_manager.process_user_message(prompt, user_claims, tokens["access_token"])


def render_login_interface(auth_manager: AuthManager):
    """Render the login interface"""
    login_url = auth_manager.get_login_url()
    st.markdown(
        f'<meta http-equiv="refresh" content="0;url={login_url}">',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
