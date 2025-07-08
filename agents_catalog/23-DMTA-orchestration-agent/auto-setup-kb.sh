#!/bin/bash

echo "🤖 Automated Knowledge Base Setup"
echo "================================="

# Create S3 bucket
BUCKET_NAME="dmta-kb-$(date +%s)-$(shuf -i 1000-9999 -n 1)"
echo "Creating S3 bucket: $BUCKET_NAME"

aws s3 mb s3://$BUCKET_NAME --region us-west-2

if [ $? -ne 0 ]; then
    echo "❌ Failed to create S3 bucket"
    exit 1
fi

# Upload knowledge base data
echo "📤 Uploading knowledge base data..."
aws s3 cp knowledge-base/project-001.md s3://$BUCKET_NAME/projects/project-001.md
aws s3 cp knowledge-base/project-015.md s3://$BUCKET_NAME/projects/project-015.md
aws s3 cp knowledge-base/project-087.md s3://$BUCKET_NAME/projects/project-087.md

echo "✅ Data uploaded successfully!"

# Create Knowledge Base
echo "🧠 Creating Knowledge Base..."
KB_NAME="DMTA-KB-$(date +%s)"

KB_RESPONSE=$(aws bedrock-agent create-knowledge-base \
    --name "$KB_NAME" \
    --description "DMTA project knowledge base with historical optimization data" \
    --role-arn "arn:aws:iam::590183741681:role/BedrockAgentRole" \
    --knowledge-base-configuration '{
        "type": "VECTOR",
        "vectorKnowledgeBaseConfiguration": {
            "embeddingModelArn": "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v1"
        }
    }' \
    --storage-configuration '{
        "type": "OPENSEARCH_SERVERLESS",
        "opensearchServerlessConfiguration": {
            "collectionArn": "arn:aws:aoss:us-west-2:590183741681:collection/dmta-collection",
            "vectorIndexName": "dmta-index",
            "fieldMapping": {
                "vectorField": "vector",
                "textField": "text", 
                "metadataField": "metadata"
            }
        }
    }' \
    --region us-west-2 2>/dev/null)

if [ $? -eq 0 ]; then
    KB_ID=$(echo $KB_RESPONSE | jq -r '.knowledgeBase.knowledgeBaseId')
    echo "✅ Knowledge Base created: $KB_ID"
    
    # Create Data Source
    echo "📊 Creating Data Source..."
    DS_RESPONSE=$(aws bedrock-agent create-data-source \
        --knowledge-base-id "$KB_ID" \
        --name "dmta-projects" \
        --description "Historical DMTA project data" \
        --data-source-configuration "{
            \"type\": \"S3\",
            \"s3Configuration\": {
                \"bucketArn\": \"arn:aws:s3:::$BUCKET_NAME\",
                \"inclusionPrefixes\": [\"projects/\"]
            }
        }" \
        --region us-west-2 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        DS_ID=$(echo $DS_RESPONSE | jq -r '.dataSource.dataSourceId')
        echo "✅ Data Source created: $DS_ID"
        
        # Start ingestion job
        echo "🔄 Starting data ingestion..."
        aws bedrock-agent start-ingestion-job \
            --knowledge-base-id "$KB_ID" \
            --data-source-id "$DS_ID" \
            --region us-west-2 >/dev/null 2>&1
        
        # Save IDs for next step
        echo "$KB_ID" > .kb-id
        echo "$BUCKET_NAME" > .kb-bucket-name
        
        echo "✅ Knowledge Base setup completed!"
        echo "📋 Knowledge Base ID: $KB_ID"
        echo "🚀 Ready for Step 3: ./deploy-step3.sh $KB_ID"
        
    else
        echo "❌ Failed to create Data Source"
        exit 1
    fi
else
    echo "❌ Failed to create Knowledge Base"
    echo "💡 This might be due to missing OpenSearch Serverless collection"
    echo "📋 Falling back to manual setup instructions..."
    
    echo ""
    echo "🔧 Manual Knowledge Base Creation:"
    echo "1. Go to AWS Bedrock Console → Knowledge bases"
    echo "2. Create knowledge base with:"
    echo "   - Name: $KB_NAME"
    echo "   - S3 Data Source: s3://$BUCKET_NAME/projects/"
    echo "   - Embedding Model: Amazon Titan Embeddings G1 - Text"
    echo "3. Note the Knowledge Base ID for next step"
    
    echo "$BUCKET_NAME" > .kb-bucket-name
fi