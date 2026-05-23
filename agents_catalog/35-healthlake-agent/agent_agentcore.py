"""
HealthLake Agent - AgentCore Runtime Wrapper

This module wraps the existing Strands agent for deployment to AWS Bedrock AgentCore.
"""

from bedrock_agentcore import BedrockAgentCoreApp
from agent import get_agent_instance
from models.session import SessionContext
import logging

logger = logging.getLogger(__name__)

# Initialize AgentCore app
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    """
    AgentCore entrypoint for the HealthLake agent.
    
    Args:
        payload: Request payload with 'prompt' and optional 'session_id', 'context'
        context: AgentCore runtime context (RequestContext object)
    
    Returns:
        Response dictionary with 'result' and metadata
    """
    try:
        # Extract parameters
        query = payload.get("prompt", "")
        session_id = payload.get("session_id", getattr(context, "session_id", "default"))
        user_context = payload.get("context", {})
        
        # Default session context if not provided
        if not user_context:
            user_context = {
                "user_id": "agentcore-user",
                "user_role": "admin",  # Valid roles: patient, service_rep, doctor, nurse, admin
                "active_member_id": None
            }
        
        # Convert to SessionContext
        session_context = SessionContext.from_dict(user_context)
        
        # Get agent instance
        agent = get_agent_instance()
        
        # Process query
        agent_result = agent(
            query,
            invocation_state={
                "session_id": session_id,
                **session_context.to_dict()
            }
        )
        
        # Return result
        return {
            "result": str(agent_result),
            "session_id": session_id,
            "metadata": {
                "type": "success",
                "agent_version": "1.0.0"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in AgentCore invoke: {str(e)}", exc_info=True)
        return {
            "result": f"Error processing request: {str(e)}",
            "session_id": session_id,
            "metadata": {
                "type": "error",
                "error": str(e)
            }
        }


if __name__ == "__main__":
    app.run()
