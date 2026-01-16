# Publication Readiness Checklist

Track your progress as you prepare the SiLA2 Lab Automation Agent for publication.

## 🔴 CRITICAL - Must Complete Before Publication

### Documentation Translation

#### README.md
- [ ] Translate main description
- [ ] Translate Quick Deploy section
- [ ] Translate Architecture section
- [ ] Translate Available Tools section
- [ ] Translate Example Usage section
- [ ] Translate Prerequisites section
- [ ] Remove Phase references
- [ ] Simplify status section

#### Agent Instructions
- [ ] Translate `agentcore/agent_instructions.txt` to English
- [ ] Review and optimize instructions
- [ ] Test with English prompts

#### Deployment Guide
- [ ] Translate `scripts/DEPLOYMENT_GUIDE.md`
- [ ] Update all command examples
- [ ] Verify all steps work

#### Core Documentation
- [ ] Translate `docs/architecture.md`
- [ ] Translate `docs/deployment.md`
- [ ] Translate `docs/development.md`

### File Organization

#### Move Files
- [ ] Move `main_agentcore.py` → `agentcore/main.py`
- [ ] Update import in `scripts/04_deploy_agentcore.sh`
- [ ] Update references in documentation
- [ ] Test after move

#### Create Directories
- [ ] Create `tests/` directory
- [ ] Move `test_integration.py` → `tests/`
- [ ] Update test documentation

#### Delete Internal Documents
- [ ] `docs/CLEANUP_PLAN.md`
- [ ] `docs/phase1_completion_report.md`
- [ ] `docs/phase2_completion_report.md`
- [ ] `docs/phase3_completion_report.md`
- [ ] `docs/phase4_completion_report.md`
- [ ] `docs/TASK_GROUP_0_SUMMARY.md`
- [ ] `docs/NAMING_REFACTORING_COMPLETE_PLAN.md`
- [ ] `docs/BUGFIX_MEMORY_DISPLAY.md`
- [ ] `docs/IMPACT_ANALYSIS.md`
- [ ] `docs/RESOURCE_INVENTORY.md`
- [ ] `docs/SAFE_EXECUTION_GUIDE.md`
- [ ] `docs/GRPC_STATUS_REPORT.md`
- [ ] `docs/ALB_ADOPTION_DECISION.md`
- [ ] `docs/ALB_VS_SERVICE_DISCOVERY.md`
- [ ] `docs/DEPLOYMENT_VALIDATION.md`

### Script Localization

#### scripts/01_setup_ecr_and_build.sh
- [ ] Translate echo messages
- [ ] Translate error messages
- [ ] Translate comments

#### scripts/02_package_lambdas.sh
- [ ] Translate echo messages
- [ ] Translate error messages
- [ ] Translate comments

#### scripts/03_deploy_stack.sh
- [ ] Translate echo messages
- [ ] Translate error messages
- [ ] Translate comments

#### scripts/04_deploy_agentcore.sh
- [ ] Translate echo messages
- [ ] Translate error messages
- [ ] Translate comments
- [ ] Update path to main.py

#### scripts/destroy.sh
- [ ] Translate echo messages
- [ ] Translate error messages
- [ ] Translate comments

#### scripts/utils/*.sh
- [ ] Translate all utility scripts
- [ ] Update function documentation

---

## 🟡 RECOMMENDED - Quality Improvements

### Code Optimization

#### agentcore/main.py
- [ ] Add type hints to all functions
- [ ] Add comprehensive docstrings
- [ ] Improve error handling
- [ ] Fix fallback mode implementation
- [ ] Add logging

#### src/bridge/mcp_server.py
- [ ] Translate Japanese comments
- [ ] Add type hints
- [ ] Improve error messages

#### src/lambda/invoker/lambda_function.py
- [ ] Translate Japanese comments
- [ ] Add type hints
- [ ] Improve error handling

### Script Improvements

#### All Scripts
- [ ] Replace `/usr/local/bin/aws` with `aws`
- [ ] Add input validation
- [ ] Improve error handling
- [ ] Add usage examples

### Root Directory Cleanup

- [ ] Review `Dockerfile` - keep or delete?
- [ ] Review `docker-compose.yml` - move to dev/?
- [ ] Delete `.python-version`
- [ ] Review `run_streamlit.sh` - improve or move?

### Code Comments

#### Python Files
- [ ] `src/bridge/*.py` - translate comments
- [ ] `src/devices/*.py` - translate comments
- [ ] `src/lambda/**/*.py` - translate comments
- [ ] `streamlit_app/*.py` - translate comments

#### Shell Scripts
- [ ] All `*.sh` files - translate comments

---

## 🟢 OPTIONAL - Future Enhancements

### Testing
- [ ] Add unit tests for core functions
- [ ] Add integration tests
- [ ] Add end-to-end tests
- [ ] Document testing procedures
- [ ] Add test coverage reporting

