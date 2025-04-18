#!/bin/bash
echo "starting inference script in: " && \
    echo | pwd &&\
    echo "using FILE_NAME:" && echo ${FILE_NAME}
    
echo "=== Checking GPU Status ==="
nvidia-smi
echo "=== GPU Check Complete ==="

mkdir -p /data/input
echo "starting the classification inference script"
OUTPUT=$(python inference.py --slide_path /data/input/${FILE_NAME})

# Parse the JSON output
STATUS=$(echo $OUTPUT | jq -r .status)
LOGITS=$(echo $OUTPUT | jq -r .logits)

# Use the parsed values
echo "Inference status: $STATUS"
echo "Logits: $LOGITS"

echo "inference done"
