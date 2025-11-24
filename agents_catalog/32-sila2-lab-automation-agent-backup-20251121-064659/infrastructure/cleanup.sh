#!/bin/bash
set -e

echo "🧹 Cleaning up SiLA2 Lab Automation Agent resources"

# Delete AgentCore runtime if exists
echo "🔄 Checking for AgentCore runtime..."
if source .venv/bin/activate && agentcore status >/dev/null 2>&1; then
  echo "🗑️ Destroying AgentCore runtime..."
  agentcore destroy --confirm
else
  echo "✅ No AgentCore runtime found"
fi

# Delete CloudFormation stack
echo "🗑️ Deleting CloudFormation stack..."
aws cloudformation delete-stack \
  --stack-name sila2-agent-infra \
  --region us-west-2

echo "⏳ Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name sila2-agent-infra \
  --region us-west-2 || echo "⚠️ Stack deletion completed (some resources may be retained)"

# Clean up local files
echo "🧹 Cleaning up local configuration files..."
rm -f .bedrock_agentcore.yaml
rm -f Dockerfile
rm -f .dockerignore

echo "✅ Cleanup completed successfully!"
echo "💡 To redeploy: bash deploy-simple.sh"