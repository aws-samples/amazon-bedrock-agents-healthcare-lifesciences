#!/bin/bash

# Upload knowledge base data to S3
BUCKET_NAME="dmta-orchestration-agent-kb-us-west-2-590183741681"

echo "📚 Uploading Knowledge Base data to S3..."

# Upload sample projects
aws s3 cp knowledge-base/project-001.md s3://$BUCKET_NAME/projects/project-001.md
aws s3 cp knowledge-base/project-015.md s3://$BUCKET_NAME/projects/project-015.md
aws s3 cp knowledge-base/project-087.md s3://$BUCKET_NAME/projects/project-087.md
aws s3 cp knowledge-base/sample-projects.json s3://$BUCKET_NAME/projects/sample-projects.json

echo "✅ Knowledge Base data uploaded successfully!"
echo "📋 Files uploaded:"
aws s3 ls s3://$BUCKET_NAME/projects/ --recursive