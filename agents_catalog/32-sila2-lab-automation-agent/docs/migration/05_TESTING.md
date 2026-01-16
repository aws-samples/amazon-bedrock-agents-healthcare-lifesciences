# Phase 5: Integration Testing (2.5 hours)

**Objective**: Validate complete SiLA2 implementation

---

## Test Scenarios

1. Docker Compose stack (30min)
2. Device communication (30min)
3. MCP tools (30min)
4. Streaming (30min)
5. End-to-end (30min)

---

## Test 1: Docker Compose Stack

Update `docker-compose.yml` if needed:

```yaml
version: '3.8'

services:
  devices:
    build:
      context: ./src/devices
    ports:
      - "50051:50051"
    environment:
      - LOG_LEVEL=INFO
    networks:
      - sila2-network

  bridge:
    build:
      context: ./src/bridge
    ports:
      - "8080:8080"
    environment:
      - DEVICE_HOST=devices
      - DEVICE_PORT=50051
    depends_on:
      - devices
    networks:
      - sila2-network

networks:
  sila2-network:
    driver: bridge
```

Start stack:

```bash
docker-compose up --build

# Expected output:
# devices_1  | INFO:__main__:Starting SiLA2 server on port 50051
# bridge_1   | INFO:__main__:Connected to SiLA2 server: LabDevice
# bridge_1   | INFO:uvicorn:Started server on 0.0.0.0:8080
```

---

## Test 2: Device Communication

```bash
# Test device listing
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

# Test device info
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_device_info",
      "arguments": {"device_id": "hplc"}
    },
    "id": 2
  }'

# Expected: {"result": "{'name': 'HPLC System', 'status': 'ready'}"}
```

---

## Test 3: MCP Tools

Test all 10 tools:

```bash
# 1. list_devices
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_devices","arguments":{}},"id":1}'

# 2. get_device_info
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_device_info","arguments":{"device_id":"hplc"}},"id":2}'

# 3. get_device_status
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_device_status","arguments":{"device_id":"hplc"}},"id":3}'

# 4. set_temperature
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"set_temperature","arguments":{"target_temperature":80}},"id":4}'

# 5. get_temperature
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_temperature","arguments":{}},"id":5}'

# 6. get_heating_status
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_heating_status","arguments":{}},"id":6}'

# 7. abort_experiment
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"abort_experiment","arguments":{}},"id":7}'

# 8. get_task_status (use command_uuid from set_temperature)
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_task_status","arguments":{"task_id":"<uuid>"}},"id":8}'

# 9. get_task_info
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_task_info","arguments":{"task_id":"<uuid>"}},"id":9}'

# 10. subscribe_temperature (streaming)
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"subscribe_temperature","arguments":{}},"id":10}'
```

---

## Test 4: Streaming

Test real-time temperature streaming:

```python
# test_streaming.py
import requests
import json
import signal
import sys

def timeout_handler(signum, frame):
    print("\n✓ Streaming test completed (timeout)")
    sys.exit(0)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)  # 10 second timeout for demo

response = requests.post(
    'http://localhost:8080/mcp',
    json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "subscribe_temperature",
            "arguments": {}
        },
        "id": 1
    },
    stream=True,
    timeout=10
)

for line in response.iter_lines():
    if line:
        data = json.loads(line)
        print(f"Temperature: {data}")
```

Run:
```bash
python test_streaming.py

# Expected: Temperature updates for ~10 seconds
# Temperature: 25.3
# Temperature: 25.4
# ✓ Streaming test completed (timeout)
```

---

## Test 5: End-to-End Scenario

Complete workflow test:

```bash
# 1. List devices
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_devices","arguments":{}},"id":1}'

# 2. Get device status
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_device_status","arguments":{"device_id":"hplc"}},"id":2}'

# 3. Get current temperature
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_temperature","arguments":{}},"id":3}'

# 4. Set temperature to 80°C
RESPONSE=$(curl -s -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"set_temperature","arguments":{"target_temperature":80}},"id":4}')
COMMAND_UUID=$(echo $RESPONSE | jq -r '.result.command_uuid')
echo "Command UUID: $COMMAND_UUID"

# 5. Monitor progress (wait 5 seconds)
sleep 5

# 6. Get heating status
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_heating_status","arguments":{}},"id":5}'

# 7. Get task status
curl -X POST http://localhost:8080/mcp -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"get_task_status\",\"arguments\":{\"task_id\":\"$COMMAND_UUID\"}},\"id\":6}"

# 8. Abort if needed
curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"abort_experiment","arguments":{}},"id":7}'
```

---

## Validation Checklist

### Infrastructure
- [ ] Docker Compose builds successfully
- [ ] Both containers start without errors
- [ ] Devices container listens on port 50051
- [ ] Bridge container listens on port 8080
- [ ] Bridge connects to devices

### MCP Tools
- [ ] list_devices returns device list
- [ ] get_device_info returns device info
- [ ] get_device_status returns status
- [ ] set_temperature starts async command
- [ ] get_temperature returns current temp
- [ ] subscribe_temperature streams updates
- [ ] get_heating_status returns status
- [ ] abort_experiment stops operation
- [ ] get_task_status returns task status
- [ ] get_task_info returns task info

### Streaming
- [ ] Temperature subscription works
- [ ] Updates arrive every 0.5s
- [ ] No connection drops
- [ ] Clean shutdown

### Error Handling
- [ ] Invalid device_id handled
- [ ] Invalid task_id handled
- [ ] Connection errors handled
- [ ] Timeout errors handled

---

## Performance Benchmarks

```bash
# Latency test
time curl -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"list_devices","arguments":{}},"id":1}'

# Expected: < 100ms

# Throughput test
for i in {1..100}; do
  curl -s -X POST http://localhost:8080/mcp -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_temperature","arguments":{}},"id":'$i'}' &
done
wait

# Expected: All requests complete successfully
```

---

## Cleanup

```bash
# Stop containers
docker-compose down

# Remove volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

---

## Success Criteria

✅ All containers start successfully  
✅ All 10 MCP tools work  
✅ Streaming works continuously  
✅ No errors in logs  
✅ Performance meets benchmarks  
✅ Error handling works correctly

---

## Migration Complete!

All phases completed. The system is now running on SiLA2 standard.

### Next Steps

1. Update documentation
2. Create deployment guide
3. Add more devices
4. Implement additional features
