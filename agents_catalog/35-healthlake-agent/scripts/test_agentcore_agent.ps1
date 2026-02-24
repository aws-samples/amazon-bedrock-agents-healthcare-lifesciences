# Test AgentCore Deployed Agent
# Quick test script for the deployed HealthLake agent

param(
    [string]$AgentName = "healthlake_agent",
    [string]$Profile = "himssdemo",
    [string]$Region = "us-west-2"
)

Write-Host "=== Testing AgentCore Agent ===" -ForegroundColor Cyan
Write-Host ""

# Set environment
$env:AWS_PROFILE = $Profile
$env:AWS_REGION = $Region

# Test 1: Simple greeting
Write-Host "Test 1: Simple Greeting" -ForegroundColor Yellow
Write-Host "Query: Hello, can you help me?" -ForegroundColor Gray
agentcore invoke '{\"prompt\": \"Hello, can you help me?\"}' --agent $AgentName
Write-Host ""

# Test 2: Datastore info
Write-Host "Test 2: Datastore Information" -ForegroundColor Yellow
Write-Host "Query: What is the HealthLake datastore information?" -ForegroundColor Gray
agentcore invoke '{\"prompt\": \"What is the HealthLake datastore information?\"}' --agent $AgentName
Write-Host ""

# Test 3: Search patients
Write-Host "Test 3: Search Patients" -ForegroundColor Yellow
Write-Host "Query: Search for patients with diabetes" -ForegroundColor Gray
agentcore invoke '{\"prompt\": \"Search for patients with diabetes\"}' --agent $AgentName
Write-Host ""

# Test 4: List S3 documents
Write-Host "Test 4: List S3 Documents" -ForegroundColor Yellow
Write-Host "Query: List documents in S3 bucket" -ForegroundColor Gray
agentcore invoke '{\"prompt\": \"List documents in the S3 bucket\"}' --agent $AgentName
Write-Host ""

# Test 5: With custom context
Write-Host "Test 5: With Custom Context (Doctor Role)" -ForegroundColor Yellow
Write-Host "Query: Search for patients" -ForegroundColor Gray
agentcore invoke '{\"prompt\": \"Search for patients\", \"context\": {\"user_id\": \"doctor-001\", \"user_role\": \"doctor\", \"active_member_id\": null}}' --agent $AgentName
Write-Host ""

Write-Host "=== Testing Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  - Check logs: aws logs tail /aws/bedrock-agentcore/runtimes/healthlake_agent-8N3lyfGL9y-DEFAULT --log-stream-name-prefix '2026/02/16/[runtime-logs]' --follow --region $Region --profile $Profile"
Write-Host "  - View status: agentcore status --agent $AgentName --verbose"
Write-Host "  - Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=$Region#gen-ai-observability/agent-core"
