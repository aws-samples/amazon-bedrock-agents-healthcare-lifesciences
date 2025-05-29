#!/bin/bash

# Debug: Print current location and S3 bucket
echo "Current directory: $(pwd)"
echo "S3 Bucket: ${S3_BUCKET}"

# Prepare UI artifact and upload to S3
if [ -d "ui" ]; then
  echo "Preparing React UI artifact..."
  cd ui || exit
  zip -r ui_artifact.zip . -x "node_modules/*" 
  echo "Uploading React UI artifact to S3..."
  aws s3 cp "ui_artifact.zip" "s3://${S3_BUCKET}/ui/ui_artifact.zip"
  echo "React UI artifact uploaded to S3, deleting local copy"
  rm "ui_artifact.zip"
  cd ..
fi

# Process react app docker build template
echo "Processing react app docker build template..."
if [ -d "ui" ] && [ -f "ui/cloudformation/docker_build_pipeline.yml" ]; then
  echo "Copying react app docker build template"
  aws s3 cp "ui/cloudformation/docker_build_pipeline.yml" "s3://${S3_BUCKET}/ui/docker_build_pipeline.yml"
fi

# Process react app ECS service build template
echo "Processing react app ECS service build template..."
if [ -d "ui" ] && [ -f "ui/cloudformation/ecs.yml" ]; then
  echo "Copying react app ECS build template"
  aws s3 cp "ui/cloudformation/ecs.yml" "s3://${S3_BUCKET}/ui/ecs.yml"
fi


echo "All UI artifacts and templates packaged and uploaded to S3"