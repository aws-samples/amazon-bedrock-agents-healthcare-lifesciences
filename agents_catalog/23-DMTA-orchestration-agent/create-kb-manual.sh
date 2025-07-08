#!/bin/bash

echo "📚 Manual Knowledge Base Creation Guide"
echo "======================================"

BUCKET_NAME=$(cat .kb-bucket-name)

echo "1. Go to AWS Bedrock Console:"
echo "   https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/knowledge-bases"
echo ""
echo "2. Click 'Create knowledge base'"
echo ""
echo "3. Knowledge base details:"
echo "   - Name: DMTA-Knowledge-Base"
echo "   - Description: DMTA project knowledge base with historical optimization data"
echo ""
echo "4. Data source:"
echo "   - Data source name: dmta-projects"
echo "   - S3 URI: s3://$BUCKET_NAME/projects/"
echo ""
echo "5. Embeddings model:"
echo "   - Select: Amazon Titan Embeddings G1 - Text"
echo ""
echo "6. Vector database:"
echo "   - Select: Quick create a new vector store"
echo ""
echo "7. After creation, copy the Knowledge Base ID and run:"
echo "   ./deploy-step3.sh <KNOWLEDGE_BASE_ID>"
echo ""
echo "📋 S3 bucket with data: s3://$BUCKET_NAME/projects/"
echo "📄 Files uploaded:"
aws s3 ls s3://$BUCKET_NAME/projects/ --recursive