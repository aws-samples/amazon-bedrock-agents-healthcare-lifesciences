# Configure AgentCore with proper AWS credentials
param(
    [string]$AgentName = "healthlake-agent",
    [string]$Region = "us-west-2"
)

Write-Host "Setting up AWS credentials..." -ForegroundColor Yellow

# Set AWS environment variables
$env:AWS_PROFILE = "himssdemo"
$env:AWS_REGION = $Region
$env:AWS_DEFAULT_REGION = $Region

# Verify AWS credentials
Write-Host "Verifying AWS credentials..." -ForegroundColor Yellow
$identity = aws sts get-caller-identity 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ AWS credentials not valid. Please run 'aws configure --profile himssdemo'" -ForegroundColor Red
    exit 1
}

Write-Host "✓ AWS credentials verified" -ForegroundColor Green
Write-Host $identity

# Configure AgentCore
Write-Host ""
Write-Host "Configuring AgentCore agent..." -ForegroundColor Yellow

agentcore configure `
    --entrypoint agent_agentcore.py `
    --name $AgentName `
    --region $Region `
    --runtime PYTHON_3_12 `
    --requirements-file requirements.txt `
    --deployment-type direct_code_deploy `
    --non-interactive

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Configuration failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
    Write-Host "1. Ensure AWS CLI is configured: aws configure --profile himssdemo"
    Write-Host "2. Verify credentials: aws sts get-caller-identity --profile himssdemo"
    Write-Host "3. Check if you have necessary IAM permissions"
    exit 1
}

Write-Host "✓ Agent configured successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Configuration saved to .bedrock_agentcore.yaml"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Review config: Get-Content .bedrock_agentcore.yaml"
Write-Host "  2. Deploy: agentcore deploy --agent $AgentName"
Write-Host "  3. Test: agentcore invoke '{\"prompt\": \"Hello\"}' --agent $AgentName"
