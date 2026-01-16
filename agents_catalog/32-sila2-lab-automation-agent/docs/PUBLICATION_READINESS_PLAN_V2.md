# Publication Readiness Plan V2 - Updated Based on Reference Agent

**Last Updated:** 2025-01-XX  
**Status:** 🔄 Updated based on agent 31 analysis

## 📊 Key Changes from V1

Based on analysis of `31-drug-label-automated-reasoning` (reference agent), the following critical changes are needed:

### 🎯 New Critical Items

1. **Adopt pyproject.toml + uv.lock pattern**
   - Replace root `requirements.txt` with `pyproject.toml`
   - Keep `requirements.txt` only in container directories
   - Use `uv sync` for dependency management

2. **Simplify folder structure**
   - Move `main_agentcore.py` → `app.py` (root level)
   - Consolidate infrastructure files
   - Remove unnecessary nesting

3. **Improve deployment scripts**
   - Add parameter validation
   - Add progress indicators
   - Improve error messages
   - Add cleanup at end

4. **Streamline documentation**
   - Single comprehensive README.md
   - Remove all internal planning docs
   - Add visual aids (architecture diagrams)

## 🔴 Critical Tasks (Updated Priority)

### 1. Dependency Management Migration ⭐ NEW
**Priority:** HIGHEST  
**Estimated Time:** 2-3 hours

**Actions:**
- [ ] Create `pyproject.toml` at root
- [ ] Generate `uv.lock` file
- [ ] Remove root `requirements.txt`
- [ ] Update deployment scripts to use `uv sync`
- [ ] Test dependency installation

**Files to modify:**
- Create: `pyproject.toml`
- Delete: `requirements.txt` (root only)
- Update: `scripts/01_setup_ecr_and_build.sh`
- Update: `scripts/04_deploy_agentcore.sh`

**Validation:**
```bash
uv sync
uv run python -c "import bedrock_agentcore; print('OK')"
```

### 2. File Structure Reorganization ⭐ UPDATED
**Priority:** HIGHEST  
**Estimated Time:** 1-2 hours

**Actions:**
- [ ] Rename `main_agentcore.py` → `app.py`
- [ ] Move `streamlit_app/app.py` → `streamlit_app/ui.py` (avoid conflict)
- [ ] Consolidate `infrastructure/nested/*.yaml` if possible
- [ ] Review and simplify `src/` structure

**Before:**
```
32-sila2-lab-automation-agent/
├── main_agentcore.py
├── requirements.txt
├── streamlit_app/
│   └── app.py
└── infrastructure/
    └── nested/
        ├── ecs.yaml
        ├── events.yaml
        ├── lambda.yaml
        └── network.yaml
```

**After:**
```
32-sila2-lab-automation-agent/
├── app.py                    # Renamed from main_agentcore.py
├── pyproject.toml            # New
├── uv.lock                   # New
├── streamlit_app/
│   └── ui.py                 # Renamed from app.py
└── infrastructure/
    ├── main.yaml
    └── nested/               # Keep if necessary
```

### 3. Deployment Script Enhancement ⭐ UPDATED
**Priority:** HIGH  
**Estimated Time:** 3-4 hours

**Reference:** `31-drug-label-automated-reasoning/scripts/deploy.sh`

**Actions:**
- [ ] Add parameter validation at start
- [ ] Add `set -e` for error handling
- [ ] Add progress indicators (echo statements)
- [ ] Add template validation before deploy
- [ ] Add cleanup at end
- [ ] Improve error messages
- [ ] Add usage examples in comments

**Template for improvement:**
```bash
#!/bin/bash
set -e

# Check parameters
if [ $# -lt 2 ]; then
    echo "Usage: $0 <project-name> <s3-bucket-name>"
    echo "Example: $0 my-project my-bucket"
    exit 1
fi

# Check prerequisites
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed"
    exit 1
fi

# Validate templates
echo "Validating CloudFormation templates..."
aws cloudformation validate-template --template-body file://infrastructure/main.yaml

# Deploy
echo "Deploying stack..."
# ... deployment commands

# Cleanup
echo "Cleaning up temporary files..."
rm -f packaged.yaml

echo "Deployment completed successfully!"
```

