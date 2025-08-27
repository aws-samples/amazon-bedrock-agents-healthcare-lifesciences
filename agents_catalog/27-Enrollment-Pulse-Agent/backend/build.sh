#!/bin/bash

set -e

echo "🔨 Building Enrollment Pulse Backend..."
echo "======================================"

# Create virtual environment if it doesn't exist
if [ ! -d "../venv" ]; then
    echo "📦 Creating virtual environment..."
    cd ..
    python3 -m venv venv
    cd backend
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source ../venv/bin/activate

# Install/update requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Build with container to avoid dependency conflicts
echo "🏗️ Building SAM application..."
sam build --use-container

echo "✅ Build complete!"