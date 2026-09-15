#!/usr/bin/env python3
"""
Test script for runtime model updates using Strands SDK update_config
Tests with 3 different models:
- anthropic.claude-haiku-4-5-20251001-v1:0
- anthropic.claude-sonnet-4-5-20250929-v1:0  
- qwen.qwen3-coder-30b-a3b-v1:0
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'agent'))

from agent.agent_config.agent import agent_task, update_agent_model

# Test models
TEST_MODELS = [
    "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0", 
    "qwen.qwen3-coder-480b-a35b-v1:0"
]

async def test_model_updates():
    """Test runtime model updates with different models"""
    
    # Initialize agent with first query
    print("🚀 Initializing agent...")
    session_id = "test-session-001"
    actor_id = "test-user"
    
    # First interaction to create agent
    print("\n📝 Initial query with default model...")
    async for response in agent_task(
        "What is the role of p53 in cancer?", 
        session_id, 
        actor_id, 
        use_semantic_search=False
    ):
        if response.strip():
            print(response, end="", flush=True)
    
    print("\n\n" + "="*60)
    
    # Test each model
    for i, model_id in enumerate(TEST_MODELS, 1):
        print(f"\n🔄 Test {i}: Updating to {model_id}")
        
        # Update model
        success = update_agent_model(model_id)
        if success:
            print(f"✅ Successfully updated to {model_id}")
        else:
            print(f"❌ Failed to update to {model_id}")
            continue
            
        # Test with updated model
        test_query = f"Explain DNA repair mechanisms (Model test {i})"
        print(f"\n📝 Testing query: {test_query}")
        
        async for response in agent_task(
            test_query,
            session_id,
            actor_id,
            use_semantic_search=False
        ):
            if response.strip():
                print(response, end="", flush=True)
        
        print(f"\n\n{'='*60}")

async def test_model_config_parameters():
    """Test update_config with additional parameters"""
    
    print("\n🧪 Testing model config with additional parameters...")
    
    # Test with temperature and max_tokens
    success = update_agent_model(
        "anthropic.claude-haiku-4-5-20251001-v1:0",
        temperature=0.7,
        max_tokens=1000
    )
    
    if success:
        print("✅ Updated model with temperature=0.7, max_tokens=1000")
        
        # Test query
        async for response in agent_task(
            "Briefly explain CRISPR gene editing",
            "test-session-002", 
            "test-user",
            use_semantic_search=False
        ):
            if response.strip():
                print(response, end="", flush=True)
    else:
        print("❌ Failed to update model with parameters")

if __name__ == "__main__":
    print("🧬 Research Agent Model Update Test")
    print("Testing runtime model switching with Strands SDK")
    
    try:
        asyncio.run(test_model_updates())
        asyncio.run(test_model_config_parameters())
        print("\n\n✅ All tests completed!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
