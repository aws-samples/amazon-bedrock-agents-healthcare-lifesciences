# Deployment Scripts

This directory contains scripts for deploying the Fullstack AgentCore Solution Template
infrastructure and frontend.

## Main Deployment Workflow

### 1. Deploy Infrastructure

```bash
cd infra-cdk
cdk deploy
```

This deploys the CDK stack. Configuration generation is handled during frontend deployment.

### 2. Deploy Frontend

```bash
# From root directory
python scripts/deploy-frontend.py
```

This script automatically:

- Generates fresh `aws-exports.json` from CDK stack outputs
- Installs/updates npm dependencies if needed
- Builds the frontend
- Deploys to AWS Amplify Hosting

## Individual Scripts

### Frontend Deployment

- `deploy-frontend.py` - Cross-platform frontend deployment script (works on Windows, Mac, Linux).
  Uses only Python standard library and AWS CLI. Handles dependency management and config generation.

The script creates `frontend/public/aws-exports.json` with the following structure. This information
is read by the React application to configure Cognito Authentication. If any of this is incorrect,
Cognito will not work. It's generated automatically from the scripts, and you should not need to
change anything:

```json
{
  "authority": "https://cognito-idp.region.amazonaws.com/user-pool-id",
  "client_id": "your-client-id",
  "redirect_uri": "https://your-amplify-url",
  "post_logout_redirect_uri": "https://your-amplify-url",
  "response_type": "code",
  "scope": "email openid profile",
  "automaticSilentRenew": true
}
```

### Shared Utilities

- `utils.py` - Common functions used by both deployment and test scripts:
  - Stack configuration and SSM parameter retrieval
  - Cognito authentication
  - AWS client creation
  - Session ID generation

## Requirements

- AWS CLI configured with appropriate permissions
- Python 3.11+ (standard library only, no pip install needed for deployment)
- Node.js and npm (for frontend build)
- CDK stack deployed with the required outputs:
  - `CognitoClientId`
  - `CognitoUserPoolId`
  - `AmplifyUrl`

## Key Features

- **Cross-Platform**: Works on Windows, Mac, and Linux
- **No Python Dependencies**: Uses only standard library (no virtual environment needed)
- **Automatic Region Detection**: Extracts region directly from CloudFormation stack ARN
- **Smart Dependency Management**: Automatically installs npm dependencies when needed
- **Fresh Config**: Always generates up-to-date configuration from current stack outputs

## New User Experience

For brand new installations, simply run:

```bash
cd infra-cdk
cdk deploy
cd ..
python scripts/deploy-frontend.py
```

The frontend deployment script will automatically handle:

1. Installing npm dependencies (if node_modules doesn't exist)
2. Generating fresh aws-exports.json from your deployed stack
3. Building and deploying the frontend

## Test Scripts

Test scripts have been moved to the `test-scripts/` directory. See [test-scripts/README.md](../test-scripts/README.md) for testing utilities and verification scripts.