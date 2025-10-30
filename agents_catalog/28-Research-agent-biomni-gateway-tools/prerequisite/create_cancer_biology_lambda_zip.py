#!/usr/bin/env python3
"""
Zip script for Cancer Biology Gateway Lambda function.

This script creates two deployment packages:
1. Lambda Layer with Python dependencies
2. Lambda Function with code only

This approach keeps both packages under AWS Lambda size limits.
"""

import os
import sys
import subprocess
import tempfile
import shutil
import zipfile
from pathlib import Path


def create_lambda_layer():
    """Create a Lambda Layer with Python dependencies."""
    
    layer_zip_path = "cancer-biology-lambda-layer.zip"
    
    # Create temporary directory for building the layer
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Lambda layers must have dependencies in python/ subdirectory
        python_dir = temp_path / "python"
        python_dir.mkdir()
        
        print("📦 Installing Python dependencies for Lambda Layer...")
        dependencies = [
            "pandas",
            "numpy",
            "scipy",
            "networkx",
            "gseapy",
            "FlowCytometryTools",
            "requests"
        ]
        
        for package in dependencies:
            try:
                print(f"  Installing {package}...")
                # nosemgrep follows best practice
                subprocess.run([
                    sys.executable, "-m", "pip", "install",
                    package,
                    "-t", str(python_dir),
                    "--upgrade",
                    "--no-cache-dir"
                ], check=True, capture_output=True, text=True)
                print(f"  ✅ Installed: {package}")
            except subprocess.CalledProcessError as e:
                print(f"  ⚠️  Failed to install {package}: {e.stderr}")
                # Continue with other packages
        
        print("\n🧹 Optimizing package size (removing unnecessary files)...")
        
        # Remove unnecessary files to reduce size
        patterns_to_remove = [
            "**/__pycache__",
            "**/*.pyc",
            "**/*.pyo",
            "**/*.dist-info",
            "**/*.egg-info",
            "**/tests",
            "**/test",
            "**/testing",
            "**/*.so.dSYM",
            "**/examples",
            "**/docs",
            "**/doc",
            "**/*.md",
            "**/*.txt",
            "**/*.rst",
            "**/LICENSE*",
            "**/NOTICE*",
            "**/.git*",
        ]
        
        removed_count = 0
        removed_size = 0
        
        for pattern in patterns_to_remove:
            for path in python_dir.glob(pattern):
                if path.is_file():
                    size = path.stat().st_size
                    path.unlink()
                    removed_count += 1
                    removed_size += size
                elif path.is_dir():
                    size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                    shutil.rmtree(path)
                    removed_count += 1
                    removed_size += size
        
        print(f"  Removed {removed_count} items, freed {removed_size / (1024 * 1024):.2f} MB")
        
        print("\n📦 Creating Lambda Layer ZIP archive...")
        
        # Create ZIP file from temp directory
        with zipfile.ZipFile(layer_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_path.rglob("*"):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(temp_path))
                    zipf.write(str(file_path), arcname)
        
        # Get file sizes
        compressed_size = os.path.getsize(layer_zip_path) / (1024 * 1024)
        
        # Calculate uncompressed size
        uncompressed_size = 0
        with zipfile.ZipFile(layer_zip_path, 'r') as zipf:
            uncompressed_size = sum(info.file_size for info in zipf.filelist) / (1024 * 1024)
        
        print(f"✅ Created: {layer_zip_path}")
        print(f"   Compressed: {compressed_size:.2f} MB")
        print(f"   Uncompressed: {uncompressed_size:.2f} MB")
        
        if uncompressed_size > 250:
            print(f"   ⚠️  WARNING: Uncompressed size exceeds 250 MB Lambda limit!")
        
    return layer_zip_path


def create_lambda_function():
    """Create a Lambda Function package with code only."""
    
    function_zip_path = "cancer-biology-lambda-function.zip"
    
    # Create temporary directory for building the package
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        print("\n📁 Copying Lambda function files...")
        
        # Copy the Lambda handler function
        handler_source = Path("lambda/python/cancer_biology_lambda_function.py")
        if not handler_source.exists():
            raise FileNotFoundError(f"Handler file not found: {handler_source}")
        shutil.copy(handler_source, temp_path / "cancer_biology_lambda_function.py")
        print(f"✅ Copied: {handler_source.name}")
        
        # Copy the cancer_biology.py implementation
        cancer_bio_source = Path("cancer_biology.py")
        if not cancer_bio_source.exists():
            raise FileNotFoundError(f"Cancer biology module not found: {cancer_bio_source}")
        shutil.copy(cancer_bio_source, temp_path / "cancer_biology.py")
        print(f"✅ Copied: {cancer_bio_source.name}")
        
        print("\n📦 Creating Lambda Function ZIP archive...")
        
        # Create ZIP file from temp directory
        with zipfile.ZipFile(function_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_path.rglob("*"):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(temp_path))
                    zipf.write(str(file_path), arcname)
        
        file_size = os.path.getsize(function_zip_path) / (1024 * 1024)
        print(f"✅ Created: {function_zip_path} ({file_size:.2f} MB)")
    
    return function_zip_path


def main():
    """Main function to create the Lambda deployment packages."""
    
    # Change to the prerequisite directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("=" * 80)
    print("Cancer Biology Lambda Package Creator")
    print("=" * 80)
    print()
    
    try:
        # Create Lambda Layer with dependencies
        layer_zip_path = create_lambda_layer()
        
        # Create Lambda Function with code only
        function_zip_path = create_lambda_function()
        
        print()
        print("=" * 80)
        print("✅ Package creation completed successfully!")
        print("=" * 80)
        print()
        print("Created packages:")
        print(f"  1. Lambda Layer (dependencies): {layer_zip_path}")
        print(f"  2. Lambda Function (code): {function_zip_path}")
        print()
        print("Next steps:")
        print("1. Upload both ZIP files to your S3 bucket")
        print("2. Update CloudFormation template to:")
        print("   - Create Lambda Layer from cancer-biology-lambda-layer.zip")
        print("   - Reference the layer in the Lambda function")
        print("   - Use cancer-biology-lambda-function.zip for function code")
        print("3. Deploy the CloudFormation stack")
        print("4. Create the gateway target using create_cancer_biology_target.py")
        
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ Package creation failed: {str(e)}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
