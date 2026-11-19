"""Orchestrator Agent — Entry Point with AgentCore Memory"""

import os
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from system_prompt import SYSTEM_PROMPT
from config import AGENT_MODEL
from memory_helper import create_session_manager, get_memory_context

from tools.invoke_patient_monitoring import invoke_patient_monitoring
from tools.invoke_device_management import invoke_device_management
from tools.invoke_patient_engagement import invoke_patient_engagement
from tools.invoke_inventory_management import invoke_inventory_management
from tools.invoke_field_service import invoke_field_service
from tools.invoke_account_intelligence import invoke_account_intelligence
from tools.publish_workflow_event import publish_workflow_event

AGENT_TOOLS = [
    invoke_patient_monitoring,
    invoke_device_management,
    invoke_patient_engagement,
    invoke_inventory_management,
    invoke_field_service,
    invoke_account_intelligence,
    publish_workflow_event,
]

if not os.environ.get("PM_RUNTIME_ARN"):
    try:
        from tools.execute_workflow import execute_workflow
        AGENT_TOOLS.append(execute_workflow)
    except Exception:
        pass

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    prompt = payload.get("prompt", "")
    session_id = payload.get("session_id", "default")
    request_id = payload.get("request_id", "")
    actor_id = payload.get("actor_id", "system")

    if not prompt:
        return {"response": "I'm the Orchestrator Agent.", "session_id": session_id}

    from tools import invoke_agent as invoke_agent_module
    invoke_agent_module.set_request_id(request_id)

    session_manager = create_session_manager(session_id, actor_id)
    try:
        agent_kwargs = dict(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=AGENT_TOOLS)
        if session_manager:
            agent_kwargs["session_manager"] = session_manager
        agent = Agent(**agent_kwargs)
        result = agent(prompt)
    except Exception as e:
        if "toolResult" in str(e) or "toolUse" in str(e) or "ValidationException" in str(e):
            print(f"Session history corrupted, retrying stateless: {e}")
            agent = Agent(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=AGENT_TOOLS)
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
        print("Orchestrator Agent — Local Testing Mode\nType 'quit' to exit.\n")
        while True:
            user_input = input("You: ")
            if user_input.lower() in ("quit", "exit"): break
            agent = Agent(model=AGENT_MODEL, system_prompt=SYSTEM_PROMPT, tools=AGENT_TOOLS)
            result = agent(user_input)
            print(f"\nAgent: {result.message}\n")
    else:
        app.run()
