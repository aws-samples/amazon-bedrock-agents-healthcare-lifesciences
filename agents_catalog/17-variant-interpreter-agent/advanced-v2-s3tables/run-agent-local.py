#!/usr/bin/env python3
"""Interactive local runner for the S3 Tables variant interpreter agent."""

import os
import sys

os.environ["BYPASS_TOOL_CONSENT"] = "true"

from strands import Agent
from strands.models import BedrockModel
from agent.tools.schema_tool import get_table_schema
from agent.tools.query_tool import execute_query, get_cohort_summary
from agent.prompts import SYSTEM_PROMPT



def main():
    required = ['AWS_REGION', 'ATHENA_DATABASE', 'ATHENA_CATALOG', 'VEP_OUTPUT_BUCKET']
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}\n   Run: source .agent-config")
        return 1

    model = BedrockModel(
        model_id=os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'),
        region_name=os.environ.get('AWS_REGION', 'us-west-2'),
        streaming=True
    )

    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[get_table_schema, execute_query, get_cohort_summary]
    )

    print("\n🧬 S3 Tables Variant Interpreter Agent (Local)")
    print("=" * 50)
    print(f"Region: {os.environ.get('AWS_REGION')} | DB: {os.environ.get('ATHENA_DATABASE')}")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            query = input("🧬 > ").strip()
            if not query:
                continue
            if query.lower() in ('quit', 'exit', 'q'):
                break
            result = agent(query)
            print(f"\n{result}\n")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

    print("👋 Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
