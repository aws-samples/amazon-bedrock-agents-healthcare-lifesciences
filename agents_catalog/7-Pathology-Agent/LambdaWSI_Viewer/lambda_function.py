import openslide
from PIL import Image
import boto3
import os
import tempfile
from botocore.exceptions import ClientError
from datetime import datetime
import pytz
from urllib.parse import urlparse

def generate_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL for the S3 object"""
    s3_client = boto3.client('s3')
    try:
        url = s3_client.generate_presigned_url('get_object',
                                             Params={'Bucket': bucket_name,
                                                    'Key': object_name},
                                             ExpiresIn=expiration)
    except ClientError as e:
        print(e)
        return None
    return url

def download_from_s3(s3_uri, local_path='/tmp'):
    # Parse the S3 URI
    parsed_uri = urlparse(s3_uri)
    
    # Extract bucket name and object key
    bucket_name = parsed_uri.netloc
    object_key = parsed_uri.path.lstrip('/')
    
    # Create the local file path
    local_file_path = os.path.join(local_path, os.path.basename(object_key))
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print(f"Downloading {object_key} from bucket {bucket_name} to {local_file_path}")
    # Download the file
    s3_client.download_file(bucket_name, object_key, local_file_path)
    
    return local_file_path

def process_wsi(wsi_path, downsample_factor=32):
    """Process WSI image and return the downsampled version"""
    local_wsi_path = download_from_s3(wsi_path)
    slide = openslide.OpenSlide(local_wsi_path)
    width, height = slide.dimensions
    
    new_width = width // downsample_factor
    new_height = height // downsample_factor
    
    downsampled_image = slide.get_thumbnail((new_width, new_height))
    slide.close()
    
    return downsampled_image

def lambda_handler(event, context):
    """
    Lambda function handler
    Expected event format:
    {
        "wsi_path": "path/to/wsi/image.svs"
    }
    """

    # Get the WSI path from the event
    wsi_path = event['wsi_path']
    
    # Get the bucket name from environment variables
    bucket_name = os.environ['BUCKET_NAME']
    
    # Generate output filename
    output_filename = 'PNG/'+os.path.splitext(os.path.basename(wsi_path))[0] + "_downsampled.png"
    
    # Create a temporary directory to store files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_output_path = os.path.join(temp_dir, output_filename)
        
        # Process the WSI image
        downsampled_image = process_wsi(wsi_path)
        
        # Save the downsampled image temporarily
        downsampled_image.save(temp_output_path, "PNG")
        
        # Upload the file to S3
        s3_client = boto3.client('s3')
        s3_client.upload_file(temp_output_path, bucket_name, output_filename)
        print(f"File {output_filename} uploaded !")
        
        # Generate a presigned URL
        presigned_url = generate_presigned_url(bucket_name, output_filename)
        print(f"Presigned URL: {presigned_url}")
        return {
            'statusCode': 200,
            'body': {
                'message': 'Image processed successfully',
                'presigned_url': presigned_url
            }
        }
            
    # except Exception as e:
    #     return {
    #         'statusCode': 500,
    #         'body': {
    #             'message': f'Error processing image: {str(e)}'
    #         }
    #     }

def get_nyc_timestamp():
    """Get current timestamp in NYC timezone"""
    nyc_tz = pytz.timezone('America/New_York')
    nyc_time = datetime.now(nyc_tz)
    return nyc_time.strftime("%Y-%m-%d %H:%M:%S %Z")

if __name__ == "__main__":
    # Example usage
    event = {
    "wsi_path": "s3://pathology-agents-048051882663/WSI/TCGA-3L-AA1B-01Z-00-DX1.8923A151-A690-40B7-9E5A-FCBEDFC2394F.svs"
    }
    print(f"Received event: {event} at datetime NYC zone: {get_nyc_timestamp()}")
    sts = boto3.client("sts")
    context = {}
    result = lambda_handler(event, context)
    print(result)
