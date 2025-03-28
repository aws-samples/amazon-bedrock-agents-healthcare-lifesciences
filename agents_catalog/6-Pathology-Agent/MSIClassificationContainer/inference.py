import json
import logging
import os
import argparse
import tempfile
import torch
import torch.nn as nn
import numpy as np
import boto3
import h5py
from pathlib import Path
from urllib.parse import urlparse
from trident.slide_encoder_models import ABMILSlideEncoder
from trident import OpenSlideWSI
from trident.segmentation_models import segmentation_model_factory
from trident.patch_encoder_models import encoder_factory
# Import your model from the separate file
from model import MulticlassClassificationModel

s3 = boto3.client('s3')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

BUCKET_NAME = os.environ.get('BUCKET_NAME')

# Helper function
def find_h5_object(bucket, prefix):
    """Search for an object in S3 with given prefix"""
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if 'Contents' not in response or not response['Contents']:
        return None
    return response['Contents'][0]['Key']

def parse_s3_uri(uri):
    """Parse S3 URI into bucket and key"""
    parsed = urlparse(uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    return bucket, key

# MAIN 

# Parse the S3 URI
parser = argparse.ArgumentParser(description="Run inference on a slide")
parser.add_argument("--slide_path", type=str, required=True, default="TCGA-3L-AA1B-01Z-00-DX1.8923A151-A690-40B7-9E5A-FCBEDFC2394F.h5", help="Path to the slide file")
args = parser.parse_args()
_, s3_key = parse_s3_uri(args.slide_path)
slide_name = os.path.basename(s3_key)  # Get just the filename
slide_name_without_ext = os.path.splitext(slide_name)[0]  # Remove .h5 extension
print(f"Processing slide: {slide_name}")

# Step 1 - Load Model
logger.info("Initializing the model ! Loading from disk")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_path = "/data/model/model.pth"
assert os.path.exists(model_path)
model = MulticlassClassificationModel().to(device)
state_dict = torch.load(model_path, map_location=device, weights_only=True)
model.load_state_dict(state_dict)
model.eval()
logging.info(f"Model loaded successfully from {model_path}")

# Step 2 - Download features from S3
s3.download_file(BUCKET_NAME, s3_key, "/data/input/features.h5")

# Step 3 - Run inference
with h5py.File("/data/input/features.h5", 'r') as f:
    features = f['features'][:]
features = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(device)
if features.dim() == 2:
    features = features.unsqueeze(0)

with torch.no_grad():
    logits = model({'features': features})
    logits = logits.squeeze(0).cpu().detach().numpy()


logger.info("Postprocessing inference output")
response = {
    "status": "COMPLETED",
    "logits": logits.tolist(),
}

print(json.dumps(response))

# Write prediction to file
prediction_file = f"/tmp/{slide_name_without_ext}_prediction.txt"
with open(prediction_file, 'w') as f:
    json.dump(response, f)

# Upload prediction file to S3
s3_prediction_path = f"PREDICTIONS/{slide_name_without_ext}.txt"
s3.upload_file(prediction_file, BUCKET_NAME, s3_prediction_path)
logger.info(f"Prediction uploaded to S3: {s3_prediction_path}")