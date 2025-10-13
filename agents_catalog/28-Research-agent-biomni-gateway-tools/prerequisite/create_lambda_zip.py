#!/usr/bin/env python3
"""
Simple zip script for Database Gateway and Literature Lambda functions.

This script zips Lambda functions with all the database query tools and literature research tools
"""

import boto3
import json
import zipfile
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

def create_lambda_zip():
    """Create a deployment package for the Database Lambda function."""
    import subprocess
    import tempfile
    import shutil
    
    zip_path = "database-gateway-function.zip"
    
    # Create temporary directory for building the package
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Copy function files
        shutil.copy("lambda/python/lambda_function.py", temp_path / "lambda_function.py")
        shutil.copy("lambda/python/database.py", temp_path / "database.py")
        
        # Copy schema files if they exist
        schema_dir = Path("lambda/python/schema_db")
        if schema_dir.exists():
            shutil.copytree(schema_dir, temp_path / "schema_db")
        
        # Install dependencies from requirements.txt
        requirements_file = Path("lambda/python/requirements.txt")
        if requirements_file.exists():
            print("📦 Installing Python dependencies...")
            
            # Install dependencies with proper conflict resolution
            try:
                # nosemgrep follows best practice
                subprocess.run([
                    sys.executable, "-m", "pip", "install",
                    "-r", str(requirements_file),
                    "-t", str(temp_path),
                    "--upgrade",
                    "--force-reinstall",
                    "--no-cache-dir"
                ], check=True, capture_output=True, text=True)
                print("✅ Dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Dependency installation had issues: {e.stderr}")
                print("🔄 Trying alternative installation method...")
                
                # Try installing each package individually
                with open(requirements_file, 'r') as f:
                    for line in f:
                        package = line.strip()
                        if package and not package.startswith('#'):
                            try:
                                # nosemgrep follows best practice
                                subprocess.run([
                                    sys.executable, "-m", "pip", "install",
                                    package,
                                    "-t", str(temp_path),
                                    "--upgrade",
                                    "--no-cache-dir"
                                ], check=True, capture_output=True, text=True)
                                print(f"✅ Installed: {package}")
                            except subprocess.CalledProcessError as pkg_error:
                                print(f"⚠️  Failed to install {package}: {pkg_error.stderr}")
                                # Continue with other packages
        
        # Create ZIP file from temp directory
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_path.rglob("*"):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(temp_path))
                    zipf.write(str(file_path), arcname)
    
    return zip_path

def create_literature_lambda_zip():
    """Create a deployment package for the Literature Lambda function."""
    
    zip_path = "literature-gateway-function.zip"
    
    # Create temporary directory for building the package
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Copy function files
        shutil.copy("lambda-literature/python/lambda_function.py", temp_path / "lambda_function.py")
        shutil.copy("lambda-literature/python/literature.py", temp_path / "literature.py")
        
        # Install dependencies from requirements.txt
        requirements_file = Path("lambda-literature/python/requirements.txt")
        if requirements_file.exists():
            print("📦 Installing Python dependencies for literature lambda...")
            
            # Install dependencies with proper conflict resolution
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install",
                    "-r", str(requirements_file),
                    "-t", str(temp_path),
                    "--upgrade",
                    "--force-reinstall",
                    "--no-cache-dir"
                ], check=True, capture_output=True, text=True)
                print("✅ Literature dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Literature dependency installation had issues: {e.stderr}")
                print("🔄 Trying alternative installation method...")
                
                # Try installing each package individually
                with open(requirements_file, 'r') as f:
                    for line in f:
                        package = line.strip()
                        if package and not package.startswith('#'):
                            try:
                                subprocess.run([
                                    sys.executable, "-m", "pip", "install",
                                    package,
                                    "-t", str(temp_path),
                                    "--upgrade",
                                    "--no-cache-dir"
                                ], check=True, capture_output=True, text=True)
                                print(f"✅ Installed: {package}")
                            except subprocess.CalledProcessError as pkg_error:
                                print(f"⚠️  Failed to install {package}: {pkg_error.stderr}")
                                # Continue with other packages
        
        # Create ZIP file from temp directory
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_path.rglob("*"):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(temp_path))
                    zipf.write(str(file_path), arcname)
    
    return zip_path

def main():
    """Main zip function."""
    
    # Change to the gateway directory
    os.chdir(Path(__file__).parent)
    
    try:
        # Step 1: Create database deployment package
        print("📦 Creating database lambda deployment package...")
        db_zip_path = create_lambda_zip()
        print(f"✅ Created {db_zip_path}")
        
        # Step 2: Create literature deployment package
        print("📦 Creating literature lambda deployment package...")
        lit_zip_path = create_literature_lambda_zip()
        print(f"✅ Created {lit_zip_path}")
        
    except Exception as e:
        print(f"❌ zip failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()