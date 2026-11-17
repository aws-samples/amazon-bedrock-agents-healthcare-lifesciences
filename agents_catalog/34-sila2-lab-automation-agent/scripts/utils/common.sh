#!/bin/bash
# Common functions

# CloudFormation operations
get_stack_output() {
  aws cloudformation describe-stacks \
    --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" \
    --output text \
    --region "${DEFAULT_REGION}"
}

# ECR operations
ecr_login() {
  aws ecr get-login-password --region "${DEFAULT_REGION}" | \
    docker login --username AWS --password-stdin \
    "${ACCOUNT_ID}.dkr.ecr.${DEFAULT_REGION}.amazonaws.com"
}

# Docker operations
build_and_push_image() {
  local dir=$1
  local repo=$2
  local original_dir=$(pwd)
  
  echo "Building image from ${dir}..."
  cd "${dir}" || exit 1
  
  docker build -t "${repo}:latest" .
  docker tag "${repo}:latest" "${ACCOUNT_ID}.dkr.ecr.${DEFAULT_REGION}.amazonaws.com/${repo}:latest"
  docker push "${ACCOUNT_ID}.dkr.ecr.${DEFAULT_REGION}.amazonaws.com/${repo}:latest"
  
  cd "${original_dir}" || exit 1
}

# Lambda operations
package_lambda() {
  local dir=$1
  local bucket=$2
  local original_dir=$(pwd)
  
  echo "Packaging Lambda from ${dir}..."
  cd "${dir}" || exit 1
  
  local zip_name=$(basename "${dir}").zip
  zip -r "/tmp/${zip_name}" . -x "*.pyc" "__pycache__/*"
  aws s3 cp "/tmp/${zip_name}" "s3://${bucket}/lambda/" --region "${DEFAULT_REGION}"
  
  cd "${original_dir}" || exit 1
}

package_custom_resource() {
  local dir=$1
  local bucket=$2
  local zip_name=$3
  local original_dir=$(pwd)
  
  echo "Packaging Custom Resource from ${dir}..."
  cd "${dir}" || exit 1
  
  zip -r "/tmp/${zip_name}" . -x "*.pyc" "__pycache__/*"
  aws s3 cp "/tmp/${zip_name}" "s3://${bucket}/lambda/" --region "${DEFAULT_REGION}"
  
  cd "${original_dir}" || exit 1
}

# Create S3 bucket, or confirm an existing one is owned by this account.
# The bucket name is predictable, so another account could create it first.
# Exits the script rather than upload code to a bucket this account does not own.
create_deployment_bucket() {
  local bucket=$1
  local head_err

  if head_err=$(aws s3api head-bucket --bucket "${bucket}" \
        --expected-bucket-owner "${ACCOUNT_ID}" --region "${DEFAULT_REGION}" 2>&1 >/dev/null); then
    echo "Bucket ${bucket} already exists and is owned by account ${ACCOUNT_ID}"
  elif echo "${head_err}" | grep -q "(404)"; then
    echo "Creating bucket ${bucket}..."
    aws s3 mb "s3://${bucket}" --region "${DEFAULT_REGION}" || exit 1
    aws s3api wait bucket-exists --bucket "${bucket}" \
      --expected-bucket-owner "${ACCOUNT_ID}" --region "${DEFAULT_REGION}" || exit 1
  else
    echo "Error: bucket ${bucket} exists but is not owned by account ${ACCOUNT_ID}," >&2
    echo "  or cannot be checked: ${head_err}" >&2
    echo "  Refusing to upload deployment artifacts to it." >&2
    exit 1
  fi
}

# Create ECR
create_ecr_if_not_exists() {
  local repo=$1
  
  if aws ecr describe-repositories --repository-names "${repo}" --region "${DEFAULT_REGION}" 2>/dev/null >/dev/null; then
    echo "✅ Repository ${repo} exists"
  else
    echo "Creating repository ${repo}..."
    aws ecr create-repository --repository-name "${repo}" --region "${DEFAULT_REGION}" >/dev/null
    echo "✅ Repository ${repo} created"
  fi
}
