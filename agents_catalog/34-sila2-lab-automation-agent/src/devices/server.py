#!/usr/bin/env python3
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'generated'))
from lab_devices.server import Server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    server = Server()
    
    logger.info("Starting SiLA2 Lab Device Server on port 50051")
    server.start_insecure(address='0.0.0.0', port=50051, enable_discovery=False)
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        server.stop()

if __name__ == '__main__':
    asyncio.run(main())
