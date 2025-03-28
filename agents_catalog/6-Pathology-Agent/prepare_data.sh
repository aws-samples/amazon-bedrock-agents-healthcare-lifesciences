#!/bin/bash

# Check if AWS profile was provided
if [ $# -lt 1 ]; then
    echo "Error: No AWS profile provided."
    echo "Usage: $0 <aws-profile> [bucket-name]"
    exit 1
fi

# Set AWS profile
AWS_PROFILE=$1
echo "Using AWS Profile: $AWS_PROFILE"

# Check if a bucket name was provided
if [ $# -eq 2 ]; then
    TARGET_BUCKET=$2
    echo "Using provided bucket name: $TARGET_BUCKET"
else
    # Get the AWS account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile "$AWS_PROFILE")

    if [ -z "$ACCOUNT_ID" ]; then
        echo "Error: Could not retrieve AWS account ID. Make sure you're authenticated with AWS CLI."
        exit 1
    fi
s3://tcga-2-open/6372f4a0-b94f-4148-8e05-ef87878678ff/TCGA-3L-AA1B.09A86147-EB23-489F-9849-9FDC91AC44A1.PDF
    # Set the target bucket name
    TARGET_BUCKET="pathology-agents-${ACCOUNT_ID}"
    echo "No bucket name provided. Using default: $TARGET_BUCKET"
fi

echo "Using bucket: $TARGET_BUCKET"

# Check if the bucket exists
if aws s3 ls "s3://$TARGET_BUCKET" --profile "$AWS_PROFILE" 2>&1 | grep -q 'NoSuchBucket'
then
    echo "Bucket does not exist. Creating bucket $TARGET_BUCKET"
    
    # Create the bucket
    # Note: By default, this creates the bucket in the default region configured in your AWS CLI
    aws s3 mb "s3://$TARGET_BUCKET" --profile "$AWS_PROFILE" 
    
    # Check if bucket creation was successful
    if [ $? -eq 0 ]
    then
        echo "Bucket created successfully"
    else
        echo "Failed to create bucket"
        exit 1
    fi
else
    echo "Bucket $TARGET_BUCKET already exists"
fi

# Array of file IDs to download from TCGA
PATHOLOGY_REPORST=(
    '6372f4a0-b94f-4148-8e05-ef87878678ff'
    'd7061d74-05b5-43a5-a9ac-a37bb688dbf2'
    '214eb83c-3dc8-414b-9b20-0ee4adf4412b'
    '473411dc-c722-42ca-beec-d8645f7a4acd'
    'b46452a0-d1c5-4d00-960e-0320b4c72122'
)

WSI_SLIDES=(
    'ed5f8c30-29e3-4144-948b-b8658564f2d6'
    '263abaf6-c5a1-4215-8dd5-a8b2a7bfd745'
    '68f65912-47da-44b1-8f4c-a6107428fba6'
    'dffdc56e-f1f5-4a1b-a16b-561462b3b740'
    '04d586ad-4f74-453f-a9c6-f8bd134ae11c'
    '2680fe2f-eef9-404e-a6a3-cdec178460a8'
    '43d122bb-54c5-42f2-9f1e-4fbc108f4c4a'
)

# Iterate through the files
# for file in "${PATHOLOGY_REPORST[@]}"; do
#     echo "Copying report file: $file"
#     aws s3 cp "s3://tcga-2-open/$file" "s3://$TARGET_BUCKET/REPORTS" --recursive --profile "$AWS_PROFILE"
# done

# for file in "${WSI_SLIDES[@]}"; do
#     echo "Copying WSI file: $file"
#     aws s3 cp "s3://tcga-2-open/$file" "s3://$TARGET_BUCKET/WSI" --recursive --profile "$AWS_PROFILE"
# done

# echo "All files have been copied to $TARGET_BUCKET"


## Copy code artifacts
aws s3 cp FeatureExtractionContainer s3://$TARGET_BUCKET/docker/feature-extraction --recursive --profile "$AWS_PROFILE"
aws s3 cp MSIClassificationContainer s3://$TARGET_BUCKET/docker/msi-classification --recursive --profile "$AWS_PROFILE"
cd LambdaDocumentParsing && zip lambda_code.zip lambda_function.py && aws s3 cp lambda_code.zip s3://$TARGET_BUCKET/lambda_code.zip --profile "$AWS_PROFILE"