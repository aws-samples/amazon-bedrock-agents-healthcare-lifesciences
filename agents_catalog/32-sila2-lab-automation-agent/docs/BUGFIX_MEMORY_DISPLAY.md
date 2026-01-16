# Memory Display Bugfix

## 問題

Streamlit UIで最新の定期実行ログが表示されない問題が発生していました。

### 根本原因

1. **AgentCore Memory API の制限**: `list_sessions` APIが最新セッションを即座に返さない（キャッシュ遅延）
2. **セッションID形式の変更**: `sila2-{device_id}-{timestamp}-{uuid}` 形式が `memory_client.create_event()` でサイレント失敗

## 修正内容

### 1. Lambda関数 (`src/lambda/invoker/lambda_function.py`)

**変更**: セッションID形式を元に戻す

```python
# 修正前（失敗）
device_session_id = f"sila2-{device_id}-{int(time.time())}-{uuid.uuid4().hex}"

# 修正後（成功）
device_session_id = f"{device_id}-{int(time.time())}-{uuid.uuid4().hex}"
```

**理由**: `sila2-` プレフィックス付きセッションIDは `memory_client.create_event()` でサイレント失敗する

### 2. Streamlit UI (`streamlit_app/app.py`)

**追加**: CloudWatch Logsから最新セッションIDを取得

```python
def get_recent_session_ids_from_logs():
    """CloudWatch Logsから最近のセッションIDを取得"""
    logs_client = boto3.client('logs', region_name=AWS_REGION)
    start_time = int((time.time() - 600) * 1000)  # 10分前
    
    response = logs_client.filter_log_events(
        logGroupName='/aws/lambda/' + LAMBDA_FUNCTION,
        startTime=start_time,
        filterPattern='"Memory recorded successfully: session="'
    )
    
    session_ids = []
    for event in response.get('events', []):
        message = event.get('message', '')
        if 'session=' in message:
            parts = message.split('session=')
            if len(parts) > 1:
                session_id = parts[1].split(',')[0].strip()
                if session_id and session_id not in session_ids:
                    session_ids.append(session_id)
    
    return session_ids
```

**変更**: `get_memory_events_with_id()` で両方のソースを統合

```python
# 1. CloudWatch Logsから最新セッション取得
recent_session_ids = get_recent_session_ids_from_logs()
all_session_ids.update(recent_session_ids)

# 2. list_sessionsで既知セッション取得
sessions_response = bedrock_agentcore.list_sessions(...)
for session in sessions:
    all_session_ids.add(session.get('sessionId'))

# 3. 統合されたセッションからイベント取得
for session_id in all_session_ids:
    events_response = bedrock_agentcore.list_events(...)
```

## デプロイ手順

### 既存環境への適用

```bash
# 1. Lambda関数を再パッケージ
cd scripts
./02_package_lambdas.sh

# 2. Lambda関数コードを更新
aws lambda update-function-code \
  --function-name sila2-agentcore-invoker \
  --s3-bucket sila2-deployment-590183741681-us-west-2 \
  --s3-key lambda/invoker.zip \
  --region us-west-2

# 3. Streamlit UIを再起動（自動リロード）
# ブラウザでStreamlit UIをリフレッシュ
```

### 新規デプロイ

通常のデプロイ手順に従ってください。修正は既にコードに含まれています。

```bash
cd scripts
./01_setup_ecr_and_build.sh
./02_package_lambdas.sh
./03_deploy_stack.sh --vpc-id vpc-xxxxx --subnet-ids subnet-xxxxx,subnet-yyyyy
./04_deploy_agentcore.sh
```

## 検証方法

### 1. Lambda関数のテスト

```bash
# 定期実行をトリガー
aws lambda invoke \
  --function-name sila2-agentcore-invoker \
  --payload '{"action":"periodic","device_id":"hplc"}' \
  --region us-west-2 \
  /tmp/response.json

# ログ確認
aws logs filter-log-events \
  --log-group-name /aws/lambda/sila2-agentcore-invoker \
  --start-time $(($(date +%s) - 120))000 \
  --region us-west-2 \
  --filter-pattern "Memory recorded successfully"
```

**期待される出力**:
```
[INFO] Memory recorded successfully: session=hplc-1768278064-..., result={...}
```

### 2. Streamlit UIの確認

1. Streamlit UIを開く
2. **AI Memory** タブに移動
3. **Debug Info** を展開
4. 以下を確認：
   - `log_sessions_count`: CloudWatch Logsから取得したセッション数（> 0）
   - `list_sessions_count`: list_sessionsから取得したセッション数
   - `total_unique_sessions`: 統合後の総セッション数
   - `latest_event_time`: 最新イベントのタイムスタンプ（現在時刻に近い）

5. イベントリストに最新の定期実行ログが表示されることを確認

## 技術的詳細

### AgentCore Memory API の制限

- `list_sessions` APIは内部キャッシュを使用
- 新しいセッションが即座に反映されない（数分の遅延）
- `list_events` は特定のセッションIDで直接クエリ可能

### 回避策

CloudWatch Logsから最新のセッションIDを取得し、`list_events` で直接クエリすることで、キャッシュ遅延を回避。

### セッションID形式の制約

- AgentCore Runtime APIは `runtimeSessionId` に最小33文字を要求
- しかし、Memory APIの `create_event()` は特定のプレフィックス（`sila2-`）でサイレント失敗
- 元の形式 `{device_id}-{timestamp}-{uuid}` は正常に動作

## 影響範囲

- **Lambda関数**: `src/lambda/invoker/lambda_function.py` の `handle_periodic()` 関数のみ
- **Streamlit UI**: `streamlit_app/app.py` の `get_memory_events_with_id()` 関数のみ
- **その他**: 影響なし

## 今後の推奨事項

1. **AgentCore Memory API の改善**: AWS側でキャッシュ遅延の改善を要望
2. **セッションID形式の標準化**: Memory APIで許可される形式を明確化
3. **エラーハンドリング強化**: `create_event()` のサイレント失敗を検出
