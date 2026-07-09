"""
Shared utility: Extract tool call traces from a Strands agent result.

Parses the agent's conversation history to find tool_use and tool_result blocks,
returning a structured list of tool calls with names, inputs, and timing.
"""


def extract_tool_calls(result) -> list[dict]:
    """Extract tool call info from a Strands agent result.

    Strands stores the full conversation in result.messages or the agent's
    message history. Each tool call appears as a content block with type='tool_use'
    followed by a 'tool_result' block.
    """
    tool_calls = []

    try:
        # Strands agent result has .messages with the full conversation
        messages = getattr(result, "messages", None)
        if not messages:
            return tool_calls

        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_name = block.get("name", "unknown")
                    tool_input = block.get("input", {})
                    # Summarize input — keep it short for trace display
                    input_summary = _summarize_input(tool_input)
                    tool_calls.append({
                        "tool": tool_name,
                        "input": input_summary,
                    })
    except Exception:
        pass

    return tool_calls


def _summarize_input(tool_input: dict) -> str:
    """Create a short summary of tool input for display."""
    if not tool_input:
        return ""
    parts = []
    for key, value in tool_input.items():
        val_str = str(value)
        if len(val_str) > 60:
            val_str = val_str[:57] + "..."
        parts.append(f"{key}={val_str}")
    summary = ", ".join(parts)
    return summary[:200] if len(summary) > 200 else summary
