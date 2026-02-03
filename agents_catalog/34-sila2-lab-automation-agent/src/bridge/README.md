# Bridge Container - MCP Server + gRPC Client

## 概要
AgentCore GatewayからのMCPリクエストを受け、gRPC経由でSiLA2デバイスと通信するブリッジコンテナ

## アーキテクチャ
```
AgentCore Gateway --[MCP/HTTP]--> Bridge Container --[gRPC]--> Mock Device Lambda
                                  (Port 8080)
```

## ファイル構成
- `mcp_server.py` - MCPプロトコルサーバー (FastAPI)
- `grpc_client.py` - gRPCクライアント (3デバイス接続)
- `main.py` - エントリーポイント
- `Dockerfile` - コンテナイメージ定義
- `requirements.txt` - Python依存関係

## ローカル実行
```bash
# 依存関係インストール
pip install -r requirements.txt

# サーバー起動
python main.py

# ヘルスチェック
curl http://localhost:8080/health
```

## Docker実行
```bash
# ビルド
docker build -t sila2-bridge .

# 実行
docker run -p 8080:8080 \
  -e HPLC_GRPC_URL=host.docker.internal:50051 \
  -e CENTRIFUGE_GRPC_URL=host.docker.internal:50052 \
  -e PIPETTE_GRPC_URL=host.docker.internal:50053 \
  sila2-bridge
```

## 環境変数
- `HPLC_GRPC_URL` - HPLCデバイスgRPCエンドポイント (default: localhost:50051)
- `CENTRIFUGE_GRPC_URL` - 遠心分離機gRPCエンドポイント (default: localhost:50052)
- `PIPETTE_GRPC_URL` - ピペットgRPCエンドポイント (default: localhost:50053)

## MCPツール
1. `list_devices` - 利用可能なデバイス一覧取得
2. `get_device_status` - デバイスステータス取得
3. `execute_command` - デバイスコマンド実行

## デプロイ
ECS Fargateへのデプロイは `../scripts/02_build_containers.sh` と `../scripts/03_deploy_ecs.sh` を使用
