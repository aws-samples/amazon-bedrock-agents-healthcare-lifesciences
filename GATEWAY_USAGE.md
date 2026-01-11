# Gateway経由でAgentを呼び出す方法

## 1. アクセストークンの取得

Cognitoからアクセストークンを取得します：

```bash
~/.pyenv/shims/python3 get_cognito_token.py
```

ユーザー名とパスワードを入力すると、アクセストークンが表示されます。

## 2. 環境変数の設定

取得したアクセストークンを環境変数に設定します：

```bash
export ACCESS_TOKEN="<取得したアクセストークン>"
```

## 3. Agentの実行

```bash
~/.pyenv/shims/python3 invoke_agent_with_gateway.py
```

## Gateway情報

- **Gateway URL**: `https://sila2-gateway-1764211277-oenso7x7wz.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp`
- **Runtime ARN**: `arn:aws:bedrock-agentcore:us-west-2:590183741681:runtime/sila2_phase3_agent-gmO6NDCNWW`
- **Gateway ARN**: `arn:aws:bedrock-agentcore:us-west-2:590183741681:gateway/sila2-gateway-1764211277-oenso7x7wz`
- **認証**: Custom JWT (Cognito)
- **User Pool ID**: `us-west-2_nS2VRVQua`
- **Client ID**: `2faf353j7nl9gh1ond7a5ehlem`

## RuntimeとGatewayの関連付け

RuntimeとGatewayを関連付けるには、Gateway側からtargetを作成します：

```python
import boto3
client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')
response = client.create_gateway_target(
    gatewayIdentifier='sila2-gateway-1764211277-oenso7x7wz',
    targetIdentifier='arn:aws:bedrock-agentcore:us-west-2:590183741681:runtime/sila2_phase3_agent-gmO6NDCNWW'
)
```
