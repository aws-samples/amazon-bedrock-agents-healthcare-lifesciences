# Phase 3: Device Implementation (12 hours)

**Objective**: Implement SiLA2 Server with Feature implementations

---

## Tasks

1. Update requirements.txt (5min)
2. Create feature implementations (8h)
3. Rewrite server.py (3h)
4. Local testing (1h)

---

## Step 1: Update Requirements

Edit `src/devices/requirements.txt`:

```toml
sila2>=0.14.0
sila2[codegen]
```

Install:
```bash
cd src/devices
pip install -r requirements.txt
```

---

## Step 2: Feature Implementations

Create `src/devices/feature_implementations/` directory:

```bash
mkdir -p src/devices/feature_implementations
```

### 2.1 TemperatureController Implementation

Create `src/devices/feature_implementations/temperaturecontroller_impl.py`:

```python
from generated.temperaturecontroller import TemperatureControllerFeature
from temperature_controller import TemperatureController
import asyncio
from uuid import uuid4

class TemperatureControllerImpl(TemperatureControllerFeature):
    def __init__(self, server):
        super().__init__(server)
        self.controller = TemperatureController()
        self.tasks = {}
    
    async def SetTemperature(self, TargetTemperature, metadata):
        """Unobservable command with intermediate responses"""
        task_id = str(uuid4())
        
        # Start async task
        task = asyncio.create_task(
            self.controller.set_temperature(TargetTemperature)
        )
        self.tasks[task_id] = task
        
        # Yield progress updates
        while not task.done():
            status = self.controller.get_status()
            yield {
                'CurrentTemperature': status['current_temp'],
                'PercentComplete': status['progress'],
                'ElapsedSeconds': status['elapsed']
            }
            await asyncio.sleep(0.5)
        
        # Return final result
        result = await task
        
        # Cleanup completed task
        self.tasks.pop(task_id, None)
        
        return {
            'FinalTemperature': result['final_temp'],
            'TotalDuration': result['duration'],
            'Success': result['success']
        }
    
    async def AbortExperiment(self, metadata):
        self.controller.abort()
        return {}
    
    async def Get_CurrentTemperature(self, metadata):
        return self.controller.current_temperature
    
    async def Subscribe_CurrentTemperature(self, metadata):
        while True:
            yield self.controller.current_temperature
            await asyncio.sleep(0.5)
    
    async def Get_TargetTemperature(self, metadata):
        return self.controller.target_temperature
    
    async def Subscribe_TargetTemperature(self, metadata):
        while True:
            yield self.controller.target_temperature
            await asyncio.sleep(1.0)
    
    async def Get_HeatingStatus(self, metadata):
        status = self.controller.get_status()
        return {
            'IsHeating': status['is_heating'],
            'ElapsedSeconds': status['elapsed'],
            'ScenarioMode': status['mode']
        }
    
    async def Subscribe_HeatingStatus(self, metadata):
        while True:
            status = self.controller.get_status()
            yield {
                'IsHeating': status['is_heating'],
                'ElapsedSeconds': status['elapsed'],
                'ScenarioMode': status['mode']
            }
            await asyncio.sleep(0.5)
```

### 2.2 DeviceManagement Implementation

Create `src/devices/feature_implementations/devicemanagement_impl.py`:

```python
from generated.devicemanagement import DeviceManagementFeature

class DeviceManagementImpl(DeviceManagementFeature):
    def __init__(self, server):
        super().__init__(server)
        self.devices = {
            'hplc': {'name': 'HPLC System', 'status': 'ready'},
            'gc': {'name': 'Gas Chromatograph', 'status': 'ready'},
            'lcms': {'name': 'LC-MS System', 'status': 'ready'}
        }
    
    async def ListDevices(self, metadata):
        return list(self.devices.keys())
    
    async def GetDeviceInfo(self, DeviceId, metadata):
        if DeviceId in self.devices:
            return str(self.devices[DeviceId])
        return f"Device {DeviceId} not found"
    
    async def GetDeviceStatus(self, DeviceId, metadata):
        if DeviceId in self.devices:
            return self.devices[DeviceId]['status']
        return "unknown"
```

### 2.3 TaskManagement Implementation

Create `src/devices/feature_implementations/taskmanagement_impl.py`:

```python
from generated.taskmanagement import TaskManagementFeature

class TaskManagementImpl(TaskManagementFeature):
    def __init__(self, server):
        super().__init__(server)
        self.tasks = {}
    
    async def GetTaskStatus(self, TaskId, metadata):
        if TaskId in self.tasks:
            return self.tasks[TaskId]['status']
        return "unknown"
    
    async def GetTaskInfo(self, TaskId, metadata):
        if TaskId in self.tasks:
            return str(self.tasks[TaskId])
        return f"Task {TaskId} not found"
```

---

## Step 3: Rewrite Server

Replace `src/devices/server.py`:

```python
from sila2.server import SilaServer
from uuid import uuid4
import asyncio
import logging

from feature_implementations.temperaturecontroller_impl import TemperatureControllerImpl
from feature_implementations.devicemanagement_impl import DeviceManagementImpl
from feature_implementations.taskmanagement_impl import TaskManagementImpl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LabDeviceServer(SilaServer):
    def __init__(self):
        super().__init__(
            server_name="LabDevice",
            server_type="LabAutomation",
            server_version="1.0",
            server_uuid=uuid4(),
            server_description="SiLA2 Lab Automation Device"
        )
        
        # Register features
        self.temp_controller = TemperatureControllerImpl(self)
        self.device_mgmt = DeviceManagementImpl(self)
        self.task_mgmt = TaskManagementImpl(self)
        
        logger.info("LabDeviceServer initialized")

async def main():
    server = LabDeviceServer()
    
    logger.info("Starting SiLA2 server on port 50051")
    await server.start(port=50051)
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down server")
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Step 4: Local Testing

```bash
cd src/devices

# Start server
python server.py

# Expected output:
# INFO:__main__:LabDeviceServer initialized
# INFO:__main__:Starting SiLA2 server on port 50051
# INFO:sila2.server:Server started on [::]:50051
```

Test from another terminal:

```bash
# Install sila2 client
pip install sila2>=0.14.0

# Test connection
python -c "
from sila2.client import SilaClient
client = SilaClient('localhost', 50051)
print('Connected:', client.server_name)
"
```

---

## Validation

```bash
# Check implementations exist
test -f src/devices/feature_implementations/temperaturecontroller_impl.py && echo "✓ TemperatureController impl"
test -f src/devices/feature_implementations/devicemanagement_impl.py && echo "✓ DeviceManagement impl"
test -f src/devices/feature_implementations/taskmanagement_impl.py && echo "✓ TaskManagement impl"

# Check server.py updated
grep -q "SilaServer" src/devices/server.py && echo "✓ server.py uses SilaServer"

# Check requirements.txt updated
grep -q "sila2" src/devices/requirements.txt && echo "✓ requirements.txt has sila2"
```

---

## Next Step

→ [Phase 4: Bridge](04_BRIDGE.md)
