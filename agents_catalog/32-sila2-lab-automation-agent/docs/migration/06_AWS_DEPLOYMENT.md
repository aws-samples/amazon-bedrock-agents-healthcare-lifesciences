# AWS Deployment (Optional - Future Use)

**Status**: Optional  
**When**: After local testing complete, if AWS deployment needed

---

## Prerequisites

- AWS CLI configured
- AWS account with appropriate permissions
- ECR repositories created
- VPC and networking configured

---

## Scripts Status

### ✅ No Changes Required

All 4 deployment scripts work without modification:

```bash
scripts/
├── 01_setup_ecr_and_build.sh    # ✅ Works as-is
├── 02_package_lambdas.sh        # ✅ Works as-is
├── 03_deploy_stack.sh           # ✅ Works as-is
└── 04_deploy_agentcore.sh       # ✅ Works as-is
```

**Why**: Scripts build containers from Dockerfiles and requirements.txt. Since we only update requirements.txt (add sila2), the build process automatically includes the new dependencies.

---

## Deployment Process

```bash
cd scripts

# 1. Build & push containers
./01_setup_ecr_and_build.sh
# Builds with updated requirements.txt containing sila2>=0.14.0

# 2. Package Lambdas
./02_package_lambdas.sh
# No changes needed

# 3. Deploy stack
./03_deploy_stack.sh
# ECS pulls new images automatically

# 4. Deploy AgentCore
./04_deploy_agentcore.sh
# No changes needed
```

---

## What Gets Updated Automatically

### Container Images
- **Bridge**: Built with `src/bridge/requirements.txt` (includes sila2>=0.14.0)
- **Devices**: Built with `src/devices/requirements.txt` (includes sila2>=0.14.0, sila2[codegen])

### ECS Task Definitions
- Automatically updated with new image tags
- No manual changes needed

### Infrastructure
- CloudFormation templates unchanged
- Networking unchanged
- Security groups unchanged

---

## Validation

```bash
# Check ECR images
aws ecr describe-images --repository-name sila2-bridge --region us-west-2
aws ecr describe-images --repository-name sila2-mock-devices --region us-west-2

# Check ECS services
aws ecs describe-services \
  --cluster sila2-bridge-dev \
  --services sila2-bridge-dev sila2-mock-devices-dev \
  --region us-west-2

# Check logs
aws logs tail /ecs/sila2-bridge-dev --follow --region us-west-2
aws logs tail /ecs/sila2-mock-devices-dev --follow --region us-west-2
```

---

## Rollback

If deployment fails:

```bash
# List previous revisions
aws ecs describe-task-definition \
  --task-definition sila2-bridge-dev \
  --region us-west-2

# Rollback to previous revision
aws ecs update-service \
  --cluster sila2-bridge-dev \
  --service sila2-bridge-dev \
  --task-definition sila2-bridge-dev:PREVIOUS_REVISION \
  --region us-west-2
```

---

## Summary

**No script modifications needed**. The existing deployment scripts automatically:
1. Read updated requirements.txt
2. Build containers with sila2 library
3. Push to ECR
4. Deploy to ECS

The migration is transparent to the deployment process.
