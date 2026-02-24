# HealthLake Agent - AgentCore Deployment Script
# This script deploys the agent to AWS Bedrock AgentCore

param(
    [string]$AgentName = "healthlake-agent",
    [string]$Region = "us-west-2",
    [switch]$LocalTest,
    [switch]$Verbose
)

Write-Host "=== HealthLake Agent - AgentCore Deployment ===" -ForegroundColor Cyan
Write-Host ""

# Check if AgentCore CLI is installed
Write-Host "Checking AgentCore CLI installation..." -ForegroundColor Yellow
$agentcoreInstalled = Get-Command agentcore -ErrorAction SilentlyContinue

if (-not $agentcoreInstalled) {
    Write-Host "AgentCore CLI not found. Installing..." -ForegroundColor Yellow
    pip install bedrock-agentcore-starter-toolkit
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install AgentCore CLI" -ForegroundColor Red
        exit 1
    }
    Write-Host "AgentCore CLI installed successfully" -ForegroundColor Green
}

# Navigate to backend directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Step 1: Configure the agent
Write-Host ""
Write-Host "Step 1: Configuring agent..." -ForegroundColor Yellow

$configArgs = @(
    "configure",
    "--entrypoint", "agent_agentcore.py",
    "--name", $AgentName,
    "--region", $Region,
    "--runtime", "PYTHON_3_12",
    "--requirements-file", "requirements.txt",
    "--deployment-type", "direct_code_deploy",
    "--vpc",
    "--subnets", "subnet-026c3f14dfe982db4,subnet-03eb3c4ca581fbfa9",
    "--security-groups", "sg-029ee008aec2e8a6e",
    "--non-interactive"
)

if ($Verbose) {
    $configArgs += "--verbose"
}

& agentcore @configArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to configure agent" -ForegroundColor Red
    exit 1
}

Write-Host "Agent configured successfully" -ForegroundColor Green

# Step 2: Deploy or test locally
if ($LocalTest) {
    Write-Host ""
    Write-Host "Step 2: Testing locally..." -ForegroundColor Yellow
    Write-Host "Starting local agent server..." -ForegroundColor Cyan
    
    & agentcore launch --agent $AgentName --local
    
} else {
    Write-Host ""
    Write-Host "Step 2: Deploying to AWS..." -ForegroundColor Yellow
    
    $launchArgs = @(
        "launch",
        "--agent", $AgentName,
        "--auto-update-on-conflict"
    )
    
    if ($Verbose) {
        $launchArgs += "--verbose"
    }
    
    & agentcore @launchArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to deploy agent" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "Agent deployed successfully!" -ForegroundColor Green
    
    # Step 3: Check status
    Write-Host ""
    Write-Host "Step 3: Checking agent status..." -ForegroundColor Yellow
    & agentcore status --agent $AgentName --verbose
    
    # Step 4: Test the deployed agent
    Write-Host ""
    Write-Host "Step 4: Testing deployed agent..." -ForegroundColor Yellow
    $testPayload = '{"prompt": "What is the HealthLake datastore information?"}'
    
    Write-Host "Sending test query: $testPayload" -ForegroundColor Cyan
    & agentcore invoke $testPayload --agent $AgentName
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  - Test: agentcore invoke '{\"prompt\": \"your query\"}' --agent $AgentName" -ForegroundColor White
Write-Host "  - Status: agentcore status --agent $AgentName --verbose" -ForegroundColor White
Write-Host "  - Logs: Check CloudWatch Logs in AWS Console" -ForegroundColor White
Write-Host "  - Destroy: agentcore destroy --agent $AgentName" -ForegroundColor White
