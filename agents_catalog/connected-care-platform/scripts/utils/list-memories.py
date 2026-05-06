"""List all AgentCore Memory stores to find your memory ID."""

from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="us-east-1")
memories = client.list_memories()

if isinstance(memories, list):
    for m in memories:
        mid = m.get("memoryId", m.get("id", "unknown"))
        name = m.get("name", "unnamed")
        status = m.get("status", "")
        print(f"{mid}  --  {name}  --  {status}")
    if not memories:
        print("No memories found. Run: python scripts/create-memory.py")
else:
    print(f"Unexpected response type: {type(memories)}")
    print(memories)
