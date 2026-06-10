#!/bin/bash
# Configure optional API keys for Open Life Sciences MCP Server
# Usage: ./configure_credentials.sh [APP_NAME]
#   Prompts for API keys and stores them in SSM Parameter Store as SecureString

set -e
set -o pipefail

APP_NAME=${1:-open-life-sciences-tool}
REGION=${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-west-2")}

echo "🔐 Configure API Credentials for $APP_NAME"
echo "📍 Region: $REGION"
echo ""
echo "This script configures optional API keys for external databases."
echo "All credentials are stored securely in AWS Systems Manager Parameter Store."
echo ""
echo "Press Enter to skip any credential you don't want to configure."
echo ""

# Define credentials with descriptions
declare -A CREDENTIALS=(
    ["NCBI_API_KEY"]="NCBI E-utilities API key (increases rate limits from 3 to 10 requests/second)"
    ["COSMIC_API_KEY"]="COSMIC API key (required for accessing cancer mutation data)"
    ["OMIM_API_KEY"]="OMIM API key (required for accessing genetic disorder information)"
    ["DRUGBANK_API_KEY"]="DrugBank API key (required for accessing drug-drug interaction data)"
    ["CHEMSPIDER_API_KEY"]="ChemSpider API key (required for accessing chemical structure data)"
)

# Define setup instructions
declare -A SETUP_INSTRUCTIONS=(
    ["NCBI_API_KEY"]="Register at: https://www.ncbi.nlm.nih.gov/account/"
    ["COSMIC_API_KEY"]="Register at: https://cancer.sanger.ac.uk/cosmic/register"
    ["OMIM_API_KEY"]="Register at: https://www.omim.org/api"
    ["DRUGBANK_API_KEY"]="Register at: https://go.drugbank.com/public_users/sign_up"
    ["CHEMSPIDER_API_KEY"]="Register at: https://developer.rsc.org/"
)

# Function to store credential in SSM
store_credential() {
    local key_name=$1
    local key_value=$2
    local param_name="/app/${APP_NAME}/credentials/${key_name}"
    
    if aws ssm put-parameter \
        --name "$param_name" \
        --value "$key_value" \
        --type "SecureString" \
        --overwrite \
        --region "$REGION" \
        --description "${CREDENTIALS[$key_name]}" \
        >/dev/null 2>&1; then
        echo "  ✅ Stored $key_name in SSM: $param_name"
        return 0
    else
        echo "  ❌ Failed to store $key_name" >&2
        return 1
    fi
}

# Function to prompt for credential
prompt_credential() {
    local key_name=$1
    local description="${CREDENTIALS[$key_name]}"
    local setup_url="${SETUP_INSTRUCTIONS[$key_name]}"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 $key_name"
    echo "   $description"
    echo "   $setup_url"
    echo ""
    
    # Check if credential already exists
    local param_name="/app/${APP_NAME}/credentials/${key_name}"
    if aws ssm get-parameter --name "$param_name" --region "$REGION" >/dev/null 2>&1; then
        echo "   ℹ️  Credential already configured in SSM"
        read -p "   Update existing credential? (y/N): " update
        if [[ "$update" != "y" && "$update" != "Y" ]]; then
            echo "   ⏭️  Skipped"
            echo ""
            return 0
        fi
    fi
    
    read -s -p "   Enter API key (or press Enter to skip): " api_key
    echo ""
    
    if [ -z "$api_key" ]; then
        echo "   ⏭️  Skipped"
        echo ""
        return 0
    fi
    
    if store_credential "$key_name" "$api_key"; then
        echo ""
        return 0
    else
        echo ""
        return 1
    fi
}

# Main execution
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting credential configuration..."
echo ""

configured_count=0
skipped_count=0
failed_count=0

# Iterate through credentials in order
for key_name in "NCBI_API_KEY" "COSMIC_API_KEY" "OMIM_API_KEY" "DRUGBANK_API_KEY" "CHEMSPIDER_API_KEY"; do
    if prompt_credential "$key_name"; then
        # Check if it was actually configured (not skipped)
        param_name="/app/${APP_NAME}/credentials/${key_name}"
        if aws ssm get-parameter --name "$param_name" --region "$REGION" >/dev/null 2>&1; then
            ((configured_count++))
        else
            ((skipped_count++))
        fi
    else
        ((failed_count++))
    fi
done

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Configuration Summary:"
echo "   ✅ Configured: $configured_count"
echo "   ⏭️  Skipped: $skipped_count"
if [ $failed_count -gt 0 ]; then
    echo "   ❌ Failed: $failed_count"
fi
echo ""

if [ $configured_count -gt 0 ]; then
    echo "✅ Credentials stored successfully in SSM Parameter Store"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Lambda functions will automatically retrieve credentials at runtime"
    echo "   2. Test tools that require credentials (e.g., uniprot_search, clinvar_search)"
    echo "   3. Monitor CloudWatch Logs for credential-related errors"
    echo ""
    echo "To list all configured credentials:"
    echo "   aws ssm get-parameters-by-path --path \"/app/${APP_NAME}/credentials\" --region $REGION --query \"Parameters[*].Name\" --output table"
    echo ""
    echo "To delete a credential:"
    echo "   aws ssm delete-parameter --name \"/app/${APP_NAME}/credentials/{KEY_NAME}\" --region $REGION"
else
    echo "ℹ️  No credentials were configured"
    echo ""
    echo "Most tools work without API keys, but some databases require authentication:"
    echo "   - COSMIC: cancer mutation data"
    echo "   - OMIM: genetic disorder information"
    echo "   - DrugBank: drug-drug interaction data"
    echo "   - ChemSpider: chemical structure data"
    echo "   - NCBI: enhanced rate limits"
    echo ""
    echo "Run this script again anytime to configure credentials."
fi

if [ $failed_count -gt 0 ]; then
    echo ""
    echo "⚠️  Some credentials failed to store. Check IAM permissions:"
    echo "   - ssm:PutParameter"
    echo "   - ssm:GetParameter"
    echo "   - kms:Encrypt (for SecureString parameters)"
    exit 1
fi
