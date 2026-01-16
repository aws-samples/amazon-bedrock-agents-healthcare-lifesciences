# Quick Reference: File Operations

This document provides quick commands for file reorganization tasks.

## Files to Move

### 1. main_agentcore.py → agentcore/main.py

```bash
# Move file
mv main_agentcore.py agentcore/main.py

# Update reference in deployment script
sed -i 's|main_agentcore.py|agentcore/main.py|g' scripts/04_deploy_agentcore.sh

# Update any documentation references
grep -r "main_agentcore.py" docs/ README.md
```

### 2. test_integration.py → tests/test_integration.py

```bash
# Create tests directory
mkdir -p tests

# Move file
mv test_integration.py tests/

# Update any references
grep -r "test_integration.py" docs/ README.md scripts/
```

### 3. Optional: Development files to dev/

```bash
# Create dev directory
mkdir -p dev

# Move development files (if needed)
mv docker-compose.yml dev/ 2>/dev/null || true
mv .python-version dev/ 2>/dev/null || true
```

## Files to Delete

### Internal Development Documents

```bash
# Delete phase reports
rm -f docs/phase1_completion_report.md
rm -f docs/phase2_completion_report.md
rm -f docs/phase3_completion_report.md
rm -f docs/phase4_completion_report.md

# Delete planning documents
rm -f docs/CLEANUP_PLAN.md
rm -f docs/TASK_GROUP_0_SUMMARY.md
rm -f docs/NAMING_REFACTORING_COMPLETE_PLAN.md

# Delete technical notes
rm -f docs/BUGFIX_MEMORY_DISPLAY.md
rm -f docs/IMPACT_ANALYSIS.md
rm -f docs/RESOURCE_INVENTORY.md
rm -f docs/SAFE_EXECUTION_GUIDE.md
rm -f docs/GRPC_STATUS_REPORT.md
rm -f docs/ALB_ADOPTION_DECISION.md
rm -f docs/ALB_VS_SERVICE_DISCOVERY.md
rm -f docs/DEPLOYMENT_VALIDATION.md
```

### One-liner to delete all internal docs

```bash
cd docs/
rm -f CLEANUP_PLAN.md \
      phase*_completion_report.md \
      TASK_GROUP_0_SUMMARY.md \
      NAMING_REFACTORING_COMPLETE_PLAN.md \
      BUGFIX_MEMORY_DISPLAY.md \
      IMPACT_ANALYSIS.md \
      RESOURCE_INVENTORY.md \
      SAFE_EXECUTION_GUIDE.md \
      GRPC_STATUS_REPORT.md \
      ALB_ADOPTION_DECISION.md \
      ALB_VS_SERVICE_DISCOVERY.md \
      DEPLOYMENT_VALIDATION.md
cd ..
```

## Files to Review

### Root Directory Files

```bash
# List all root files for review
ls -la | grep -v "^d" | grep -v "^total"

# Files to consider:
# - Dockerfile (keep if needed for local dev)
# - docker-compose.yml (move to dev/ or keep)
# - .python-version (delete - personal config)
# - run_streamlit.sh (keep - useful for users)
# - requirements.txt (keep - needed)
```

## Script Path Updates

### Replace hardcoded AWS CLI paths

```bash
# Find all hardcoded paths
grep -r "/usr/local/bin/aws" scripts/

# Replace in all scripts
find scripts/ -type f -name "*.sh" -exec sed -i 's|/usr/local/bin/aws|aws|g' {} +

# Verify changes
grep -r "/usr/local/bin/aws" scripts/
```

## Verification Commands

### After moving files

```bash
# Verify main.py moved correctly
test -f agentcore/main.py && echo "✓ main.py moved" || echo "✗ main.py not found"

# Verify tests directory created
test -d tests && echo "✓ tests/ directory exists" || echo "✗ tests/ not found"

# Verify internal docs deleted
! test -f docs/CLEANUP_PLAN.md && echo "✓ Internal docs deleted" || echo "✗ Some docs remain"

# Check for Japanese text in public files
grep -r "日本語\|です\|ます\|した" README.md scripts/*.sh agentcore/*.txt 2>/dev/null && \
  echo "⚠ Japanese text found" || echo "✓ No Japanese text in critical files"
```

## Backup Before Changes

```bash
# Create backup of current state
cd ..
tar -czf 32-sila2-lab-automation-agent-backup-$(date +%Y%m%d).tar.gz \
  32-sila2-lab-automation-agent/

# Verify backup
ls -lh 32-sila2-lab-automation-agent-backup-*.tar.gz
```

## Restore from Backup (if needed)

```bash
# Extract backup
cd ..
tar -xzf 32-sila2-lab-automation-agent-backup-YYYYMMDD.tar.gz

# Or restore specific files
tar -xzf 32-sila2-lab-automation-agent-backup-YYYYMMDD.tar.gz \
  32-sila2-lab-automation-agent/main_agentcore.py
```

## Complete Reorganization Script

```bash
#!/bin/bash
# Run this script from the agent root directory

set -e

echo "=== Starting File Reorganization ==="

# 1. Create backup
echo "Creating backup..."
cd ..
tar -czf 32-sila2-lab-automation-agent-backup-$(date +%Y%m%d).tar.gz \
  32-sila2-lab-automation-agent/
cd 32-sila2-lab-automation-agent

# 2. Move files
echo "Moving files..."
mv main_agentcore.py agentcore/main.py
mkdir -p tests
mv test_integration.py tests/ 2>/dev/null || true

# 3. Update references
echo "Updating references..."
sed -i 's|main_agentcore.py|agentcore/main.py|g' scripts/04_deploy_agentcore.sh

# 4. Delete internal docs
echo "Deleting internal documents..."
cd docs/
rm -f CLEANUP_PLAN.md \
      phase*_completion_report.md \
      TASK_GROUP_0_SUMMARY.md \
      NAMING_REFACTORING_COMPLETE_PLAN.md \
      BUGFIX_MEMORY_DISPLAY.md \
      IMPACT_ANALYSIS.md \
      RESOURCE_INVENTORY.md \
      SAFE_EXECUTION_GUIDE.md \
      GRPC_STATUS_REPORT.md \
      ALB_ADOPTION_DECISION.md \
      ALB_VS_SERVICE_DISCOVERY.md \
      DEPLOYMENT_VALIDATION.md
cd ..

# 5. Fix hardcoded paths
echo "Fixing hardcoded paths..."
find scripts/ -type f -name "*.sh" -exec sed -i 's|/usr/local/bin/aws|aws|g' {} +

# 6. Verify
echo "Verifying changes..."
test -f agentcore/main.py && echo "✓ main.py moved" || echo "✗ main.py not found"
test -d tests && echo "✓ tests/ directory exists" || echo "✗ tests/ not found"
! test -f docs/CLEANUP_PLAN.md && echo "✓ Internal docs deleted" || echo "✗ Some docs remain"

echo "=== Reorganization Complete ==="
echo "Backup saved as: ../32-sila2-lab-automation-agent-backup-$(date +%Y%m%d).tar.gz"
```

## Notes

- Always create a backup before making changes
- Test deployment after file moves
- Update all documentation references
- Verify git status before committing

---

Last Updated: 2025-01-XX
