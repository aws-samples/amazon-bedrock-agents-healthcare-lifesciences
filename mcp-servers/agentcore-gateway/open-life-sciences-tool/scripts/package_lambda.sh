#!/bin/bash
set -e
set -o pipefail

# Standalone Lambda packaging script for Open Life Sciences MCP Server
#
# This script creates a Lambda deployment package (ZIP) with optional module selection.
# It outputs a ZIP file with a hash-based name for cache-busting.
#
# Usage:
#   ./package_lambda.sh [OPTIONS]
#
# Options:
#   -o, --output DIR     Output directory for ZIP file (default: ../database-lambda)
#   -m, --modules LIST   Comma-separated list of modules to include (default: all)
#   -h, --help          Show this help message
#
# Examples:
#   # Package all modules
#   ./package_lambda.sh
#
#   # Package only genomics and proteomics modules
#   ./package_lambda.sh --modules "life_sciences_genomics,life_sciences_proteomics"
#
#   # Package to custom output directory
#   ./package_lambda.sh --output /tmp/lambda-build

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATABASE_LAMBDA_DIR="$PROJECT_ROOT/database-lambda"

# Default configuration
OUTPUT_DIR="$DATABASE_LAMBDA_DIR"
SELECTED_MODULES=""

# Available modules (for validation and --help)
AVAILABLE_MODULES=(
    "life_sciences_genomics"
    "life_sciences_proteomics"
    "life_sciences_structural"
    "life_sciences_cheminformatics"
    "life_sciences_pathways"
    "life_sciences_ontologies"
    "life_sciences_clinical"
    "life_sciences_agriculture"
    "life_sciences_aiml"
    "life_sciences_biobanking"
    "life_sciences_cellbiology"
    "life_sciences_cloud"
    "life_sciences_datastandards"
    "life_sciences_ecology"
    "life_sciences_epigenomics"
    "life_sciences_healthcare"
    "life_sciences_imaging"
    "life_sciences_immunology"
    "life_sciences_metabolomics"
    "life_sciences_microbiology"
    "life_sciences_model_organisms"
    "life_sciences_molbio"
    "life_sciences_neuroscience"
    "life_sciences_pipelines"
)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

show_help() {
    cat << EOF
Standalone Lambda packaging script for Open Life Sciences MCP Server

Usage: $0 [OPTIONS]

Options:
  -o, --output DIR     Output directory for ZIP file (default: ../database-lambda)
  -m, --modules LIST   Comma-separated list of modules to include (default: all)
  -h, --help          Show this help message

Available modules:
EOF
    for module in "${AVAILABLE_MODULES[@]}"; do
        echo "  - $module"
    done
    cat << EOF

Examples:
  # Package all modules
  $0

  # Package only genomics and proteomics modules
  $0 --modules "life_sciences_genomics,life_sciences_proteomics"

  # Package to custom output directory
  $0 --output /tmp/lambda-build

EOF
}

validate_modules() {
    local module_list="$1"
    IFS=',' read -ra MODULES <<< "$module_list"
    
    for module in "${MODULES[@]}"; do
        module=$(echo "$module" | xargs)  # Trim whitespace
        if [[ ! " ${AVAILABLE_MODULES[@]} " =~ " ${module} " ]]; then
            echo "❌ Error: Unknown module '$module'"
            echo "Available modules:"
            for m in "${AVAILABLE_MODULES[@]}"; do
                echo "  - $m"
            done
            exit 1
        fi
    done
}

# ---------------------------------------------------------------------------
# Parse Arguments
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -m|--modules)
            SELECTED_MODULES="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "❌ Error: Unknown option $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate selected modules
if [[ -n "$SELECTED_MODULES" ]]; then
    validate_modules "$SELECTED_MODULES"
fi

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

echo "========================================"
echo "Lambda Packaging"
echo "========================================"
echo "Source:  $DATABASE_LAMBDA_DIR"
echo "Output:  $OUTPUT_DIR"
if [[ -n "$SELECTED_MODULES" ]]; then
    echo "Modules: $SELECTED_MODULES"
else
    echo "Modules: ALL (default)"
fi
echo "========================================"

# ---------------------------------------------------------------------------
# Package Lambda Code
# ---------------------------------------------------------------------------

echo ""
echo "📦 Packaging Lambda deployment package..."

cd "$DATABASE_LAMBDA_DIR"

# Create a clean build directory
BUILD_DIR="build"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy Lambda function code
echo "  Copying lambda_function.py..."
cp lambda_function.py "$BUILD_DIR/"

