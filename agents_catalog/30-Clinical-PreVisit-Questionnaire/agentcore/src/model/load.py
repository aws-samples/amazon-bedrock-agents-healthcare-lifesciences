from strands.models import BedrockModel

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
FAST_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def load_model() -> BedrockModel:
    """Get primary Bedrock model (Sonnet 4.5)."""
    return BedrockModel(model_id=MODEL_ID)


def load_fast_model() -> BedrockModel:
    """Get fast/cheap Bedrock model (Haiku 4.5)."""
    return BedrockModel(model_id=FAST_MODEL_ID)
