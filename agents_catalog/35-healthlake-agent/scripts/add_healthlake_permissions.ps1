# Add HealthLake Permissions to AgentCore Execution Role
# This script adds the necessary HealthLake permissions to the AgentCore execution role

param(
    [Parameter(Mandatory=$true)][string]$RoleName,
    [string]$Profile = $env:AWS_PROFILE,
    [string]$Region = "us-east-1"
)

$PolicyName = "HealthLakeAccessPolicy"
$PolicyFile = "healthlake-permissions-policy.json"

Write-Host "Adding HealthLake permissions to role: $RoleName" -ForegroundColor Cyan
Write-Host ""

# Add inline policy to the role using file:// URI
$args = @("iam", "put-role-policy",
    "--role-name", $RoleName,
    "--policy-name", $PolicyName,
    "--policy-document", "file://$PolicyFile",
    "--region", $Region
)

if ($Profile) {
    $args += @("--profile", $Profile)
}

aws @args

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Successfully added HealthLake permissions!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Permissions added:" -ForegroundColor Yellow
    Write-Host "  - healthlake:DescribeFHIRDatastore"
    Write-Host "  - healthlake:ReadResource"
    Write-Host "  - healthlake:SearchWithGet"
    Write-Host "  - healthlake:SearchWithPost"
    Write-Host ""
    Write-Host "Next: Test the agent with HealthLake queries"
    Write-Host "  .\test_agentcore_agent.ps1"
} else {
    Write-Host "❌ Failed to add permissions" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual steps:" -ForegroundColor Yellow
    Write-Host "1. Go to IAM Console: https://console.aws.amazon.com/iam/"
    Write-Host "2. Find role: $RoleName"
    Write-Host "3. Add inline policy with contents from healthlake-permissions-policy.json"
}