### CI/CD
- [ ] Create `.github/workflows/test.yml`
- [ ] Create `.github/workflows/lint.yml`
- [ ] Add automated deployment
- [ ] Add security scanning

### Documentation
- [ ] Create `docs/API.md`
- [ ] Create `docs/FAQ.md`
- [ ] Create `CONTRIBUTING.md`
- [ ] Create `CHANGELOG.md`
- [ ] Add architecture diagrams

### Code Quality
- [ ] Add `.pre-commit-config.yaml`
- [ ] Add `pyproject.toml` for black/isort
- [ ] Add `.pylintrc`
- [ ] Add `mypy.ini`
- [ ] Run and fix all linting issues

---

## Verification Steps

After completing critical tasks:

### 1. Documentation Review
- [ ] All README sections are in English
- [ ] No Japanese text in public files
- [ ] All links work correctly
- [ ] Code examples are accurate

### 2. Deployment Test
- [ ] Run `01_setup_ecr_and_build.sh` successfully
- [ ] Run `02_package_lambdas.sh` successfully
- [ ] Run `03_deploy_stack.sh` successfully
- [ ] Run `04_deploy_agentcore.sh` successfully
- [ ] Verify all resources created

### 3. Functionality Test
- [ ] Test all 6 tools via AgentCore
- [ ] Test Streamlit UI
- [ ] Test Lambda Invoker
- [ ] Test Memory management
- [ ] Test autonomous control

### 4. Cleanup Test
- [ ] Run `destroy.sh` successfully
- [ ] Verify all resources deleted
- [ ] No orphaned resources remain

### 5. Code Quality
- [ ] No Japanese comments in code
- [ ] Consistent code style
- [ ] All imports work
- [ ] No hardcoded credentials

---

## Progress Tracking

### Week 1: Critical Documentation
- Start Date: ___________
- Completion Date: ___________
- Status: ⬜ Not Started / 🔄 In Progress / ✅ Complete

### Week 2: File Organization & Scripts
- Start Date: ___________
- Completion Date: ___________
- Status: ⬜ Not Started / 🔄 In Progress / ✅ Complete

### Week 3: Code Quality & Testing
- Start Date: ___________
- Completion Date: ___________
- Status: ⬜ Not Started / 🔄 In Progress / ✅ Complete

### Week 4: Final Review
- Start Date: ___________
- Completion Date: ___________
- Status: ⬜ Not Started / 🔄 In Progress / ✅ Complete

---

## Notes

Use this space to track issues, blockers, or important decisions:

```
[Date] - [Note]
Example:
2025-01-15 - Decided to keep docker-compose.yml for local development
2025-01-16 - Found issue with main.py import, needs fix
```

---

## Sign-off

Before publication, confirm:

- [ ] All critical tasks completed
- [ ] All verification steps passed
- [ ] Code reviewed by team
- [ ] Documentation reviewed
- [ ] Security review completed
- [ ] Legal review completed (if required)

**Reviewed by:** ___________
**Date:** ___________
**Approved for publication:** ⬜ Yes / ⬜ No

---

Last Updated: 2025-01-XX


---

## 🔴 CRITICAL - Environment Dependencies (Added)

### Remove Personal Environment Configurations

#### Python Path (pyenv)
- [ ] Remove `export PATH="$HOME/.pyenv/shims:$PATH"` from all scripts
- [ ] `scripts/destroy.sh` - line 3
- [ ] `scripts/01_setup_ecr_and_build.sh`
- [ ] `scripts/02_package_lambdas.sh`
- [ ] `scripts/03_deploy_stack.sh`
- [ ] `scripts/04_deploy_agentcore.sh`

#### AWS CLI Hardcoded Paths
- [ ] Replace `/usr/local/bin/aws` with `aws` in all scripts
- [ ] `scripts/destroy.sh` - multiple lines
- [ ] `scripts/01_setup_ecr_and_build.sh`
- [ ] `scripts/02_package_lambdas.sh`
- [ ] `scripts/03_deploy_stack.sh`
- [ ] `scripts/04_deploy_agentcore.sh`

#### User-Specific Paths
- [ ] Search for `/home/tetsutm` references
- [ ] Search for other hardcoded paths
- [ ] Remove or make configurable

### Add Environment Validation

#### scripts/utils/validation.sh
- [ ] Add Python version check (3.9+)
- [ ] Add AWS CLI availability check
- [ ] Add AWS CLI v2 check
- [ ] Add Docker availability check
- [ ] Add Docker daemon running check

#### Update All Scripts
- [ ] Source validation.sh in all deployment scripts
- [ ] Call validation functions before operations
- [ ] Provide helpful error messages

### Verification
- [ ] Run: `grep -r "pyenv" scripts/`
- [ ] Run: `grep -r "/usr/local/bin/" scripts/`
- [ ] Run: `grep -r "/home/tetsutm" .`
- [ ] Test on clean Amazon Linux 2023
- [ ] Test on clean Ubuntu 22.04
- [ ] Test on macOS (if applicable)
