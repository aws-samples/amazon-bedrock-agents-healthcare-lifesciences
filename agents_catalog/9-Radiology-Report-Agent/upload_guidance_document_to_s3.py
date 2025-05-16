import boto3
import os

def create_s3_bucket(bucket_name, region):
    s3_client = boto3.client('s3', region_name=region)
    location = {'LocationConstraint': region}
    s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    print(f"Bucket '{bucket_name}' created successfully in region '{region}'.")

def upload_folder_to_s3(bucket_name, folder_path):
    s3_client = boto3.client('s3')
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            s3_key = os.path.relpath(file_path, folder_path)
            s3_client.upload_file(file_path, bucket_name, s3_key)
            print(f"Uploaded {file_path} to s3://{bucket_name}/{s3_key}")

            
if __name__ == "__main__":
    bucket_name = 'radiology-report-agent-guidance-documents'
    region = 'us-west-2'

   # check if the bucket exists if not create it
    s3_client = boto3.client('s3', region_name=region)
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' already exists.")
    except Exception as e:
        create_s3_bucket(bucket_name, region)

    # Upload the guidance document
    folder_path = './ACRdocs'
    upload_folder_to_s3(bucket_name, folder_path)
    