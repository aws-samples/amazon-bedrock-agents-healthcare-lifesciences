#!/bin/bash

# Phase 3 AgentCore動作確認スクリプト
source .phase3-config

echo "=== AgentCore Runtime & Gateway 動作確認 ==="

# 1. Runtime確認
echo "1. Runtime確認中..."
agentcore runtime list

# 2. Gateway確認
echo -e "\n2. Gateway確認中..."
agentcore gateway list

# 3. Gateway詳細情報
echo -e "\n3. Gateway詳細情報..."
agentcore gateway describe --gateway-identifier sila2-gateway-new

# 4. Gateway URLテスト
echo -e "\n4. Gateway URLテスト..."
GATEWAY_URL="https://sila2-gateway-new-cr6efpcusg.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp"
echo "Gateway URL: $GATEWAY_URL"

# 5. Lambda関数確認
echo -e "\n5. Lambda関数確認..."
aws lambda list-functions --query 'Functions[?contains(FunctionName, `sila2-phase3`)].{Name:FunctionName,Runtime:Runtime,Status:State}' --output table

# 6. API Gateway確認
echo -e "\n6. API Gateway確認..."
aws apigateway get-rest-apis --query 'items[?contains(name, `sila2-phase3`)].{Name:name,Id:id,Status:endpointConfiguration.types[0]}' --output table

echo -e "\n=== 動作確認完了 ==="