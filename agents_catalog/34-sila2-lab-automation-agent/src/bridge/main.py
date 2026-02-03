"""Main - MCP Server with SiLA2 Bridge"""
import uvicorn
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from mcp_server import app, bridge, buffer
from sila2_stream_client import SiLA2StreamClient

def start_device_streams():
    """Start streaming for all available devices"""
    grpc_server = os.getenv('GRPC_SERVER', 'mock-devices.sila2.local:50051')
    host, port = grpc_server.rsplit(':', 1)
    
    try:
        devices = bridge.list_devices()
        logger.info(f"Found {len(devices)} devices, starting streams...")
        logger.info(f"Devices: {devices}")
        
        for device in devices:
            # Handle both dict and list formats
            if isinstance(device, dict):
                device_id = device.get('device_id')
            elif isinstance(device, list) and len(device) > 0:
                device_id = device[0] if isinstance(device[0], str) else device[0].get('device_id')
            else:
                device_id = str(device)
                
            if device_id:
                client = SiLA2StreamClient(host, int(port), device_id, buffer)
                client.start_streaming()
                logger.info(f"Started streaming for device: {device_id}")
                
    except Exception as e:
        logger.error(f"Failed to start device streams: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Start device streams before starting server
    start_device_streams()
    
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)
