"""Clinical PreVisit Questionnaire Agent — AgentCore runtime."""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agents.pvq_agent import PVQStrandsAgent

app = BedrockAgentCoreApp()
log = app.logger


@app.entrypoint
async def invoke(payload, context):
    """Process a pre-visit questionnaire interaction.

    Payload:
        message: str — patient message/response
        mode: str — "fast" for Haiku model, default uses Sonnet
    """
    message = payload.get("message") or payload.get("prompt", "")
    mode = payload.get("mode", "standard")

    if mode == "fast":
        from agents.pvq_agent_fast import FastPVQAgent
        agent_instance = FastPVQAgent()
    else:
        agent_instance = PVQStrandsAgent()

    response = agent_instance.chat(message)
    yield response


if __name__ == "__main__":
    app.run()