# If specific modules are selected, modify ENABLED_MODULES in lambda_function.py
if [[ -n "$SELECTED_MODULES" ]]; then
    echo "  Configuring selective module deployment..."
    
    # Convert comma-separated list to Python list format
    IFS=',' read -ra MODULES <<< "$SELECTED_MODULES"
    PYTHON_LIST=""
    for module in "${MODULES[@]}"; do
        module=$(echo "$module" | xargs)  # Trim whitespace
        if [[ -n "$PYTHON_LIST" ]]; then
            PYTHON_LIST="$PYTHON_LIST,\n        '$module'"
        else
            PYTHON_LIST="        '$module'"
        fi
    done
    
    # Replace ENABLED_MODULES in lambda_function.py
    # Find the line with ENABLED_MODULES = [ and replace until the closing ]
    python3 << EOF
import re

with open('$BUILD_DIR/lambda_function.py', 'r') as f:
    content = f.read()

# Find and replace ENABLED_MODULES list
pattern = r'ENABLED_MODULES\s*=\s*\[.*?\]'
replacement = f"""ENABLED_MODULES = [
$PYTHON_LIST
    ]"""

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('$BUILD_DIR/lambda_function.py', 'w') as f:
    f.write(content)

print("  ✓ Updated ENABLED_MODULES configuration")
EOF
fi

# Install dependencies in the build directory
if [ -f requirements.txt ]; then
    echo "  Installing dependencies..."
    pip install -r requirements.txt -t "$BUILD_DIR" --quiet --upgrade
else
    echo "⚠️  Warning: requirements.txt not found"
fi

# Create ZIP archive
if [[ -n "$SELECTED_MODULES" ]]; then
    # Use module list in filename
    MODULE_SUFFIX=$(echo "$SELECTED_MODULES" | tr ',' '-' | sed 's/life_sciences_//g')
    ZIP_FILE="database-function-${MODULE_SUFFIX}.zip"
else
    ZIP_FILE="database-function.zip"
fi

cd "$BUILD_DIR"
echo "  Creating ZIP archive..."
zip -r "../$ZIP_FILE" . -q
cd ..

# Move ZIP to output directory if different from current directory
if [[ "$OUTPUT_DIR" != "$DATABASE_LAMBDA_DIR" ]]; then
    mv "$ZIP_FILE" "$OUTPUT_DIR/"
fi

# Clean up build directory
rm -rf "$BUILD_DIR"

# ---------------------------------------------------------------------------
# Generate Hash and Display Results
# ---------------------------------------------------------------------------

cd "$OUTPUT_DIR"

# Generate SHA-256 hash for cache busting
HASH=$(shasum -a 256 "$ZIP_FILE" | cut -d' ' -f1 | cut -c1-8)
HASH_FILENAME="${ZIP_FILE%.zip}-${HASH}.zip"

# Create copy with hash-based name
cp "$ZIP_FILE" "$HASH_FILENAME"

# Get file size
FILE_SIZE=$(du -h "$ZIP_FILE" | cut -f1)

echo "✅ Lambda package created successfully!"
echo ""
echo "========================================"
echo "Package Details"
echo "========================================"
echo "Original:  $ZIP_FILE"
echo "Hashed:    $HASH_FILENAME"
echo "Size:      $FILE_SIZE"
echo "SHA-256:   $HASH (first 8 chars)"
echo "Location:  $OUTPUT_DIR"
echo "========================================"

if [[ -n "$SELECTED_MODULES" ]]; then
    echo ""
    echo "📋 Included modules:"
    IFS=',' read -ra MODULES <<< "$SELECTED_MODULES"
    for module in "${MODULES[@]}"; do
        module=$(echo "$module" | xargs)
        echo "  ✓ $module"
    done
fi

echo ""
echo "💡 Usage examples:"
echo ""
echo "  # Upload to S3 for deployment:"
echo "  aws s3 cp $HASH_FILENAME s3://YOUR-BUCKET/lambda-code/$HASH_FILENAME"
echo ""
echo "  # Use in CloudFormation deployment:"
echo "  aws cloudformation deploy --stack-name my-stack \\"
echo "    --template-file cfn/infrastructure.yaml \\"
echo "    --parameter-overrides \\"
echo "      LambdaS3Bucket=YOUR-BUCKET \\"
echo "      DatabaseLambdaS3Key=lambda-code/$HASH_FILENAME"
echo ""
