# Lambda Proxy成功のための修正サマリー

## 🎯 問題と解決

### 問題1: AgentCore Gatewayが空イベントを送信
**現象**: `{}` または `{"device_type": ""}` が送信される
**原因**: AgentCore GatewayのMCP標準プロトコル実装
**解決**: Lambda Proxyで空イベントを`list_devices`ツール呼び出しに変換

### 問題2: DNS解決エラー
**現象**: `bridge.sila2.local` が解決できない
**原因**: Lambda Security GroupにDNS (UDP 53)のアウトバウンドルールがない
**解決**: UDP 53ポートのアウトバウンドルールを追加

### 問題3: Gatewayプレフィックス
**現象**: ツール名に `gateway-id___` プレフィックスが付く
**原因**: AgentCore Gatewayが自動的にプレフィックスを追加
**解決**: Bridge ContainerとLambda Proxyでプレフィックスを除去

---

## 📁 修正が必要なファイル

### 1. `lambda_proxy/index.py` ⭐ 最重要

```python
def lambda_handler(event, context):
    # AgentCore Gateway sends tool calls in different formats
    tool_name = event.get('name', '')
    arguments = event.get('arguments', event if event else {})
    
    # Remove Gateway prefix if present
    if tool_name and '___' in tool_name:
        tool_name = tool_name.split('___', 1)[1]
    
    # Empty event → list_devices
    if not tool_name:
        method = "tools/call"
        params = {"name": "list_devices", "arguments": arguments}
    else:
        method = "tools/call"
        params = {"name": tool_name, "arguments": arguments}
    
    # Build JSON-RPC request
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": event.get('id', 1)
    }
    
    # Forward to Bridge Container
    response = http.request(
        'POST',
        f"{MCP_ENDPOINT}/mcp",
        body=json.dumps(jsonrpc_request),
        headers={'Content-Type': 'application/json'},
        timeout=30.0
    )
    
    return json.loads(response.data.decode('utf-8'))
```

### 2. `bridge_container/mcp_server.py`

```python
@app.post("/mcp")
async def handle_mcp(request: Request):
    body = await request.json()
    
    # Handle empty event
    if not body or body == {}:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Empty request"},
            "id": None
        }
    
    # Handle JSON-RPC format
    if "jsonrpc" in body:
        method = body.get("method")
        params = body.get("params", {})
        
        if method == "tools/call":
            tool_name = params.get("name")
            # Remove Gateway prefix
            if tool_name and '___' in tool_name:
                tool_name = tool_name.split('___', 1)[1]
            arguments = params.get("arguments", {})
            # ... rest of the code
```

### 3. Lambda Security Group (手動実行またはスクリプト化)

```bash
# DNS解決用のUDP 53ポートを追加
aws ec2 authorize-security-group-egress \
  --group-id <LAMBDA_SG_ID> \
  --ip-permissions IpProtocol=udp,FromPort=53,ToPort=53,IpRanges='[{CidrIp=0.0.0.0/0}]' \
  --region us-west-2
```

---

## 🚀 デプロイ手順

### 既存環境への適用

1. **Lambda Proxyを更新**
```bash
cd lambda_proxy
zip -r /tmp/lambda-proxy.zip .
aws lambda update-function-code \
  --function-name sila2-mcp-proxy \
  --zip-file fileb:///tmp/lambda-proxy.zip \
  --region us-west-2
```

2. **Bridge Containerを再ビルド・デプロイ**
```bash
./scripts/02_build_containers.sh
aws ecs update-service \
  --cluster sila2-bridge-dev \
  --service sila2-bridge-dev \
  --force-new-deployment \
  --region us-west-2
```

3. **Lambda Security Groupを更新**
```bash
LAMBDA_SG=$(aws lambda get-function-configuration \
  --function-name sila2-mcp-proxy \
  --region us-west-2 \
  --query 'VpcConfig.SecurityGroupIds[0]' \
  --output text)

aws ec2 authorize-security-group-egress \
  --group-id $LAMBDA_SG \
  --ip-permissions IpProtocol=udp,FromPort=53,ToPort=53,IpRanges='[{CidrIp=0.0.0.0/0}]' \
  --region us-west-2
```

### 新規デプロイ

既存のデプロイスクリプトを使用:
```bash
./scripts/deploy_all.sh
```

**注意**: Step 3の後にLambda Security Groupを手動更新する必要があります。

---

## ✅ 動作確認

```bash
# テスト実行
agentcore invoke '{"prompt": "List all available SiLA2 devices"}'

# 期待される結果
# 3つのデバイス (HPLC, Centrifuge, Pipette) がリストされる
```

---

## 📊 最終アーキテクチャ

```
AgentCore Gateway
    ↓ [MCP Protocol] 空イベント {} 送信
Lambda Proxy (index.py)
    ↓ [JSON-RPC 2.0] {"method":"tools/call","params":{"name":"list_devices"}}
Bridge Container (mcp_server.py)
    ↓ [gRPC] GetDeviceInfo()
Mock Device Container
    └─ 3デバイス応答
```

---

## 🔍 トラブルシューティング

### Lambda Proxyログ確認
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/sila2-mcp-proxy \
  --start-time $(($(date +%s) * 1000 - 300000)) \
  --region us-west-2 \
  --query 'events[*].message' \
  --output text | grep -E "(Received|Forwarding|Bridge)"
```

### Bridge Containerログ確認
```bash
aws logs get-log-events \
  --log-group-name /ecs/sila2-bridge-dev \
  --log-stream-name <STREAM_NAME> \
  --region us-west-2 \
  --limit 50 \
  --query 'events[*].message' \
  --output text | grep "Connected to"
```

### gRPC接続確認
起動時のログに以下が表示されるはず:
```
Connected to hplc at mock-devices.sila2.local:50051
Connected to centrifuge at mock-devices.sila2.local:50051
Connected to pipette at mock-devices.sila2.local:50051
```