### 4. Documentation Consolidation ⭐ CRITICAL
**Priority:** HIGHEST  
**Estimated Time:** 4-6 hours

**Actions:**
- [ ] Rewrite README.md following reference pattern
- [ ] Add Prerequisites section
- [ ] Add Installation section with step-by-step
- [ ] Add Demo/Usage section
- [ ] Add Cleanup section
- [ ] Add architecture diagram to `static/`
- [ ] Delete ALL internal planning documents

**README.md Structure (based on reference):**
```markdown
# SiLA2 Lab Automation Agent

## Summary
[Brief description]

## Architecture
![Architecture](static/architecture.png)

## Getting Started

### Prerequisites
- AWS CLI configured
- Python 3.13+ with uv
- Docker (for local testing)

### Installation
1. Clone repository
2. Install dependencies: `uv sync`
3. Configure AWS credentials

### Deploy CloudFormation Stack
1. Create S3 bucket (optional)
2. Run deployment: `./scripts/deploy.sh <project-name> <bucket-name>`

## Demo
1. Start Streamlit: `uv run streamlit run streamlit_app/ui.py`
2. [Step-by-step demo instructions]

## Clean up
Run: `./scripts/destroy.sh <project-name> <bucket-name>`

## Architecture Details
[Technical details]

## License
MIT-0
```

### 5. Environment Dependencies Removal
**Priority:** HIGH (unchanged)  
**Estimated Time:** 2-3 hours

**Actions:** (same as V1)
- [ ] Remove pyenv references
- [ ] Remove hardcoded AWS CLI paths
- [ ] Add validation checks

### 6. Translation to English
**Priority:** HIGH (unchanged)  
**Estimated Time:** 6-8 hours

**Files to translate:**
- [ ] README.md
- [ ] agentcore/agent_instructions.txt
- [ ] scripts/DEPLOYMENT_GUIDE.md
- [ ] All script echo messages
- [ ] Code comments

## 🟡 Recommended Tasks (Updated)

### 1. Add Static Assets ⭐ NEW
**Priority:** MEDIUM  
**Estimated Time:** 2-3 hours

**Actions:**
- [ ] Create `static/` directory
- [ ] Add architecture diagram
- [ ] Add screenshots for README
- [ ] Add any icons/logos

### 2. Improve Error Handling
**Priority:** MEDIUM (unchanged)

### 3. Add Type Hints
**Priority:** MEDIUM (unchanged)

### 4. Code Comment Translation
**Priority:** MEDIUM (unchanged)

## 🟢 Optional Tasks (Unchanged)

- Unit tests
- CI/CD setup
- API documentation
- Pre-commit hooks

## 📅 Updated Execution Timeline

### Week 1: Critical Restructuring
**Days 1-2:**
- [ ] Create `pyproject.toml` and migrate dependencies
- [ ] Rename `main_agentcore.py` → `app.py`
- [ ] Test basic functionality

**Days 3-4:**
- [ ] Enhance deployment scripts
- [ ] Add parameter validation
- [ ] Test deployment in clean environment

**Days 5-7:**
- [ ] Rewrite README.md
- [ ] Create architecture diagram
- [ ] Delete internal docs

### Week 2: Translation & Polish
**Days 1-3:**
- [ ] Translate all documentation
- [ ] Translate code comments
- [ ] Translate script messages

**Days 4-5:**
- [ ] Remove environment dependencies
- [ ] Add validation checks
- [ ] Test in clean environment

**Days 6-7:**
- [ ] Final testing
- [ ] Documentation review
- [ ] Create static assets

### Week 3: Final Review
**Days 1-2:**
- [ ] Complete testing
- [ ] Security review
- [ ] Performance check

**Days 3-5:**
- [ ] Address any issues
- [ ] Final documentation pass
- [ ] Prepare for publication

## 🎯 Success Criteria (Updated)

Before publication, verify:

