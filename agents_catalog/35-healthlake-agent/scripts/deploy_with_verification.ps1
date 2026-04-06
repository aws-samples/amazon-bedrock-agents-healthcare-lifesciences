#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy HealthLake Agent with automatic resource verification and creation
.DESCRIPTION
    This script verifies that required AWS resources exist (HealthLake datastore, S3 bucket)
    and creates them if they don't exist, then deploys the agent to AgentCore.
#>

param(
    [string]$AgentName = "healthlake_agent",
    [string]$DatastoreName = "healthlake-agent-datastore",
    [string]$S3BucketPrefix = "healthlake-clinical-docs",
    [string]$Region = "us-east-1",
    [switch]$SkipDatastoreCreation,
    [switch]$SkipS3Creation
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "HealthLake Agent Deployment Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get AWS Account ID
Write-Host "Getting AWS Account ID..." -ForegroundColor Yellow
$AccountId = (aws sts get-caller-identity --query Account --output text)
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to get AWS Account ID. Please check your AWS credentials." -ForegroundColor Red
    exit 1
}
Write-Host "Account ID: $AccountId" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Step 1: Check/Create HealthLake Datastore
# ============================================================================
Write-Host "Step 1: Verifying HealthLake Datastore..." -ForegroundColor Yellow

$DatastoreId = $null
$DatastoreEndpoint = $null

# List existing datastores
$datastores = aws healthlake list-fhir-datastores --region $Region --output json | ConvertFrom-Json

if ($datastores.DatastorePropertiesList.Count -gt 0) {
    # Find ACTIVE datastore
    $activeDatastore = $datastores.DatastorePropertiesList | Where-Object { $_.DatastoreStatus -eq "ACTIVE" } | Select-Object -First 1
    
    if ($activeDatastore) {
        $DatastoreId = $activeDatastore.DatastoreId
        $DatastoreEndpoint = $activeDatastore.DatastoreEndpoint
        Write-Host "✓ Found existing ACTIVE HealthLake datastore:" -ForegroundColor Green
        Write-Host "  Datastore ID: $DatastoreId" -ForegroundColor Green
        Write-Host "  Datastore Name: $($activeDatastore.DatastoreName)" -ForegroundColor Green
        Write-Host "  Endpoint: $DatastoreEndpoint" -ForegroundColor Green
    }
}

