"""Patient Monitoring Agent — Entry Point with AgentCore Memory"""

import os
import logging
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from system_prompt import SYSTEM_PROMPT
from tools import ALL_TOOLS
from config import AGENT_MODEL
from memory_helper import create_session_manager, get_memory_context
from tools.phi_access import set_actor_email

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    prompt = payload.get("prompt", "")
    session_id = payload.get("session_id", "default")
    actor_id = payload.get("actor_id", "system")
    actor_email = payload.get("actor_email", "")

    # Set the actor email for PHI access checks
    set_actor_email(actor_email)

    if not prompt:
        return {"response": "Hello! I'm the Patient Monitoring Agent.", "session_id": session_id}

    # Try with memory first, fall back to stateless if session history is corrupted
    session_manager = create_session_manager(session_id, actor_id)
    try:
        agent_kwargs = dict(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)
        if session_manager:
            agent_kwargs["session_manager"] = session_manager
            logger.info(f"MEMORY_OK: session={session_id} actor={actor_id}")
        else:
            logger.warning(f"MEMORY_NONE: AGENTCORE_MEMORY_ID={os.environ.get('AGENTCORE_MEMORY_ID', 'NOT_SET')}")
        agent = Agent(**agent_kwargs)
        result = agent(prompt)
    except Exception as e:
        error_str = str(e)
        logger.error(f"MEMORY_FAIL: {error_str[:300]}")
        if "toolResult" in error_str or "toolUse" in error_str or "ValidationException" in error_str:
            logger.info("MEMORY_FALLBACK: retrying stateless")
            agent = Agent(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)
            result = agent(prompt)
        else:
            raise

    if session_manager:
        try:
            memory_ctx = get_memory_context(session_manager)
            session_manager.close()
            logger.info("MEMORY_CLOSE: session manager closed successfully")
        except Exception as close_err:
            logger.error(f"MEMORY_CLOSE_FAIL: {close_err}")
            memory_ctx = {"used": False, "short_term": 0, "long_term": []}
    else:
        memory_ctx = {"used": False, "short_term": 0, "long_term": []}

    return {"response": result.message, "session_id": session_id, "memory": memory_ctx}


if __name__ == "__main__":
    if os.environ.get("LOCAL_MODE", "false").lower() == "true":
        print("Patient Monitoring Agent — Local Testing Mode\nType 'quit' to exit.\n")
        while True:
            user_input = input("You: ")
            if user_input.lower() in ("quit", "exit"): break
            result = Agent(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)(user_input)
            print(f"\nAgent: {result.message}\n")
    else:
        app.run()
