# Phase 4: Bridge Implementation (6 hours)

**Objective**: Implement SiLA2 Client and update MCP tools

---

## Tasks

1. Update requirements.txt (5min)
2. Create sila2_bridge.py (2h)
3. Update mcp_server.py (3h)
4. Local testing (1h)

---

## Step 1: Update Requirements

Edit `src/bridge/requirements.txt`:

```toml
sila2>=0.14.0
fastapi==0.115.0
uvicorn==0.34.2
```

Install:
```bash
cd src/bridge
pip install -r requirements.txt
```

---

## Step 2: Create SiLA2 Bridge

Create `src/bridge/sila2_bridge.py`:

```python
from sila2.client import SilaClient
import logging
import time

logger = logging.getLogger(__name__)

class SiLA2Bridge:
    def __init__(self, host='devices', port=50051):
        self.host = host
        self.port = port
        self.client = None
        self._connect()
    
    def _connect(self):
        """Connect with simple retry for demo"""
        for attempt in range(3):
            try:
                self.client = SilaClient(self.host, self.port)
                logger.info(f"Connected to SiLA2 server: {self.client.server_name}")
                return
            except Exception as e:
                if attempt < 2:
                    logger.warning(f"Connection attempt {attempt+1} failed, retrying...")
                    time.sleep(2)
                else:
                    logger.error(f"Failed to connect: {e}")
                    raise
    
    def list_devices(self):
        """List all devices"""
        return self.client.DeviceManagement.ListDevices()
    
    def get_device_info(self, device_id):
        """Get device information"""
        return self.client.DeviceManagement.GetDeviceInfo(DeviceId=device_id)
    
    def get_device_status(self, device_id):
        """Get device status"""
        return self.client.DeviceManagement.GetDeviceStatus(DeviceId=device_id)
    
    def set_temperature(self, target_temperature):
        """Set temperature (returns CommandExecutionUUID)"""
        return self.client.TemperatureController.SetTemperature(
            TargetTemperature=target_temperature
        )
    
    def get_temperature_progress(self, command_uuid):
        """Get temperature setting progress (generator)"""
        return self.client.TemperatureController.SetTemperature_Info(command_uuid)
    
    def get_temperature_result(self, command_uuid):
        """Get final temperature result"""
        return self.client.TemperatureController.SetTemperature_Result(command_uuid)
    
    def get_current_temperature(self):
        """Get current temperature"""
        return self.client.TemperatureController.Get_CurrentTemperature()
    
    def subscribe_temperature(self):
        """Subscribe to temperature updates (generator)"""
        return self.client.TemperatureController.Subscribe_CurrentTemperature()
    
    def get_heating_status(self):
        """Get heating status"""
        return self.client.TemperatureController.Get_HeatingStatus()
    
    def abort_experiment(self):
        """Abort current experiment"""
        return self.client.TemperatureController.AbortExperiment()
    
    def get_task_status(self, task_id):
        """Get task status"""
        return self.client.TaskManagement.GetTaskStatus(TaskId=task_id)
    
    def get_task_info(self, task_id):
        """Get task information"""
        return self.client.TaskManagement.GetTaskInfo(TaskId=task_id)
```

---

## Step 3: Update MCP Server

Edit `src/bridge/mcp_server.py` to use SiLA2Bridge:

```python
from sila2_bridge import SiLA2Bridge
import logging

logger = logging.getLogger(__name__)

# Initialize bridge
bridge = SiLA2Bridge(host='devices', port=50051)

# MCP Tool definitions
TOOLS = [
    {
        "name": "list_devices",
        "description": "List all available lab devices",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_device_info",
        "description": "Get information about a specific device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "description": "Device identifier"}
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "get_device_status",
        "description": "Get current status of a device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "description": "Device identifier"}
            },
            "required": ["device_id"]
        }
    },
    {
        "name": "set_temperature",
        "description": "Set target temperature for a device",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_temperature": {"type": "number", "description": "Target temperature in Celsius"}
            },
            "required": ["target_temperature"]
        }
    },
    {
        "name": "get_temperature",
        "description": "Get current temperature",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "subscribe_temperature",
        "description": "Subscribe to real-time temperature updates",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_heating_status",
        "description": "Get current heating status",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "abort_experiment",
        "description": "Abort current temperature control operation",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_task_status",
        "description": "Get status of an asynchronous task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task UUID"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "get_task_info",
        "description": "Get information about a task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task UUID"}
            },
            "required": ["task_id"]
        }
    }
]

async def handle_tool_call(tool_name, arguments):
    """Handle MCP tool calls"""
    try:
        if tool_name == "list_devices":
            return bridge.list_devices()
        
        elif tool_name == "get_device_info":
            return bridge.get_device_info(arguments["device_id"])
        
        elif tool_name == "get_device_status":
            return bridge.get_device_status(arguments["device_id"])
        
        elif tool_name == "set_temperature":
            command_uuid = bridge.set_temperature(arguments["target_temperature"])
            return {"command_uuid": str(command_uuid), "status": "started"}
        
        elif tool_name == "get_temperature":
            return bridge.get_current_temperature()
        
        elif tool_name == "subscribe_temperature":
            # Return generator for streaming
            return bridge.subscribe_temperature()
        
        elif tool_name == "get_heating_status":
            return bridge.get_heating_status()
        
        elif tool_name == "abort_experiment":
            return bridge.abort_experiment()
        
        elif tool_name == "get_task_status":
            return bridge.get_task_status(arguments["task_id"])
        
        elif tool_name == "get_task_info":
            return bridge.get_task_info(arguments["task_id"])
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        raise
```

---

## Step 4: Local Testing

```bash
# Terminal 1: Start devices
cd src/devices
python server.py

# Terminal 2: Start bridge
cd src/bridge
python main.py

# Terminal 3: Test MCP tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_devices",
      "arguments": {}
    },
    "id": 1
  }'

# Expected: {"result": ["hplc", "gc", "lcms"]}

curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "set_temperature",
      "arguments": {"target_temperature": 80}
    },
    "id": 2
  }'

# Expected: {"result": {"command_uuid": "...", "status": "started"}}
```

---

## Validation

```bash
# Check bridge exists
test -f src/bridge/sila2_bridge.py && echo "✓ sila2_bridge.py created"

# Check mcp_server.py updated
grep -q "SiLA2Bridge" src/bridge/mcp_server.py && echo "✓ mcp_server.py uses SiLA2Bridge"

# Check requirements.txt updated
grep -q "sila2" src/bridge/requirements.txt && echo "✓ requirements.txt has sila2"

# Check grpc_client.py deleted
test ! -f src/bridge/grpc_client.py && echo "✓ grpc_client.py deleted"
```

---

## Next Step

→ [Phase 5: Testing](05_TESTING.md)
