#!/bin/bash
# Build and deploy the container-based S3 Tables Import Lambda
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/deployment-config.env"

ECR_REPO="genomics-s3tables-import"
IMAGE_TAG="latest"
LAMBDA_NAME="genomics-vep-s3tables-s3tables-import"
FULL_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"

echo "=== Step 1: Create ECR repository ==="
aws ecr create-repository --repository-name ${ECR_REPO} --region ${AWS_REGION} 2>/dev/null || echo "Repository exists"

echo "=== Step 2: Build container image (amd64) ==="
cd "${SCRIPT_DIR}"
docker build --platform linux/amd64 --provenance=false -t ${ECR_REPO}:${IMAGE_TAG} -f Dockerfile.s3tables-import .

echo "=== Step 3: Push to ECR ==="
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
docker tag ${ECR_REPO}:${IMAGE_TAG} ${FULL_IMAGE}
docker push ${FULL_IMAGE}

echo "=== Step 4: Update Lambda to use container image ==="
# Check if Lambda exists as zip-based and needs to be recreated as container
PACKAGE_TYPE=$(aws lambda get-function --function-name ${LAMBDA_NAME} --region ${AWS_REGION} --query 'Configuration.PackageType' --output text 2>/dev/null || echo "NOT_FOUND")

if [ "${PACKAGE_TYPE}" = "Zip" ]; then
    echo "Lambda is zip-based — deleting and recreating as container image..."
    ROLE_ARN=$(aws lambda get-function --function-name ${LAMBDA_NAME} --region ${AWS_REGION} --query 'Configuration.Role' --output text)

    aws lambda delete-function --function-name ${LAMBDA_NAME} --region ${AWS_REGION}
    sleep 5

    aws lambda create-function \
        --function-name ${LAMBDA_NAME} \
        --package-type Image \
        --code ImageUri=${FULL_IMAGE} \
        --role ${ROLE_ARN} \
        --timeout 900 \
        --memory-size 10240 \
        --environment "Variables={DYNAMODB_TABLE=${DYNAMODB_TABLE},TABLE_BUCKET_ARN=${TABLE_BUCKET_ARN}}" \
        --region ${AWS_REGION}
elif [ "${PACKAGE_TYPE}" = "Image" ]; then
    echo "Updating existing container Lambda..."
    aws lambda update-function-code \
        --function-name ${LAMBDA_NAME} \
        --image-uri ${FULL_IMAGE} \
        --region ${AWS_REGION}

    echo "Waiting for code update to complete..."
    aws lambda wait function-updated-v2 --function-name ${LAMBDA_NAME} --region ${AWS_REGION}

    aws lambda update-function-configuration \
        --function-name ${LAMBDA_NAME} \
        --timeout 900 \
        --memory-size 10240 \
        --environment "Variables={DYNAMODB_TABLE=${DYNAMODB_TABLE},TABLE_BUCKET_ARN=${TABLE_BUCKET_ARN}}" \
        --region ${AWS_REGION}
else
    echo "Creating new container Lambda..."
    ROLE_ARN="${LAMBDA_ROLE_ARN}"

    aws lambda create-function \
        --function-name ${LAMBDA_NAME} \
        --package-type Image \
        --code ImageUri=${FULL_IMAGE} \
        --role ${ROLE_ARN} \
        --timeout 900 \
        --memory-size 10240 \
        --environment "Variables={DYNAMODB_TABLE=${DYNAMODB_TABLE},TABLE_BUCKET_ARN=${TABLE_BUCKET_ARN}}" \
        --region ${AWS_REGION}
fi

echo "=== Step 5: Re-add EventBridge permission ==="
aws lambda add-permission \
    --function-name ${LAMBDA_NAME} \
    --statement-id "EventBridgeInvokePermission" \
    --action "lambda:InvokeFunction" \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:rule/genomics-vep-s3tables-workflow-completion" \
    --region ${AWS_REGION} 2>/dev/null || echo "Permission exists"

echo ""
echo "=== Done ==="
echo "Lambda: ${LAMBDA_NAME}"
echo "Image:  ${FULL_IMAGE}"
echo "Memory: 10240 MB (10 GB), Timeout: 900s (15 min)"
echo ""
echo "Test with:"
echo "  aws lambda invoke --function-name ${LAMBDA_NAME} --cli-binary-format raw-in-base64-out \\"
echo "    --payload '{\"detail-type\":\"Run Status Change\",\"source\":\"aws.omics\",\"detail\":{\"runId\":\"8931837\",\"status\":\"COMPLETED\",\"runOutputUri\":\"s3://genomics-vep-output-v3-942514891246-us-west-2/output/1000G-chr22/8931837\",\"workflowId\":\"5035092\"}}' \\"
echo "    --region ${AWS_REGION} /tmp/response.json && cat /tmp/response.json"
