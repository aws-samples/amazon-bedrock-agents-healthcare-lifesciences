"""
Agent Discovery Module
Dynamically discovers AgentCore runtimes in the account
"""
from typing import List, Dict, Optional
import boto3
import streamlit as st


# Module-level cached functions (better for Streamlit caching)
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_agent_runtimes(region: str = "us-east-1") -> List[Dict]:
    """
    Fetch available agent runtimes from bedrock-agentcore-control
    
    Args:
        region: AWS region to query
        
    Returns:
        List of agent runtime dictionaries with status, ARN, name, etc.
    """
    try:
        client = boto3.client("bedrock-agentcore-control", region_name=region)
        response = client.list_agent_runtimes(maxResults=100)
        
        # Filter only READY agents
        ready_agents = [
            agent
            for agent in response.get("agentRuntimes", [])
            if agent.get("status") == "READY"
        ]
        
        # Sort by most recent update time (newest first)
        ready_agents.sort(
            key=lambda x: x.get("lastUpdatedAt", ""), 
            reverse=True
        )
        
        return ready_agents
        
    except Exception as e:
        st.error(f"Error fetching agent runtimes: {e}")
        return []


@st.cache_data(ttl=300)
def fetch_agent_runtime_versions(
    agent_runtime_id: str,
    region: str = "us-east-1"
) -> List[Dict]:
    """
    Fetch versions for a specific agent runtime
    
    Args:
        agent_runtime_id: The agent runtime ID
        region: AWS region to query
        
    Returns:
        List of agent runtime version dictionaries
    """
    try:
        client = boto3.client("bedrock-agentcore-control", region_name=region)
        response = client.list_agent_runtime_versions(
            agentRuntimeId=agent_runtime_id
        )
        
        # Filter only READY versions
        ready_versions = [
            version
            for version in response.get("agentRuntimes", [])
            if version.get("status") == "READY"
        ]
        
        # Sort by most recent update time (newest first)
        ready_versions.sort(
            key=lambda x: x.get("lastUpdatedAt", ""), 
            reverse=True
        )
        
        return ready_versions
        
    except Exception as e:
        st.error(f"Error fetching agent runtime versions: {e}")
        return []


class AgentDiscovery:
    """Handles dynamic discovery of AgentCore runtimes"""
    
    def __init__(self, region: Optional[str] = None):
        self.region = region or "us-east-1"
    
    def fetch_agent_runtimes(self) -> List[Dict]:
        """
        Fetch available agent runtimes (delegates to cached function)
        
        Returns:
            List of agent runtime dictionaries
        """
        return fetch_agent_runtimes(self.region)
    
    def fetch_agent_runtime_versions(self, agent_runtime_id: str) -> List[Dict]:
        """
        Fetch versions for a specific agent runtime (delegates to cached function)
        
        Args:
            agent_runtime_id: The agent runtime ID
            
        Returns:
            List of agent runtime version dictionaries
        """
        return fetch_agent_runtime_versions(agent_runtime_id, self.region)
    
    def format_agent_display_name(self, agent: Dict) -> str:
        """
        Format agent information for display in dropdown
        
        Args:
            agent: Agent runtime dictionary
            
        Returns:
            Formatted string for display
        """
        name = agent.get("agentRuntimeName", "Unnamed")
        agent_id = agent.get("agentRuntimeId", "")
        version = agent.get("agentRuntimeVersion", "")
        
        if version:
            return f"{name} (v{version})"
        return f"{name} ({agent_id[:8]}...)"
    
    def get_agent_arn(self, agent: Dict) -> str:
        """
        Extract agent ARN from agent dictionary
        
        Args:
            agent: Agent runtime dictionary
            
        Returns:
            Agent ARN string
        """
        return agent.get("agentRuntimeArn", "")
    
    def get_agent_id(self, agent: Dict) -> str:
        """
        Extract agent ID from agent dictionary
        
        Args:
            agent: Agent runtime dictionary
            
        Returns:
            Agent ID string
        """
        return agent.get("agentRuntimeId", "")
