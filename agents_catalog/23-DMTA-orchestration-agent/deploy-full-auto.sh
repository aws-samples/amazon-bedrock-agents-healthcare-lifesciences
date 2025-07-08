#!/bin/bash

echo "🚀 DMTA Orchestration Agent - Full Automated Deployment"
echo "======================================================="

# Step 1: Deploy basic functions
echo "📋 Step 1: Deploying basic functions..."
./deploy-step1.sh

if [ $? -ne 0 ]; then
    echo "❌ Step 1 failed"
    exit 1
fi

echo ""
echo "⏳ Waiting 30 seconds for resources to stabilize..."
sleep 30

# Step 2: Setup Knowledge Base (automated)
echo "📋 Step 2: Setting up Knowledge Base..."
./auto-setup-kb.sh

if [ $? -ne 0 ]; then
    echo "❌ Step 2 failed"
    exit 1
fi

echo ""
echo "⏳ Waiting 60 seconds for Knowledge Base to be ready..."
sleep 60

# Step 3: Link Knowledge Base to Agent
echo "📋 Step 3: Linking Knowledge Base to Agent..."
./deploy-step3.sh

if [ $? -ne 0 ]; then
    echo "❌ Step 3 failed"
    exit 1
fi

echo ""
echo "⏳ Waiting 30 seconds for agent preparation..."
sleep 30

# Step 4: Test the complete system
echo "📋 Step 4: Testing complete system..."
python3 test_agent.py

echo ""
echo "🎉 Full deployment completed successfully!"
echo "📊 DMTA Orchestration Agent with Knowledge Base is ready!"