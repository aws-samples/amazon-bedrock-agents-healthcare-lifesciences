#!/bin/bash

# Verification script to check for remaining placeholders
# Run this script before deploying to ensure all placeholders have been replaced

echo "🔍 Checking for remaining placeholders..."
echo "================================================"

# Define placeholder patterns to check
PLACEHOLDERS=(
    "<YOUR_ACCOUNT_ID>"
    "<YOUR_REGION>"
    "<YOUR_KMS_KEY_ID>"
    "YOUR_S3_BUCKET"
    "YOUR_PREFIX"
    "YOUR_VARIANT_STORE_NAME"
    "YOUR_REF_STORE_ID"
    "YOUR_REFERENCE_ID"
    "YOUR_AWS_PROFILE"
)

# Files to check
FILE_PATTERNS=("*.py" "*.ipynb" "*.md")

FOUND_PLACEHOLDERS=false

for placeholder in "${PLACEHOLDERS[@]}"; do
    echo -n "Checking for $placeholder... "
    
    # Search for the placeholder in relevant files
    MATCHES=$(find . -type f \( -name "*.py" -o -name "*.ipynb" -o -name "*.md" \) ! -name "CONFIGURATION_PLACEHOLDERS.md" ! -name "verify_placeholders.sh" -exec grep -l "$placeholder" {} \; 2>/dev/null)
    
    if [ -n "$MATCHES" ]; then
        echo "❌ FOUND"
        echo "   Files containing this placeholder:"
        echo "$MATCHES" | sed 's/^/     /'
        FOUND_PLACEHOLDERS=true
    else
        echo "✅ OK"
    fi
done

echo ""
echo "================================================"

if [ "$FOUND_PLACEHOLDERS" = true ]; then
    echo "❌ VERIFICATION FAILED"
    echo ""
    echo "Some placeholders still need to be replaced."
    echo "Please update the files listed above before deploying."
    echo ""
    echo "Refer to CONFIGURATION_PLACEHOLDERS.md for guidance."
    exit 1
else
    echo "✅ VERIFICATION PASSED"
    echo ""
    echo "All required placeholders have been replaced."
    echo "You can proceed with deployment."
    exit 0
fi
