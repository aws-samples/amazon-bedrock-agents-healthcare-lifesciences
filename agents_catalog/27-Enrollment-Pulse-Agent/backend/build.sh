#!/bin/bash

set -e

echo "🔨 Building Enrollment Pulse Backend..."
echo "======================================"

# Clean previous build
echo "🧹 Cleaning previous build..."
rm -rf .aws-sam

# Build with container (no local venv needed)
echo "🏗️ Building SAM application with container..."
sam build --use-container

echo "✅ Build complete!"