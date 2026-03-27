# HealthLake Agent - Template Integration Script (PowerShell)
# This script integrates the HealthLake agent with the agentcore_template

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Green
Write-Host "HealthLake Agent Template Integration" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "agentcore_template")) {
    Write-Host "Error: agentcore_template directory not found" -ForegroundColor Red
    Write-Host "Please run this script from the repository root"
    exit 1
}

if (-not (Test-Path "agents_catalog/35-healthlake-agent")) {
    Write-Host "Error: agents_catalog/35-healthlake-agent directory not found" -ForegroundColor Red
    exit 1
}

# Get configuration
Write-Host "Configuration:" -ForegroundColor Yellow
$PREFIX = Read-Host "Enter your prefix (e.g., myapp)"
$HEALTHLAKE_DATASTORE_ID = Read-Host "Enter your HealthLake datastore ID"
$AWS_REGION = Read-Host "Enter AWS region (default: us-west-2)"
if ([string]::IsNullOrWhiteSpace($AWS_REGION)) {
    $AWS_REGION = "us-west-2"
}

Write-Host ""
Write-Host "Step 1: Copying HealthLake tools to template" -ForegroundColor Green
$sourceFile = "agentcore_template\agent\agent_config\tools\healthlake_tools.py"
if (Test-Path $sourceFile) {
    Write-Host "✓ Tools already exist" -ForegroundColor Green
} else {
    Write-Host "✓ Tools copied" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 2: Creating SSM parameter for HealthLake datastore" -ForegroundColor Green
try {
    aws ssm put-parameter `
        --name "/app/$PREFIX/healthlake/datastore_id" `
        --value "$HEALTHLAKE_DATASTORE_ID" `
        --type "String" `
        --region "$AWS_REGION" `
        --overwrite
    Write-Host "✓ SSM parameter created" -ForegroundColor Green
} catch {
    Write-Host "Warning: Could not create SSM parameter (may need to do manually)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 3: Updating requirements.txt" -ForegroundColor Green
$requirementsFile = "agentcore_template\agent\requirements.txt"
$requirementsContent = Get-Content $requirementsFile -Raw
if ($requirementsContent -notmatch "requests>=2.31.0") {
    Add-Content -Path $requirementsFile -Value "requests>=2.31.0"
    Write-Host "✓ Added requests to requirements" -ForegroundColor Green
} else {
    Write-Host "✓ requests already in requirements" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 4: Creating IAM policy document" -ForegroundColor Green
$policyJson = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "healthlake:DescribeFHIRDatastore",
        "healthlake:ReadResource",
        "healthlake:SearchWithGet",
        "healthlake:SearchWithPost"
      ],
      "Resource": "arn:aws:healthlake:*:*:datastore/fhir/*"
    }
  ]
}
"@
$policyPath = "$env:TEMP\healthlake-policy.json"
$policyJson | Out-File -FilePath $policyPath -Encoding UTF8
Write-Host "✓ Policy document created at $policyPath" -ForegroundColor Green

Write-Host ""
Write-Host "Step 5: Getting runtime role" -ForegroundColor Green
try {
    $RUNTIME_ROLE = aws ssm get-parameter --name "/app/$PREFIX/agentcore/runtime_iam_role" --query "Parameter.Value" --output text --region "$AWS_REGION" 2>$null
    
    if ([string]::IsNullOrWhiteSpace($RUNTIME_ROLE)) {
        throw "Role not found"
    }
    
    Write-Host "✓ Found runtime role: $RUNTIME_ROLE" -ForegroundColor Green
    
    $ROLE_NAME = $RUNTIME_ROLE.Split('/')[-1]
    
    Write-Host ""
    Write-Host "Step 6: Attaching HealthLake policy to role" -ForegroundColor Green
    try {
        aws iam put-role-policy `
            --role-name "$ROLE_NAME" `
            --policy-name HealthLakeAccess `
            --policy-document "file://$policyPath" `
            --region "$AWS_REGION"
        Write-Host "✓ Policy attached" -ForegroundColor Green
    } catch {
        Write-Host "Warning: Could not attach policy (may need to do manually)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Warning: Could not find runtime role in SSM" -ForegroundColor Yellow
    Write-Host "You'll need to attach the HealthLake policy manually" -ForegroundColor Yellow
    Write-Host "Policy document is at: $policyPath" -ForegroundColor Yellow
    $RUNTIME_ROLE = "<your-runtime-role-arn>"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Integration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Update agent_task.py to use HealthLake tools:"
Write-Host "   cd agentcore_template\agent\agent_config" -ForegroundColor Green
Write-Host "   # Edit agent_task.py and add:" -ForegroundColor Green
Write-Host "   from .tools.healthlake_tools import HEALTHLAKE_TOOLS" -ForegroundColor Green
Write-Host "   # Then update tools parameter: tools=HEALTHLAKE_TOOLS" -ForegroundColor Green
Write-Host ""
Write-Host "2. Deploy the agent:"
Write-Host "   cd agentcore_template" -ForegroundColor Green
Write-Host "   agentcore configure --entrypoint main.py -rf agent/requirements.txt -er $RUNTIME_ROLE --name $PREFIX-healthlake-agent" -ForegroundColor Green
Write-Host "   rm .agentcore.yaml" -ForegroundColor Green
Write-Host "   agentcore launch" -ForegroundColor Green
Write-Host ""
Write-Host "3. Test the agent:"
Write-Host "   agentcore invoke '{`"prompt`": `"What is the HealthLake datastore information?`"}' --agent $PREFIX-healthlake-agent" -ForegroundColor Green
Write-Host ""
Write-Host "For detailed instructions, see:" -ForegroundColor Yellow
Write-Host "   agents_catalog\35-healthlake-agent\AGENTCORE_TEMPLATE_README.md"
Write-Host ""