if (-not $DatastoreId -and -not $SkipDatastoreCreation) {
    Write-Host "No ACTIVE HealthLake datastore found. Creating new datastore..." -ForegroundColor Yellow
    Write-Host "Note: This will take 5-10 minutes and will preload with SYNTHEA sample data." -ForegroundColor Yellow
    
    $createResponse = aws healthlake create-fhir-datastore `
        --datastore-name $DatastoreName `
        --datastore-type-version R4 `
        --preload-data-config PreloadDataType=SYNTHEA `
        --region $Region `
        --output json | ConvertFrom-Json
    
    if ($LASTEXITCODE -eq 0) {
        $DatastoreId = $createResponse.DatastoreId
        Write-Host "✓ HealthLake datastore creation initiated:" -ForegroundColor Green
        Write-Host "  Datastore ID: $DatastoreId" -ForegroundColor Green
        Write-Host ""
        Write-Host "Waiting for datastore to become ACTIVE (this may take 5-10 minutes)..." -ForegroundColor Yellow
        
        $maxWaitTime = 600  # 10 minutes
        $waitInterval = 30
        $elapsedTime = 0
        
        while ($elapsedTime -lt $maxWaitTime) {
            Start-Sleep -Seconds $waitInterval
            $elapsedTime += $waitInterval
            
            $status = aws healthlake describe-fhir-datastore `
                --datastore-id $DatastoreId `
                --region $Region `
                --output json | ConvertFrom-Json
            
            Write-Host "  Status: $($status.DatastoreProperties.DatastoreStatus) (${elapsedTime}s elapsed)" -ForegroundColor Yellow
            
            if ($status.DatastoreProperties.DatastoreStatus -eq "ACTIVE") {
                $DatastoreEndpoint = $status.DatastoreProperties.DatastoreEndpoint
                Write-Host "✓ Datastore is now ACTIVE!" -ForegroundColor Green
                Write-Host "  Endpoint: $DatastoreEndpoint" -ForegroundColor Green
                break
            }
            
            if ($status.DatastoreProperties.DatastoreStatus -eq "CREATE_FAILED") {
                Write-Host "✗ Datastore creation failed!" -ForegroundColor Red
                Write-Host "  Error: $($status.DatastoreProperties.ErrorCause.ErrorMessage)" -ForegroundColor Red
                exit 1
            }
        }
        
        if ($elapsedTime -ge $maxWaitTime) {
            Write-Host "Warning: Datastore is still creating after 10 minutes." -ForegroundColor Yellow
            Write-Host "You can check status later with: aws healthlake describe-fhir-datastore --datastore-id $DatastoreId" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✗ Failed to create HealthLake datastore" -ForegroundColor Red
        exit 1
    }
} elseif (-not $DatastoreId) {
    Write-Host "✗ No HealthLake datastore found and creation was skipped." -ForegroundColor Red
    Write-Host "Please create a datastore manually or run without --SkipDatastoreCreation" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ============================================================================
# Step 2: Check/Create S3 Bucket for Clinical Documents
# ============================================================================
Write-Host "Step 2: Verifying S3 Bucket for Clinical Documents..." -ForegroundColor Yellow

$S3BucketName = "$S3BucketPrefix-$AccountId"
$bucketExists = $false

# Check if bucket exists
$checkBucket = aws s3api head-bucket --bucket $S3BucketName 2>&1
if ($LASTEXITCODE -eq 0) {
    $bucketExists = $true
    Write-Host "✓ Found existing S3 bucket: $S3BucketName" -ForegroundColor Green
}

if (-not $bucketExists -and -not $SkipS3Creation) {
    Write-Host "S3 bucket not found. Creating bucket..." -ForegroundColor Yellow
    
    if ($Region -eq "us-east-1") {
        aws s3api create-bucket --bucket $S3BucketName --region $Region | Out-Null
    } else {
        aws s3api create-bucket --bucket $S3BucketName --region $Region --create-bucket-configuration LocationConstraint=$Region | Out-Null
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Created S3 bucket: $S3BucketName" -ForegroundColor Green
        
        # Enable versioning
        aws s3api put-bucket-versioning --bucket $S3BucketName --versioning-configuration Status=Enabled | Out-Null
        Write-Host "✓ Enabled versioning on S3 bucket" -ForegroundColor Green
        
        # Add encryption
        aws s3api put-bucket-encryption --bucket $S3BucketName --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }' | Out-Null
        Write-Host "✓ Enabled encryption on S3 bucket" -ForegroundColor Green
        
        # Create sample folder structure
        Write-Host "Creating sample folder structure..." -ForegroundColor Yellow
        $sampleFolders = @("patient-records", "lab-results", "imaging-reports", "clinical-notes")
        foreach ($folder in $sampleFolders) {
            aws s3api put-object --bucket $S3BucketName --key "$folder/" | Out-Null
        }
        Write-Host "✓ Created sample folder structure" -ForegroundColor Green
        
        $bucketExists = $true
    } else {
        Write-Host "✗ Failed to create S3 bucket" -ForegroundColor Red
        Write-Host "Continuing without S3 bucket..." -ForegroundColor Yellow
    }
} elseif (-not $bucketExists) {
    Write-Host "Warning: No S3 bucket found and creation was skipped." -ForegroundColor Yellow
    Write-Host "S3 document features will not be available." -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Step 3: Update .env File
# ============================================================================
Write-Host "Step 3: Updating .env configuration..." -ForegroundColor Yellow

$envPath = ".env"
$envContent = @"
# AWS Configuration
AWS_REGION=$Region
AWS_PROFILE=

# HealthLake Configuration
HEALTHLAKE_DATASTORE_ID=$DatastoreId

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_TEMPERATURE=0.7
BEDROCK_MAX_TOKENS=4096

# S3 Configuration
S3_BUCKET_NAME=$S3BucketName

# AgentCore Configuration
AGENTCORE_RUNTIME_NAME=$AgentName
AGENTCORE_TIMEOUT_SECONDS=300
AGENTCORE_MEMORY_MB=2048

# Debug
DEBUG=false
LOG_LEVEL=INFO
"@

$envContent | Out-File -FilePath $envPath -Encoding UTF8
Write-Host "✓ Updated .env file with configuration" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Step 4: Update AgentCore Configuration
# ============================================================================
Write-Host "Step 4: Updating AgentCore configuration..." -ForegroundColor Yellow

$configPath = ".bedrock_agentcore.yaml"
if (Test-Path $configPath) {
    $config = Get-Content $configPath -Raw | ConvertFrom-Yaml
    
    # Update environment variables
    if (-not $config.agents.$AgentName.environment_variables) {
        $config.agents.$AgentName | Add-Member -MemberType NoteProperty -Name environment_variables -Value @{}
    }
    
    $config.agents.$AgentName.environment_variables.HEALTHLAKE_DATASTORE_ID = $DatastoreId
    $config.agents.$AgentName.environment_variables.AWS_REGION = $Region
    $config.agents.$AgentName.environment_variables.S3_BUCKET_NAME = $S3BucketName
    $config.agents.$AgentName.environment_variables.BEDROCK_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    $config.agents.$AgentName.environment_variables.BEDROCK_TEMPERATURE = "0.7"
    $config.agents.$AgentName.environment_variables.BEDROCK_MAX_TOKENS = "4096"
    
    $config | ConvertTo-Yaml | Out-File -FilePath $configPath -Encoding UTF8
    Write-Host "✓ Updated AgentCore configuration with environment variables" -ForegroundColor Green
} else {
    Write-Host "Warning: .bedrock_agentcore.yaml not found. Run 'agentcore configure' first." -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================
# Step 5: Display Summary
# ============================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuration Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AWS Account: $AccountId" -ForegroundColor White
Write-Host "Region: $Region" -ForegroundColor White
Write-Host "HealthLake Datastore ID: $DatastoreId" -ForegroundColor White
if ($DatastoreEndpoint) {
    Write-Host "HealthLake Endpoint: $DatastoreEndpoint" -ForegroundColor White
}
if ($bucketExists) {
    Write-Host "S3 Bucket: $S3BucketName" -ForegroundColor White
}
Write-Host ""

# ============================================================================
# Step 6: Deploy Agent
# ============================================================================
Write-Host "Step 6: Deploying agent to AgentCore..." -ForegroundColor Yellow
Write-Host ""

$deployChoice = Read-Host "Do you want to deploy the agent now? (y/n)"
if ($deployChoice -eq "y" -or $deployChoice -eq "Y") {
    Write-Host "Starting deployment..." -ForegroundColor Yellow
    agentcore deploy --agent $AgentName
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Deployment Complete!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Test your agent with:" -ForegroundColor White
        Write-Host "  agentcore invoke '{\"prompt\": \"Search for patients\"}' --agent $AgentName" -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host "✗ Deployment failed. Check the error messages above." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "Deployment skipped. To deploy later, run:" -ForegroundColor Yellow
    Write-Host "  agentcore deploy --agent $AgentName" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "Done!" -ForegroundColor Green