- ✅ Uses `pyproject.toml` + `uv.lock` (no root `requirements.txt`)
- ✅ Main entry point is `app.py` at root
- ✅ Deployment scripts have validation and error handling
- ✅ README.md follows reference pattern
- ✅ Architecture diagram included
- ✅ All internal docs deleted
- ✅ All environment dependencies removed
- ✅ All documentation in English
- ✅ Tested in clean environment
- ✅ No hardcoded paths or credentials

## 📋 Files to Delete (Updated)

### Internal Planning Documents
```
docs/phase1_completion_report.md
docs/phase2_completion_report.md
docs/phase3_completion_report.md
docs/phase4_completion_report.md
docs/CLEANUP_PLAN.md
docs/DEPLOYMENT_VALIDATION.md
docs/IMPACT_ANALYSIS.md
docs/NAMING_REFACTORING_COMPLETE_PLAN.md
docs/PUBLICATION_CHECKLIST.md
docs/PUBLICATION_READINESS_PLAN.md
docs/RESOURCE_INVENTORY.md
docs/SAFE_EXECUTION_GUIDE.md
docs/TASK_GROUP_0_SUMMARY.md
docs/GRPC_STATUS_REPORT.md
docs/BUGFIX_MEMORY_DISPLAY.md
docs/ALB_ADOPTION_DECISION.md
docs/ALB_VS_SERVICE_DISCOVERY.md
docs/ENVIRONMENT_DEPENDENCIES.md
docs/FILE_OPERATIONS_GUIDE.md
docs/INDEX.md
docs/future_optimization.md
```

### Keep These Docs (Translate to English)
```
docs/architecture.md
docs/deployment.md
docs/development.md
docs/troubleshooting.md
docs/folder_structure.md (update after restructuring)
```

## 🔄 Migration Checklist

### Phase 1: Structure (Days 1-2)
- [ ] Backup current state
- [ ] Create `pyproject.toml`
- [ ] Run `uv sync` and test
- [ ] Rename `main_agentcore.py` → `app.py`
- [ ] Update all references to new filename
- [ ] Test basic functionality

### Phase 2: Scripts (Days 3-4)
- [ ] Update `01_setup_ecr_and_build.sh`
- [ ] Update `04_deploy_agentcore.sh`
- [ ] Add validation to all scripts
- [ ] Add error handling
- [ ] Test deployment

### Phase 3: Documentation (Days 5-7)
- [ ] Create new README.md
- [ ] Create architecture diagram
- [ ] Delete internal docs
- [ ] Update remaining docs

### Phase 4: Translation (Week 2)
- [ ] Translate README.md
- [ ] Translate agent_instructions.txt
- [ ] Translate DEPLOYMENT_GUIDE.md
- [ ] Translate script messages
- [ ] Translate code comments

### Phase 5: Final (Week 3)
- [ ] Remove environment dependencies
- [ ] Final testing
- [ ] Security review
- [ ] Publication

## 📞 Quick Reference

### Key Differences from Reference Agent

| Aspect | Reference (31) | Current (32) | Action |
|--------|---------------|--------------|--------|
| Dependency mgmt | pyproject.toml | requirements.txt | Migrate |
| Main file | app.py | main_agentcore.py | Rename |
| Structure | Simple | Complex | Simplify |
| Scripts | Validated | Basic | Enhance |
| Docs | Clean | Many internal | Delete |
| README | Complete | Incomplete | Rewrite |

### Commands to Run

```bash
# 1. Create pyproject.toml
cat > pyproject.toml << 'EOF'
[project]
name = "sila2-lab-automation-agent"
version = "0.1.0"
description = "SiLA2 Lab Automation Agent with Amazon Bedrock AgentCore"
requires-python = ">=3.13"
dependencies = [
    "bedrock-agentcore>=0.1.7",
    "boto3>=1.40.45",
    "strands-agents>=1.10.0",
    "streamlit>=1.50.0",
]
EOF

# 2. Generate lock file
uv sync

# 3. Rename main file
mv main_agentcore.py app.py

# 4. Update references
grep -r "main_agentcore" . --exclude-dir=.git

# 5. Test
uv run python app.py
```

---

**Next Steps:**
1. Review this updated plan
2. Start with Phase 1 (Structure)
3. Update PUBLICATION_CHECKLIST.md with new tasks
4. Begin execution
