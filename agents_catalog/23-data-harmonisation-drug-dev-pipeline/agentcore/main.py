"""BedrockAgentCoreApp entrypoint for Drug Development Pipeline Data Harmonization Agent."""

from bedrock_agentcore.app import BedrockAgentCoreApp
from agent.agent_config.agent import agent_task

app = BedrockAgentCoreApp()
app.register(agent_task)

if __name__ == "__main__":
    app.run()
