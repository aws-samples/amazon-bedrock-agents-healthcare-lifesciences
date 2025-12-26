# SiLA2 Agent Deployment Scripts
## Phase 4: MCP + gRPC + Phase 6 (SNS/Lambda/EventBridge)

## Script Organization

### Deployment Scripts (Sequential Order)

| # | Script | Description | Duration |
|---|--------|-------------|----------|
| 01 | `01_setup_infrastructure.sh` | ECR repositories | 2 min |
| 02 | `02_build_containers.sh` | Docker build & ECR push | 5 min |
| 03 | `03_deploy_ecs.sh` | ECS + Lambda Proxy + Phase 6 | 15 min |
| 04 | `04_create_gateway.sh` | AgentCore Gateway | 3 min |
| 05 | `05_create_mcp_target.sh` | MCP Target | 2 min |
| 06 | `06_deploy_agentcore.sh` | AgentCore Runtime | 5 min |
| 07 | `07_run_tests.sh` | Integration tests | 3 min |
| 08 | `08_setup_ui.sh` | Streamlit UI | 2 min |
| 09 | `09_cleanup_nlb.sh` | Cleanup old NLB (optional) | 2 min |

**Total**: ~39 minutes

### Phase 6 Components (Deployed in Step 3)

- **SNS Topic**: sila2-events-topic
- **Lambda Function**: sila2-agentcore-invoker
- **EventBridge Rule**: sila2-periodic-collection-dev (5 min interval)
- **VPC Integration**: Lambda in VPC for Bridge Server access

### Utility Scripts

- `deploy_all.sh` - Full automated deployment (all steps)
- `create_mcp_gateway_target.py` - MCP Target creation helper
- `delete_lambda_gateway_target.py` - Target deletion helper

### Documentation

- `DEPLOYMENT_ORDER.md` - Detailed deployment guide
- `README_GATEWAY_MIGRATION.md` - Gateway migration guide

## Quick Start

### Full Deployment
```bash
# Set environment variables
export AWS_REGION=us-east-1
export GATEWAY_ID=<your-gateway-id>

# Run all steps
./scripts/deploy_all.sh
```

### Individual Steps
```bash
# Step by step
./scripts/01_setup_infrastructure.sh
./scripts/02_deploy_mock_devices.sh
./scripts/03_build_bridge_container.sh
./scripts/04_deploy_bridge_container.sh
./scripts/05_enable_device_grpc.sh
GATEWAY_ID=<id> ./scripts/06_update_gateway_target.sh
./scripts/07_deploy_agentcore.sh
./scripts/09_setup_ui.sh
./scripts/10_run_tests.sh
```

## Architecture

```
Step 1: ECR Repositories
    ↓
Step 2: Build Containers (Bridge + Mock Device)
    ↓
Step 3: Deploy ECS + Lambda Proxy + Phase 6
    ├─ ECS Service (Bridge Server)
    ├─ Lambda Proxy (MCP)
    ├─ SNS Topic
    ├─ Lambda Invoker
    └─ EventBridge Rule (5 min)
    ↓
Step 4-5: Gateway + MCP Target
    ↓
Step 6: AgentCore Runtime
    ↓
Step 7-8: Tests + UI
```

## Archived Scripts

Phase 3 scripts moved to `archive/old-deploy-scripts/`:
- `03_setup_mcp_bridge.sh` (replaced by container)
- `04_create_device_gateway.sh` (no longer needed)
- `05_create_gateway.sh` (integrated into 07)
- `06_create_gateway_target.sh` (replaced by MCP target)
- `08_integrate_phase3.sh` (no longer needed)

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AWS_REGION | No | us-east-1 | AWS region |
| ENV_NAME | No | dev | Environment name |
| GATEWAY_ID | Yes* | - | AgentCore Gateway ID |
| STACK_NAME | No | sila2-bridge-ecs | CloudFormation stack |
| IMAGE_TAG | No | latest | Docker image tag |

*Required for step 06

## Troubleshooting

See `DEPLOYMENT_ORDER.md` for detailed troubleshooting guide.

## Rollback

```bash
# Stop ECS service
aws ecs update-service \
  --cluster sila2-bridge-dev \
  --service sila2-bridge-dev \
  --desired-count 0

# Disable gRPC
for device in hplc centrifuge pipette; do
  aws lambda update-function-configuration \
    --function-name sila2-mock-${device}-device \
    --environment "Variables={GRPC_ENABLED=false}"
done
```
