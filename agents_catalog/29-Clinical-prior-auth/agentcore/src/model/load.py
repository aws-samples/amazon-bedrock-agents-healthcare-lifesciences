from strands.models import BedrockModel

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def load_model() -> BedrockModel:
    """Get Bedrock model client for prior auth agent."""
    return BedrockModel(model_id=MODEL_ID)
