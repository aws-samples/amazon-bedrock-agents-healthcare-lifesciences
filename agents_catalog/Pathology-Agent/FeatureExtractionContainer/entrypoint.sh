#!/bin/bash
echo "starting Feature extraction script in: " && \
    echo | pwd &&\
    echo "using FILE_NAME:" && echo ${FILE_NAME}
    
bucket_uri=$(echo $FILE_NAME | awk -F/ '{print $1"//"$3}')

echo "=== Checking GPU Status ==="
nvidia-smi
echo "=== GPU Check Complete ==="

mkdir -p /data/input
aws s3 cp ${FILE_NAME} /data/input/${FILE_NAME}
echo "Downloaded slide from S3, starting inference" 
python run_single_slide.py --slide_path /data/input/${FILE_NAME} \
    --job_dir "/data/output" \
    --patch_encoder hoptimus0 \
    --mag 20 \
    --patch_size 256

echo "inference done"
ls /data/output    
aws s3 cp --recursive /data/output/ $bucket_uri/FEATURES/${FILE_NAME%.*}/ --exclude "*" --include "*.h5" --no-prefix
echo "copied done"