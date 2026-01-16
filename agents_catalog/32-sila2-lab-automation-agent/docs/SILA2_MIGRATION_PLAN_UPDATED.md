# SiLA2 Standard Migration Implementation Plan

**Status**: Draft  
**Created**: 2025-01-XX  
**Estimated Effort**: 32.5 hours (4-5 days)

---

## Executive Summary

This plan outlines the migration from custom gRPC implementation to SiLA2 standard compliance using the official `sila2` Python library. The approach uses **Feature-based MCP Tools** with a **simple bridge pattern** for maximum maintainability.

### Design Decision

**Approach B: MCP Tools aligned with SiLA2 Features**
- MCP Tools map 1:1 to SiLA2 Commands (manual definition)
- Bridge performs simple pass-through (no device-specific logic)
- Device additions require minimal bridge changes

---

## Implementation Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| **Phase 0: Cleanup** | **0.5h** | **0.5h** |
| Phase 1: Feature Definition | 5h | 5.5h |
| Phase 2: Device Implementation | 14h | 19.5h |
| Phase 3: Bridge Implementation | 7h | 26.5h |
| Phase 4: Integration Testing | 4h | 30.5h |
| **Phase 5: AWS Deployment** | **2h** | **32.5h** |
| **Total** | **32.5 hours** | **(4-5 days)** |

---

## Phase 0: Cleanup (30 minutes)

### Objective
Remove custom gRPC implementation files to avoid confusion during migration.

### Files to Delete

```bash
# Custom Protocol Buffers
src/proto/                          # All custom .proto files
├── sila2_basic.proto
├── sila2_streaming.proto
├── sila2_tasks.proto
└── *_pb2*.py                       # Generated Python files

src/devices/proto/                  # Device-side proto
└── (all files)

src/bridge/proto/                   # Bridge-side proto
└── (all files)

src/bridge/grpc_client.py          # Custom gRPC client
```

### Files to Keep

```bash
# Business Logic (Reuse)
src/devices/temperature_controller.py
src/devices/Dockerfile
src/devices/requirements.txt        # Will be updated
src/devices/README.md

# Bridge Components (Reuse/Update)
src/bridge/mcp_server.py           # Will be updated
src/bridge/main.py
src/bridge/api.py
src/bridge/event_handler.py
src/bridge/data_buffer.py
src/bridge/stream_client.py        # May need updates
src/bridge/Dockerfile
src/bridge/requirements.txt         # Will be updated
src/bridge/README.md

# Infrastructure (No changes)
infrastructure/                     # All files
scripts/                            # All files
streamlit_app/                      # All files
agentcore/                          # All files
```

### Cleanup Commands

```bash
cd /path/to/32-sila2-lab-automation-agent

# Delete custom proto implementations
rm -rf src/proto/
rm -rf src/devices/proto/
rm -rf src/bridge/proto/
rm src/bridge/grpc_client.py

# Verify deletion
git status

# Commit cleanup
git add -A
git commit -m "chore: remove custom gRPC implementation for SiLA2 migration"
```

### Validation

```bash
# Verify deleted files
ls src/proto/          # Should not exist
ls src/devices/proto/  # Should not exist
ls src/bridge/proto/   # Should not exist
ls src/bridge/grpc_client.py  # Should not exist

# Verify kept files
ls src/devices/temperature_controller.py  # Should exist
ls src/bridge/mcp_server.py               # Should exist
```

---

## Phase 1-4: Implementation

[Previous Phase 1-4 content remains the same...]

---

## Phase 5: AWS Deployment (2 hours)

### Objective
Deploy SiLA2-compliant containers to AWS using existing infrastructure.

### Infrastructure Reuse

**✅ No Changes Required**:
- ECR repositories (sila2-bridge, sila2-mock-devices)
- ECS Cluster & Fargate configuration
- Task Definitions (auto-updated with new images)
- Service Discovery (sila2.local namespace)
- Security Groups & Networking
- CloudFormation templates
- **All 4 deployment scripts**

**🔄 Updates Required**:
- Container images (rebuilt with sila2 library)
- requirements.txt (both containers)

### Deployment Process

Use existing scripts without modification:

```bash
cd scripts

# Step 1: Build & push containers to ECR
./01_setup_ecr_and_build.sh
# - Creates ECR repositories (if not exists)
# - Builds bridge container with updated requirements.txt
# - Builds mock devices container with updated requirements.txt
# - Pushes both images to ECR

# Step 2: Package Lambda functions
./02_package_lambdas.sh
# - No changes needed for Lambda functions

# Step 3: Deploy infrastructure stack
./03_deploy_stack.sh
# - Deploys/updates CloudFormation stack
# - ECS services automatically pull new images
# - Task definitions updated with new image tags

# Step 4: Deploy AgentCore Runtime
./04_deploy_agentcore.sh
# - Deploys AgentCore components
# - No changes needed
```

### Container Build Process

**Bridge Container** (`src/bridge/Dockerfile`):
- No Dockerfile changes needed
- requirements.txt updated with `sila2>=0.14.0`
- Build process unchanged

**Mock Devices Container** (`src/devices/Dockerfile`):
- No Dockerfile changes needed
- requirements.txt updated with `sila2>=0.14.0` and `sila2[codegen]`
- Build process unchanged

### Deployment Validation

