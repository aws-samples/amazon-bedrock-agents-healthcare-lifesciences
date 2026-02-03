#!/bin/bash
set -e

echo "=== Bridge Container Local Test ==="

# 依存関係インストール
echo "Installing dependencies..."
pip install -q -r requirements.txt

# gRPCコード生成
echo "Generating gRPC code..."
cd ..
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. src/proto/sila2_basic.proto
cd src/bridge

# モックgRPCサーバー起動
echo "Starting mock gRPC servers..."
python test_mock_grpc_server.py &
MOCK_PID=$!
sleep 2

# MCPサーバー起動
echo "Starting MCP server..."
python main.py &
MCP_PID=$!
sleep 3

# ヘルスチェック
echo "Testing health endpoint..."
curl -s http://localhost:8080/health | python -m json.tool

# MCPリクエストテスト
echo -e "\nTesting MCP list_devices..."
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool_calls": [{"name": "list_devices", "arguments": {}}]}' | python -m json.tool

echo -e "\nTesting MCP get_device_status..."
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool_calls": [{"name": "get_device_status", "arguments": {"device_id": "hplc"}}]}' | python -m json.tool

echo -e "\nTesting MCP execute_command..."
curl -s -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool_calls": [{"name": "execute_command", "arguments": {"device_id": "hplc", "command": "start_analysis", "parameters": {"sample": "test-001"}}}]}' | python -m json.tool

# クリーンアップ
echo -e "\nCleaning up..."
kill $MCP_PID $MOCK_PID 2>/dev/null || true

echo -e "\n=== Test Complete ==="
