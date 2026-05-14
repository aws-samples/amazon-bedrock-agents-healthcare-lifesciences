"""Device Management Agent — Entry Point with AgentCore Memory"""

import os
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from system_prompt import SYSTEM_PROMPT
from tools import ALL_TOOLS
from config import AGENT_MODEL
from memory_helper import create_session_manager, get_memory_context

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    prompt = payload.get("prompt", "")
    session_id = payload.get("session_id", "default")
    actor_id = payload.get("actor_id", "system")

    if not prompt:
        return {"response": "Hello! I'm the Device Management Agent.", "session_id": session_id}

    session_manager = create_session_manager(session_id, actor_id)
    try:
        agent_kwargs = dict(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)
        if session_manager:
            agent_kwargs["session_manager"] = session_manager
        agent = Agent(**agent_kwargs)
        result = agent(prompt)
    except Exception as e:
        if "toolResult" in str(e) or "toolUse" in str(e) or "ValidationException" in str(e):
            print(f"Session history corrupted, retrying stateless: {e}")
            agent = Agent(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)
            result = agent(prompt)
        else:
            raise

    if session_manager:
        try:
            memory_ctx = get_memory_context(session_manager)
            session_manager.close()
        except Exception:
            memory_ctx = {"used": False, "short_term": 0, "long_term": []}
    else:
        memory_ctx = {"used": False, "short_term": 0, "long_term": []}

    return {"response": result.message, "session_id": session_id, "memory": memory_ctx}


if __name__ == "__main__":
    if os.environ.get("LOCAL_MODE", "false").lower() == "true":
        print("Device Management Agent — Local Testing Mode\nType 'quit' to exit.\n")
        while True:
            user_input = input("You: ")
            if user_input.lower() in ("quit", "exit"): break
            result = Agent(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)(user_input)
            print(f"\nAgent: {result.message}\n")
    else:
        app.run()
