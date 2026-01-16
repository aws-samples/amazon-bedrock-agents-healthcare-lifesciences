# Phase 1: Cleanup (30 minutes)

**Objective**: Remove custom gRPC implementation

---

## Files to Delete

```bash
src/proto/                    # All custom .proto files
src/devices/proto/            # Device-side proto
src/bridge/proto/             # Bridge-side proto
src/bridge/grpc_client.py     # Custom gRPC client
```

---

## Execution

```bash
cd agents_catalog/32-sila2-lab-automation-agent

# Delete custom proto implementations
rm -rf src/proto/
rm -rf src/devices/proto/
rm -rf src/bridge/proto/
rm src/bridge/grpc_client.py

# Verify deletion
ls src/proto/ 2>/dev/null && echo "ERROR: proto/ still exists" || echo "✓ proto/ deleted"
ls src/devices/proto/ 2>/dev/null && echo "ERROR: devices/proto/ still exists" || echo "✓ devices/proto/ deleted"
ls src/bridge/proto/ 2>/dev/null && echo "ERROR: bridge/proto/ still exists" || echo "✓ bridge/proto/ deleted"
ls src/bridge/grpc_client.py 2>/dev/null && echo "ERROR: grpc_client.py still exists" || echo "✓ grpc_client.py deleted"

# Commit
git add -A
git commit -m "chore: remove custom gRPC for SiLA2 migration"
```

---

## Validation

```bash
# Verify kept files
test -f src/devices/temperature_controller.py && echo "✓ temperature_controller.py exists"
test -f src/bridge/mcp_server.py && echo "✓ mcp_server.py exists"
test -f src/devices/server.py && echo "✓ server.py exists"
```

---

## Next Step

→ [Phase 2: Features](02_FEATURES.md)
