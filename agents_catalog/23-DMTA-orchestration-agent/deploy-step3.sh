#!/bin/bash

echo "🔗 Step 3: Linking Knowledge Base to Agent"
echo "=========================================="

# Check if Knowledge Base ID is provided or saved
if [ -z "$1" ]; then
    if [ -f ".kb-id" ]; then
        KNOWLEDGE_BASE_ID=$(cat .kb-id)
        echo "📋 Using saved Knowledge Base ID: $KNOWLEDGE_BASE_ID"
    else
        echo "❌ Please provide Knowledge Base ID as argument"
        echo "Usage: ./deploy-step3.sh <KNOWLEDGE_BASE_ID>"
        echo "Example: ./deploy-step3.sh KB123456789"
        exit 1
    fi
else
    KNOWLEDGE_BASE_ID=$1
fi
AGENT_ID="NTV3DLL9DQ"

echo "🔧 Linking Knowledge Base $KNOWLEDGE_BASE_ID to Agent $AGENT_ID"

# Update agent with Knowledge Base (using AWS CLI)
aws bedrock-agent associate-agent-knowledge-base \
    --agent-id $AGENT_ID \
    --agent-version DRAFT \
    --knowledge-base-id $KNOWLEDGE_BASE_ID \
    --description "Historical DMTA project data for optimization guidance" \
    --knowledge-base-state ENABLED \
    --region us-west-2

if [ $? -eq 0 ]; then
    echo "✅ Knowledge Base linked successfully!"
    
    # Prepare and update agent
    echo "🔄 Preparing agent for production..."
    aws bedrock-agent prepare-agent \
        --agent-id $AGENT_ID \
        --region us-west-2
    
    echo "✅ Step 3 completed successfully!"
    echo "🎉 DMTA Orchestration Agent with Knowledge Base is ready!"
    echo ""
    echo "📋 Test the agent with:"
    echo "   python3 test_agent.py"
    
else
    echo "❌ Failed to link Knowledge Base to Agent"
    exit 1
fi