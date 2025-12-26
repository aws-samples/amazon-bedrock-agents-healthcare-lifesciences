from fastapi import FastAPI, Query
from typing import Optional
from data_buffer import DataBuffer

app = FastAPI(title="SiLA2 Bridge Server API")
buffer = DataBuffer(max_minutes=5)

@app.get("/api/history/{device_id}")
async def get_device_history(
    device_id: str,
    minutes: Optional[int] = Query(5, ge=1, le=60)
):
    history = buffer.get_history(device_id=device_id, minutes=minutes)
    return {
        "device_id": device_id,
        "count": len(history),
        "minutes": minutes,
        "data": history
    }

@app.get("/api/devices")
async def list_devices():
    devices = buffer.get_devices()
    return {"count": len(devices), "devices": devices}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "buffer_size": len(buffer.buffer),
        "devices": len(buffer.get_devices())
    }
