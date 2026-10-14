"""Create the AgentCore Memory store for Connected Care Platform.

Run once: python scripts/create-memory.py
Outputs the MEMORY_ID to set as an environment variable in CDK.
"""

from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name="us-east-1")

memory = client.create_memory_and_wait(
    name="ConnectedCareMemory",
    description="Shared memory for Connected Care Platform agents",
    strategies=[
        {
            "summaryMemoryStrategy": {
                "name": "SessionSummarizer",
                "namespaces": ["/summaries/{actorId}/{sessionId}/"],
            }
        },
        {
            "userPreferenceMemoryStrategy": {
                "name": "ClinicianPreferences",
                "namespaces": ["/preferences/{actorId}/"],
            }
        },
        {
            "semanticMemoryStrategy": {
                "name": "ClinicalFacts",
                "namespaces": ["/facts/{actorId}/"],
            }
        },
    ],
)

print(f"\nMemory created successfully!")
print(f"MEMORY_ID: {memory['id']}")
print(f"\nDeploy with:")
print(f"  npx cdk deploy ConnectedCareAgentCoreStack -c memoryId='{memory['id']}' --require-approval never")
