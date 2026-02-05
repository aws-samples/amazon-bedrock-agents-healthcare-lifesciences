# Lambda Proxy for MCP Bridge

## Overview

Lambda関数がAgentCore GatewayとECS Bridge Container間のHTTPプロキシとして機能します。

## Architecture

```
AgentCore Gateway (VPC外)
    ↓ [Lambda Target]
Lambda Proxy (VPC内)
    ↓ [HTTP]
Bridge Container (ECS, VPC内)
    ↓ [gRPC]
Mock Device Container (ECS, VPC内)
```

## Benefits

- **コスト削減**: NLB ($16/月) + API Gateway ($3.50/月) = $19.50/月削減
- **レイテンシ改善**: NLB/API Gatewayホップ削除で50-100ms短縮
- **構成簡素化**: Lambda Target標準パターン使用

## Deployment

```bash
# 1. Deploy Lambda Proxy
aws cloudformation deploy \
  --template-file infrastructure/lambda_proxy.yaml \
  --stack-name sila2-lambda-proxy \
  --capabilities CAPABILITY_IAM

# 2. Create MCP Target
./scripts/05_create_mcp_target.sh

# 3. Cleanup old NLB (optional)
./scripts/09_cleanup_nlb.sh
```

## Configuration

- **MCP_ENDPOINT**: `http://bridge-service.sila2.local:8080`
- **Timeout**: 30秒
- **Memory**: 256MB
- **VPC**: Private subnets

## Testing

```bash
# Invoke Lambda directly
aws lambda invoke \
  --function-name sila2-mcp-proxy \
  --payload '{"tool":"list_devices"}' \
  response.json
```
