#!/bin/bash

# Get the runtime IAM role
RUNTIME_ROLE=$(aws ssm get-parameter --name /app/researchapp/agentcore/runtime_iam_role --region us-west-2 --query "Parameter.Value" --output text)

echo "Using runtime role: $RUNTIME_ROLE"

# Run agentcore configure with automated inputs
agentcore configure \
  --entrypoint agent/main.py \
  -er "$RUNTIME_ROLE" \
  --name researchappAgent \
  --requirements agent/requirements.txt \
  --no-oauth

echo "Configuration complete!"
