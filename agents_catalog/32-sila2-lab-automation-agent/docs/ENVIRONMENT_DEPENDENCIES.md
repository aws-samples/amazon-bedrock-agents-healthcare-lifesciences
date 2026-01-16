# Environment Dependencies Cleanup

## Overview

This document identifies environment-specific configurations that need to be removed or made portable before publication.

## 🔴 CRITICAL: Environment-Specific Issues

### 1. Python Path Dependencies

**Current Issue:**
```bash
# In multiple scripts
export PATH="$HOME/.pyenv/shims:$PATH"
```

**Problem:** Assumes pyenv installation in user's home directory

**Solution:** Use system Python or make it optional
```bash
# Option 1: Use system Python (recommended)
# Remove the line entirely - rely on system PATH

# Option 2: Make it optional
if [ -d "$HOME/.pyenv/shims" ]; then
  export PATH="$HOME/.pyenv/shims:$PATH"
fi
```

**Files to Fix:**
- `scripts/destroy.sh` (line 3)
- `scripts/01_setup_ecr_and_build.sh`
- `scripts/02_package_lambdas.sh`
- `scripts/03_deploy_stack.sh`
- `scripts/04_deploy_agentcore.sh`

### 2. AWS CLI Path Dependencies

**Current Issue:**
```bash
/usr/local/bin/aws bedrock-agentcore-control ...
/usr/local/bin/aws cloudformation ...
/usr/local/bin/aws ecr ...
```

**Problem:** Hardcoded AWS CLI v2 installation path

**Solution:** Use PATH-based lookup
```bash
# Simply use 'aws' - let the system find it
aws bedrock-agentcore-control ...
aws cloudformation ...
aws ecr ...
```

**Files to Fix:**
- `scripts/destroy.sh` (multiple lines)
- `scripts/01_setup_ecr_and_build.sh`
- `scripts/02_package_lambdas.sh`
- `scripts/03_deploy_stack.sh`
- `scripts/04_deploy_agentcore.sh`

### 3. Docker Path Dependencies

**Check for:**
```bash
# Look for hardcoded docker paths
grep -r "/usr/local/bin/docker" scripts/
grep -r "/usr/bin/docker" scripts/
```

**Solution:** Use `docker` from PATH

## 🟡 RECOMMENDED: Portability Improvements

### 1. Python Version Requirements

**Add to scripts:**
```bash
# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.9"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,9) else 1)"; then
  echo "Error: Python 3.9+ required, found $PYTHON_VERSION"
  exit 1
fi
```

### 2. AWS CLI Version Check

**Add to scripts:**
```bash
# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
  echo "Error: AWS CLI not found. Please install: https://aws.amazon.com/cli/"
  exit 1
fi

# Check AWS CLI v2
AWS_VERSION=$(aws --version 2>&1 | cut -d/ -f2 | cut -d' ' -f1)
if [[ ! "$AWS_VERSION" =~ ^2\. ]]; then
  echo "Warning: AWS CLI v2 recommended, found v$AWS_VERSION"
fi
```

### 3. Docker Availability Check

**Add to scripts:**
```bash
# Check Docker is installed and running
if ! command -v docker &> /dev/null; then
  echo "Error: Docker not found. Please install: https://docs.docker.com/get-docker/"
  exit 1
fi

if ! docker info &> /dev/null; then
  echo "Error: Docker daemon not running. Please start Docker."
  exit 1
fi
```

## 📋 Complete Fix Script

```bash
#!/bin/bash
# Fix all environment dependencies

set -e

AGENT_DIR="/home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/32-sila2-lab-automation-agent"
cd "$AGENT_DIR"

echo "=== Fixing Environment Dependencies ==="

# 1. Remove pyenv PATH exports
echo "Removing pyenv PATH exports..."
find scripts/ -type f -name "*.sh" -exec sed -i '/export PATH=.*pyenv/d' {} +

# 2. Replace hardcoded AWS CLI paths
echo "Replacing hardcoded AWS CLI paths..."
find scripts/ -type f -name "*.sh" -exec sed -i 's|/usr/local/bin/aws|aws|g' {} +

# 3. Replace hardcoded docker paths (if any)
echo "Checking for hardcoded docker paths..."
find scripts/ -type f -name "*.sh" -exec sed -i 's|/usr/local/bin/docker|docker|g' {} +
find scripts/ -type f -name "*.sh" -exec sed -i 's|/usr/bin/docker|docker|g' {} +

# 4. Verify changes
echo "Verifying changes..."
if grep -r "pyenv" scripts/ 2>/dev/null; then
  echo "⚠ Warning: pyenv references still found"
else
  echo "✓ No pyenv references"
fi

if grep -r "/usr/local/bin/aws" scripts/ 2>/dev/null; then
  echo "⚠ Warning: Hardcoded AWS paths still found"
else
  echo "✓ No hardcoded AWS paths"
fi

echo "=== Fix Complete ==="
```

