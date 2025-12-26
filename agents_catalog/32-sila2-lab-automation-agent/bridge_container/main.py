"""Main - Phase 4 MCP Server + Phase 6 REST API"""
import uvicorn
import os
import threading
from api import buffer
from stream_client import GRPCStreamClient

# mcp_server.appにREST APIエンドポイントを追加
from mcp_server import app
from api import get_device_history, list_devices

app.get("/api/history/{device_id}")(get_device_history)
app.get("/api/devices")(list_devices)

def start_grpc_streaming():
    grpc_server = os.getenv('GRPC_SERVER', 'mock-device:50051')
    device_id = os.getenv('DEVICE_ID', 'hplc')
    client = GRPCStreamClient(grpc_server, device_id, buffer)
    client.start_streaming()

if __name__ == "__main__":
    threading.Thread(target=start_grpc_streaming, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)
