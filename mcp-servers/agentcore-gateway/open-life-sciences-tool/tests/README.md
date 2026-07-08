# Open Life Sciences MCP Gateway Tests

This directory contains integration tests for the Open Life Sciences MCP Gateway.

## Prerequisites

1. Deploy the infrastructure using `../deploy.sh`
2. Ensure AWS credentials are configured
3. Install test dependencies:

```bash
pip install pytest boto3 requests
```

## Running Tests

### Using pytest

```bash
# Run all tests
pytest tests/test_gateway.py -v

# Run specific test
pytest tests/test_gateway.py::TestGatewayToolInvocation::test_uniprot_search -v
```

### Using Python directly

```bash
# Run all tests
python tests/test_gateway.py
```

### Environment Variables

- `APP_NAME`: Application name (default: `open-life-sciences-tool`)
- `AWS_REGION`: AWS region (default: auto-detected from boto3 session)

## Test Coverage

### test_uniprot_search
Validates:
- OAuth2 token retrieval from Cognito
- Tool invocation via Gateway with valid JWT
- HTTP 200 response for valid requests
- Response format matches Tool Schema (contains `results` field)
- Results respect `max_results` parameter

**Requirements**: 10.2

### test_unknown_tool_returns_404
Validates:
- Error handling for unknown tool names
- HTTP 404 response for non-existent tools
- Error message in response body

**Requirements**: 10.3

### test_invalid_jwt_rejected
Validates:
- JWT validation by Gateway
- HTTP 401 response for invalid tokens
- Security enforcement at Gateway level

**Requirements**: 10.4

## Post-Deployment Verification

Use the verification script for smoke testing:

```bash
bash tests/verify_deployment.sh
```

This script:
1. Checks CloudFormation stack status
2. Retrieves Gateway URL from SSM
3. Obtains OAuth2 token
4. Executes sample tool invocation
5. Reports success/failure with diagnostics
