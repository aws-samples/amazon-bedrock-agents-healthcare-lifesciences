#!/bin/bash
source ~/.bashrc

echo "Starting script execution..."
echo "--------------------------------------"

echo "Loading bash configuration..."
source ~/.bashrc
echo "Bash configuration loaded"
echo "--------------------------------------"

echo "Changing to evaluation framework directory..."
cd amazon-bedrock-agent-evaluation-framework
echo "Directory changed successfully"
echo "--------------------------------------"

echo "Installing requirements..."
pip3 install -r requirements.txt
echo "Requirements installation complete"
echo "--------------------------------------"

echo "Running evaluation ..."
python3 driver.py
echo "--------------------------------------"
echo "Script execution completed"
