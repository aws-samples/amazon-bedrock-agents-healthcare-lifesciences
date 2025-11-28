# ALB vs Service Discovery 比較

## 概要

Task 8では、ALBを削除してService Discovery直接接続に移行します。

---

## アーキテクチャ比較

### With ALB (現在)
```
AgentCore Gateway --> ALB --> Bridge Container --> Mock Device Container
                      ↓
                   $16/月
                   +50-100ms
```

### Service Discovery (Task 8)
```
AgentCore Gateway --> Bridge Container --> Mock Device Container
                      (bridge.sila2.local:8080)
                      ↓
                   $0/月
                   直接接続
```

---

## コスト比較

| リソース | With ALB | Service Discovery | 削減額 |
|---------|----------|-------------------|--------|
| ALB | $16/月 | $0 | **-$16** |
| ECS Fargate (Bridge) | $7/月 | $7/月 | $0 |
| ECS Fargate (Mock) | $7/月 | $7/月 | $0 |
| CloudWatch Logs | $2/月 | $2/月 | $0 |
| **合計** | **$32/月** | **$16/月** | **-$16 (50%)** |

---

## パフォーマンス比較

| メトリクス | With ALB | Service Discovery | 改善 |
|-----------|----------|-------------------|------|
| レイテンシ | 150-200ms | 100-150ms | **-50ms** |
| ホップ数 | 3 | 2 | **-1** |
| DNS解決 | ALB DNS | Service Discovery | 同等 |
| ヘルスチェック | ALB + ECS | ECS | 簡素化 |

---

## リソース比較

### 削除されるリソース (3個)
- ❌ BridgeALB
- ❌ BridgeTargetGroup
- ❌ BridgeListener

### 追加されるリソース (2個)
- ✅ ServiceDiscoveryNamespace (`sila2.local`)
- ✅ BridgeServiceDiscovery (`bridge.sila2.local`)

**純減**: 1リソース

---

## 接続方法の変更

### With ALB
```yaml
# Gateway Target設定
Endpoint: http://sila2-bridge-dev-123456789.us-east-1.elb.amazonaws.com:8080
```

### Service Discovery
```yaml
# Gateway Target設定
Endpoint: http://bridge.sila2.local:8080
```

**注意**: AgentCore GatewayがVPC内に存在する必要があります。

---

## メリット

### 1. コスト削減
- ALB $16/月削減
- 50%のコスト削減

### 2. レイテンシ改善
- ALBホップ削除
- 50-100ms短縮

### 3. 構成簡素化
- リソース数削減
- 管理対象減少

### 4. セキュリティ向上
- VPC内部通信のみ
- 外部公開不要

---

## デメリット

### 1. VPC制約
- Gateway must be in same VPC
- Cross-VPC requires VPC Peering

### 2. ヘルスチェック
- ALBレベルのヘルスチェック喪失
- ECSタスクレベルのみ

### 3. スケーリング
- ALBの自動スケーリング機能喪失
- 手動スケーリング必要

---

## 移行手順

### 1. 新テンプレートデプロイ
```bash
aws cloudformation deploy \
  --template-file infrastructure/bridge_container_ecs_no_alb.yaml \
  --stack-name sila2-bridge-ecs-no-alb \
  --parameter-overrides \
    VpcId=vpc-xxx \
    SubnetIds=subnet-xxx,subnet-yyy \
    EnvironmentName=dev \
  --capabilities CAPABILITY_IAM
```

### 2. Gateway Target更新
```bash
# 新エンドポイント取得
ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name sila2-bridge-ecs-no-alb \
  --query 'Stacks[0].Outputs[?OutputKey==`BridgeServiceEndpoint`].OutputValue' \
  --output text)

# Gateway Target更新
GATEWAY_ID=<gateway-id> \
ENDPOINT=$ENDPOINT \
python scripts/create_mcp_gateway_target.py
```

### 3. 動作確認
```bash
# DNS解決確認
nslookup bridge.sila2.local

# ヘルスチェック
curl http://bridge.sila2.local:8080/health
```

### 4. 旧スタック削除
```bash
aws cloudformation delete-stack \
  --stack-name sila2-bridge-ecs
```

---

## ロールバック手順

### 問題発生時
```bash
# 旧スタック再デプロイ
aws cloudformation deploy \
  --template-file infrastructure/bridge_container_ecs.yaml \
  --stack-name sila2-bridge-ecs \
  --parameter-overrides ... \
  --capabilities CAPABILITY_IAM

# Gateway Target復元
GATEWAY_ID=<gateway-id> \
OLD_ENDPOINT=<alb-endpoint> \
python scripts/create_mcp_gateway_target.py
```

---

## 推奨事項

### 開発環境
✅ **Service Discovery推奨**
- コスト削減優先
- VPC内通信のみ

### 本番環境
⚠️ **ALB検討**
- 高可用性要求
- クロスVPC通信
- 外部アクセス必要

---

## 結論

**Task 8実装により**:
- ✅ コスト50%削減 ($16/月)
- ✅ レイテンシ改善 (50ms)
- ✅ 構成簡素化 (1リソース減)
- ⚠️ VPC内通信限定

**推奨**: 開発環境でService Discovery採用、本番環境は要件次第