```bash
# 1. Verify ECR images
aws ecr describe-images \
  --repository-name sila2-bridge \
  --region us-west-2

aws ecr describe-images \
  --repository-name sila2-mock-devices \
  --region us-west-2

# 2. Verify ECS services
aws ecs describe-services \
  --cluster sila2-bridge-dev \
  --services sila2-bridge-dev sila2-mock-devices-dev \
  --region us-west-2

# 3. Check task status
aws ecs list-tasks \
  --cluster sila2-bridge-dev \
  --region us-west-2

# 4. Monitor container logs
aws logs tail /ecs/sila2-bridge-dev --follow --region us-west-2
aws logs tail /ecs/sila2-mock-devices-dev --follow --region us-west-2

# 5. Test MCP endpoint (via ALB or Service Discovery)
curl http://bridge.sila2.local:8080/health

# 6. Test Streamlit UI
# Access via CloudFormation output URL
```

### Rollback Plan

If issues occur, rollback to previous container images:

```bash
# List previous task definition revisions
aws ecs describe-task-definition \
  --task-definition sila2-bridge-dev \
  --region us-west-2

# Rollback bridge service
aws ecs update-service \
  --cluster sila2-bridge-dev \
  --service sila2-bridge-dev \
  --task-definition sila2-bridge-dev:PREVIOUS_REVISION \
  --region us-west-2

# Rollback mock devices service
aws ecs update-service \
  --cluster sila2-bridge-dev \
  --service sila2-mock-devices-dev \
  --task-definition sila2-mock-devices-dev:PREVIOUS_REVISION \
  --region us-west-2
```

### Post-Deployment Testing

```bash
# 1. Test device listing
curl -X POST http://bridge.sila2.local:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"method":"tools/call","params":{"name":"list_devices","arguments":{}}}'

# 2. Test temperature setting
curl -X POST http://bridge.sila2.local:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"method":"tools/call","params":{"name":"set_temperature","arguments":{"device_id":"hplc","target_temperature":80}}}'

# 3. Test temperature subscription (via Streamlit UI)
# Open Streamlit UI and verify real-time temperature updates

# 4. Test AI Agent integration
# Invoke AgentCore Runtime and verify device control
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] Phase 0-4 completed and tested locally
- [ ] Docker builds successful locally
- [ ] requirements.txt updated in both containers
- [ ] All tests passing
- [ ] Git branch created and committed

### Deployment
- [ ] Run `./01_setup_ecr_and_build.sh` successfully
- [ ] Verify ECR images pushed
- [ ] Run `./02_package_lambdas.sh` successfully
- [ ] Run `./03_deploy_stack.sh` successfully
- [ ] Verify CloudFormation stack updated
- [ ] Run `./04_deploy_agentcore.sh` successfully

### Post-Deployment
- [ ] ECS services running (2/2 tasks)
- [ ] Container logs show no errors
- [ ] MCP endpoint responding
- [ ] Streamlit UI accessible
- [ ] Device listing works
- [ ] Temperature control works
- [ ] Real-time streaming works
- [ ] AI Agent integration works

### Rollback (if needed)
- [ ] Previous task definitions identified
- [ ] Rollback commands prepared
- [ ] Rollback tested

---

## File Changes Summary

### New Files
```
src/devices/features/
├── TemperatureController.sila.xml
├── DeviceManagement.sila.xml
└── TaskManagement.sila.xml

src/devices/feature_implementations/
├── temperaturecontroller_impl.py
├── devicemanagement_impl.py
└── taskmanagement_impl.py

src/devices/generated/
└── (auto-generated by sila2-codegen)

src/bridge/sila2_bridge.py
```

### Modified Files
```
src/devices/server.py              # Complete rewrite with SilaServer
src/devices/requirements.txt       # Add sila2>=0.14.0, sila2[codegen]
src/bridge/mcp_server.py          # Update tool definitions
src/bridge/requirements.txt        # Add sila2>=0.14.0
```

### Deleted Files (Phase 0)
```
src/proto/                         # All custom .proto files
src/devices/proto/                 # All files
src/bridge/proto/                  # All files
src/bridge/grpc_client.py         # Custom gRPC client
```

---

## Dependencies

### Device Container
```toml
# src/devices/requirements.txt
sila2>=0.14.0
sila2[codegen]
```

### Bridge Container
```toml
# src/bridge/requirements.txt
sila2>=0.14.0
fastapi==0.115.0
uvicorn==0.34.2
```

---

## Success Criteria

- ✅ All 3 SiLA2 Features implemented
- ✅ Unobservable Commands with Intermediate Responses working
- ✅ Observable Properties streaming in real-time
- ✅ Bridge performs simple pass-through
- ✅ All 10 MCP tools functional
- ✅ Streamlit UI works without changes
- ✅ AI Agent can control devices
- ✅ Deployed to AWS successfully
- ✅ No breaking changes to external interfaces

---

## Risk Mitigation

### Risk 1: Breaking Changes
**Mitigation**: Git branch for migration, easy rollback

### Risk 2: Performance Degradation
**Mitigation**: Benchmark before/after, monitor CloudWatch metrics

### Risk 3: Integration Issues
**Mitigation**: Incremental testing at each phase

### Risk 4: Deployment Failures
**Mitigation**: Existing infrastructure reused, rollback plan ready

---

## Next Steps

1. ✅ Review and approve this plan
2. ✅ Create Git branch: `git checkout -b sila2-migration`
3. ▶️ Execute Phase 0: Cleanup
4. ▶️ Execute Phase 1-4: Implementation
5. ▶️ Execute Phase 5: AWS Deployment
6. ▶️ Validate and merge to main

---

## References

- SiLA2 Standard: https://sila-standard.com/
- sila2 Python Library: https://gitlab.com/SiLA2/sila_python
- Documentation: https://sila2.gitlab.io/sila_python/
