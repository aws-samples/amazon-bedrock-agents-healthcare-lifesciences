# Model Switching Fix Documentation

## Issue Description

When switching between different models mid-conversation in the Streamlit UI, the following error occurred:

```
Error processing request: An error occurred (ValidationException) when calling the ConverseStream operation: 
The model returned the following errors: messages.6: tool_use ids were found without tool_result blocks 
immediately after: tooluse_DS8cf_vtQWaa84S2-v9MGg. Each tool_use block must have a corresponding tool_result 
block in the next message.
```

## Root Cause

The issue stemmed from how conversation history is stored and retrieved when switching models:

1. **Memory Storage Limitation**: The AgentCore memory system stores only the text content of messages, not the complete message structure including tool execution blocks
2. **History Loading**: When a new agent is initialized (e.g., when switching models), it loads the last 5 conversation turns from memory
3. **Incomplete Tool Records**: If previous messages included tool usage, only the text representation was saved, creating incomplete tool execution records
4. **API Validation Failure**: Bedrock's Converse API validates that every `tool_use` block has a corresponding `tool_result` block, and fails when this requirement isn't met

## Solution

Modified `agent/agent_config/memory_hook_provider.py` to filter out messages containing tool references when loading conversation history:

### Key Changes

1. **Added Tool Reference Detection**:
```python
def _contains_tool_references(self, content: str) -> bool:
    """Check if content contains references to tool usage that might be incomplete"""
    tool_indicators = [
        "🔧 Using tool:",
        "tool_use",
        "tooluse_",
        "tool_result",
        "toolResult"
    ]
    return any(indicator in content for indicator in tool_indicators)
```

2. **Modified History Loading**:
```python
# Only add messages that don't reference tool usage
# This prevents incomplete tool execution records when switching models
if not self._contains_tool_references(content):
    context_messages.append(
        {"role": role, "content": [{"text": content}]}
    )
```

## Benefits

- **Clean Model Switching**: Users can now switch between models (Claude Sonnet 4, Haiku, Nova Premier, etc.) mid-conversation without errors
- **Maintains Context**: Regular conversation history is still preserved and loaded
- **Prevents API Errors**: Filters out incomplete tool execution records that would cause validation failures
- **Backwards Compatible**: Doesn't affect conversations without tool usage

## Testing

### Manual Test via Streamlit UI

1. Start the Streamlit app:
```bash
cd agents_catalog/28-Research-agent-biomni-gateway-tools
uv run streamlit run app.py --server.port 8502
```

2. Test scenario:
   - Start a conversation with Claude Sonnet 4
   - Ask a query that uses tools (e.g., "Find information about insulin protein")
   - After the response, switch to a different model (e.g., Nova Premier) using the sidebar dropdown
   - Ask another question
   - Verify no validation errors occur

### Automated Test

Run the model update test script:
```bash
cd agents_catalog/28-Research-agent-biomni-gateway-tools
uv run python tests/test_model_update.py
```

This test:
- Initializes an agent with a query
- Switches between 3 different models
- Verifies each model can process queries successfully
- Tests both Claude and non-Claude models (QWEN)

## Limitations

- **Tool History Loss**: When switching models, the context of previous tool usages is not carried forward
- **Text-Only Memory**: Only the final text responses are preserved in memory, not the intermediate tool executions
- **Session Continuity**: For complex multi-turn tool-using conversations, consider starting a new session when switching models

## Alternative Approaches Considered

1. **Store Complete Message Structure**: Would require changes to how AgentCore memory stores conversation data
2. **Model-Specific Memory**: Maintain separate memory for each model type
3. **Tool Result Reconstruction**: Attempt to reconstruct missing tool_result blocks (too complex and error-prone)

## Recommendations

- **Best Practice**: For conversations heavily using tools, consider starting a new session when switching models
- **Session Reset**: Use the "Refresh" button in the Streamlit sidebar to generate a new session ID and clear chat history
- **Model Selection**: Choose the appropriate model before starting a complex research query

## Related Files

- `agent/agent_config/memory_hook_provider.py` - Memory hook implementation with the fix
- `agent/agent_config/agent.py` - Agent initialization and model configuration
- `app.py` - Streamlit UI with model selection dropdown
- `tests/test_model_update.py` - Automated test for model switching

## Date: 2025-11-19
## Fixed By: Memory Hook Provider Update
