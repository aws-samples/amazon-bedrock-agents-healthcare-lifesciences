"""Delete and recreate the AgentCore Memory store — wipes all short-term and long-term data."""

import time
from bedrock_agentcore.memory import MemoryClient

MEMORY_ID = "ConnectedCareMemory-fJc1LlBuB3"
client = MemoryClient(region_name="us-east-1")

# Delete
print(f"Deleting memory {MEMORY_ID}...")
try:
    client.delete_memory(memory_id=MEMORY_ID)
except Exception as e:
    print(f"Delete error: {e}")

# Wait for deletion
for i in range(12):
    memories = client.list_memories()
    found = any(m.get("id") == MEMORY_ID for m in memories)
    if not found:
        print("Deleted.")
        break
    print(f"  Waiting... ({i+1})")
    time.sleep(5)

# Recreate
print("Creating fresh memory...")
memory = client.create_memory_and_wait(
    name="ConnectedCareMemory",
    description="Shared memory for Connected Care Platform agents",
    strategies=[
        {"summaryMemoryStrategy": {"name": "SessionSummarizer", "namespaces": ["/summaries/{actorId}/{sessionId}/"]}},
        {"userPreferenceMemoryStrategy": {"name": "ClinicianPreferences", "namespaces": ["/preferences/{actorId}/"]}},
        {"semanticMemoryStrategy": {"name": "ClinicalFacts", "namespaces": ["/facts/{actorId}/"]}},
    ],
)

print(f"\nNew MEMORY_ID: {memory['id']}")
print(f"Redeploy: npx cdk deploy ConnectedCareAgentCoreStack -c memoryId='{memory['id']}' --require-approval never")
