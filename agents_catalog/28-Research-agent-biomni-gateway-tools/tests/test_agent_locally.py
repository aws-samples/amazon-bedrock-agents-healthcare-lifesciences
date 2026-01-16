#!/usr/bin/env python3

import asyncio
import sys
import os
import uuid
import click

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.agent_config.access_token import get_gateway_access_token
from agent.agent_config.agent import agent_task


@click.command()
@click.option("--prompt", "-p", required=True, help="Prompt to send to the agent")
@click.option("--use-search", is_flag=True, help="Use semantic search to find relevant tools")
@click.option("--session-id", "-s", help="Session ID (generates random if not provided)")
@click.option("--actor-id", "-a", default="DEFAULT", help="Actor ID")
def main(prompt, use_search, session_id, actor_id):
    """Test the research agent locally using ResearchContext."""
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    print(f"🤖 Testing agent with prompt: {prompt}")
    print(f"🔍 Use search: {use_search}")
    print(f"🔗 Session ID: {session_id}")
    print("=" * 60)
    
    asyncio.run(test_agent_async(prompt, session_id, actor_id, use_search))

async def test_agent_async(prompt, session_id, actor_id, use_search):
    """Test agent using the same logic as main.py"""
    
    # Create task like in main.py - agent_task returns an async generator
    async for item in agent_task(prompt, session_id, actor_id, use_semantic_search=use_search):
        print(item, end="", flush=True)
    
    print("\n" + "=" * 60)
    print("✅ Response completed")

if __name__ == "__main__":
    main()