## 🔍 Verification Commands

### Find all environment-specific patterns

```bash
cd /home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/32-sila2-lab-automation-agent

# Find pyenv references
echo "=== Pyenv References ==="
grep -rn "pyenv" scripts/ 2>/dev/null || echo "None found"

# Find hardcoded paths
echo "=== Hardcoded Paths ==="
grep -rn "/usr/local/bin/" scripts/ 2>/dev/null || echo "None found"
grep -rn "/usr/bin/" scripts/ 2>/dev/null || echo "None found"

# Find HOME directory references
echo "=== HOME Directory References ==="
grep -rn "\$HOME" scripts/ 2>/dev/null | grep -v "SCRIPT_DIR" || echo "None found"

# Find user-specific paths
echo "=== User-Specific Paths ==="
grep -rn "/home/tetsutm" . 2>/dev/null || echo "None found"
```

## 📝 Files Requiring Changes

### High Priority (AWS CLI paths)

1. **scripts/destroy.sh**
   - Lines: 32, 43, 58, 67, 77, 82, 87, 92, 97, 102
   - Change: `/usr/local/bin/aws` → `aws`

2. **scripts/01_setup_ecr_and_build.sh**
   - Find and replace all AWS CLI paths

3. **scripts/02_package_lambdas.sh**
   - Find and replace all AWS CLI paths

4. **scripts/03_deploy_stack.sh**
   - Find and replace all AWS CLI paths

5. **scripts/04_deploy_agentcore.sh**
   - Find and replace all AWS CLI paths

### High Priority (Python paths)

1. **scripts/destroy.sh**
   - Line 3: Remove `export PATH="$HOME/.pyenv/shims:$PATH"`

2. **All other scripts in scripts/**
   - Remove pyenv PATH exports

### Medium Priority (Add checks)

1. **scripts/utils/validation.sh**
   - Add Python version check
   - Add AWS CLI check
   - Add Docker check

## 🎯 Recommended Script Structure

```bash
#!/bin/bash
# Standard portable script header

set -e  # Exit on error

# Get script directory (portable)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load utilities
source "${SCRIPT_DIR}/utils/common.sh"
source "${SCRIPT_DIR}/utils/validation.sh"

# Validate environment
check_python_version
check_aws_cli
check_docker

# Rest of script...
```

## 🔄 Testing After Changes

```bash
# Test on clean environment
docker run -it --rm \
  -v ~/.aws:/root/.aws \
  -v $(pwd):/workspace \
  -w /workspace \
  public.ecr.aws/amazonlinux/amazonlinux:2023 \
  bash -c "
    yum install -y aws-cli python3 docker
    cd scripts
    ./01_setup_ecr_and_build.sh
  "
```

## ✅ Success Criteria

After fixes:
- [ ] No references to `/usr/local/bin/aws`
- [ ] No references to `$HOME/.pyenv`
- [ ] No references to `/home/tetsutm`
- [ ] Scripts work with system Python
- [ ] Scripts work with AWS CLI in PATH
- [ ] Scripts work on Amazon Linux 2023
- [ ] Scripts work on Ubuntu 22.04
- [ ] Scripts work on macOS

## 📚 Additional Considerations

### 1. Document Requirements

Add to README.md:
```markdown
## Prerequisites

- Python 3.9 or higher
- AWS CLI v2
- Docker 20.10 or higher
- AWS credentials configured
- Sufficient AWS permissions
```

### 2. Add Installation Guide

Create `docs/INSTALLATION.md`:
- How to install Python
- How to install AWS CLI
- How to install Docker
- How to configure AWS credentials

### 3. Add Troubleshooting

Add to `docs/troubleshooting.md`:
- "Command not found: aws"
- "Command not found: python3"
- "Command not found: docker"

---

Last Updated: 2025-01-XX
