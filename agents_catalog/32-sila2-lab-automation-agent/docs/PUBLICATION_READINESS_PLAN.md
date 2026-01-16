# Publication Readiness Plan

## Overview

This document outlines the tasks required to prepare the SiLA2 Lab Automation Agent for public release.

## Priority Levels

- 🔴 **CRITICAL**: Must be completed before publication
- 🟡 **RECOMMENDED**: Should be completed for quality
- 🟢 **OPTIONAL**: Nice to have for future improvements

---

## 🔴 CRITICAL Tasks (Must Complete)

### 1. Documentation Translation to English

#### High Priority
- [ ] `README.md` - Complete English translation
- [ ] `scripts/DEPLOYMENT_GUIDE.md` - English translation
- [ ] `agentcore/agent_instructions.txt` - English translation

#### Medium Priority
- [ ] `docs/architecture.md` - English translation
- [ ] `docs/deployment.md` - English translation
- [ ] `docs/development.md` - English translation
- [ ] Code comments in Japanese → English

### 2. File Organization

#### Move Files
- [ ] Move `main_agentcore.py` → `agentcore/main.py`
- [ ] Move `test_integration.py` → `tests/test_integration.py`
- [ ] Update all references to moved files

#### Delete Internal Development Documents
- [ ] Delete `docs/CLEANUP_PLAN.md`
- [ ] Delete `docs/phase1_completion_report.md`
- [ ] Delete `docs/phase2_completion_report.md`
- [ ] Delete `docs/phase3_completion_report.md`
- [ ] Delete `docs/phase4_completion_report.md`
- [ ] Delete `docs/TASK_GROUP_0_SUMMARY.md`
- [ ] Delete `docs/NAMING_REFACTORING_COMPLETE_PLAN.md`
- [ ] Delete `docs/BUGFIX_MEMORY_DISPLAY.md`
- [ ] Delete `docs/IMPACT_ANALYSIS.md`
- [ ] Delete `docs/RESOURCE_INVENTORY.md`
- [ ] Delete `docs/SAFE_EXECUTION_GUIDE.md`

### 3. README.md Restructuring

Create a clean, professional README with:

```markdown
# SiLA2 Lab Automation Agent

[Brief English description]

## Features
- 6 integrated tools for lab automation
- AI-powered autonomous control
- Built-in memory management
- Real-time monitoring UI

## Quick Start
[Concise deployment steps in English]

## Architecture
[Clean architecture overview]

## Documentation
- [Deployment Guide](docs/deployment.md)
- [Architecture](docs/architecture.md)
- [Development Guide](docs/development.md)
- [Troubleshooting](docs/troubleshooting.md)

## Prerequisites
[List requirements]

## License
[License information]
```

### 4. Script Localization

- [ ] Translate all error messages in `scripts/*.sh` to English
- [ ] Translate all echo statements to English
- [ ] Update comments to English

---

## 🟡 RECOMMENDED Tasks (Quality Improvements)

### 1. Code Optimization

#### `agentcore/main.py` (formerly main_agentcore.py)
- [ ] Improve fallback mode implementation
- [ ] Add comprehensive error handling
- [ ] Add type hints to all functions
- [ ] Add docstrings in English

#### Scripts
- [ ] Replace hardcoded paths `/usr/local/bin/aws` with `aws`
- [ ] Add input validation
- [ ] Improve error messages

### 2. Root Directory Cleanup

- [ ] Review and remove/move `Dockerfile` if not needed
- [ ] Move `docker-compose.yml` to `dev/` if development-only
- [ ] Remove `.python-version` (personal configuration)
- [ ] Create `tests/` directory structure

### 3. Code Comments

- [ ] Translate all Japanese comments to English
- [ ] Add missing docstrings
- [ ] Improve inline documentation

### 4. Configuration Files

- [ ] Review `.gitignore` for completeness
- [ ] Add `.dockerignore` optimization
- [ ] Document environment variables

---

## 🟢 OPTIONAL Tasks (Future Enhancements)

### 1. Testing

- [ ] Add unit tests for core functions
- [ ] Add integration tests
- [ ] Add end-to-end tests
- [ ] Document testing procedures

### 2. CI/CD

- [ ] Set up GitHub Actions workflow
- [ ] Add automated testing
- [ ] Add linting checks
- [ ] Add security scanning

### 3. Documentation

- [ ] Add API documentation
- [ ] Add troubleshooting guide
- [ ] Add FAQ section
- [ ] Add contribution guidelines

### 4. Code Quality

- [ ] Add pre-commit hooks
- [ ] Add code formatting (black, isort)
- [ ] Add linting (pylint, flake8)
- [ ] Add type checking (mypy)

---

## Recommended Folder Structure (After Cleanup)

```
32-sila2-lab-automation-agent/
├── agentcore/
│   ├── main.py                    # ← Moved from root
│   ├── agent_instructions.txt     # ← English version
│   ├── gateway_config.py
│   ├── runtime_config.py
│   └── verify_setup.py
├── docs/
│   ├── architecture.md            # ← English version
│   ├── deployment.md              # ← English version
│   ├── development.md             # ← English version
│   ├── troubleshooting.md
│   └── folder_structure.md
├── infrastructure/
│   ├── lambda/
│   ├── nested/
│   └── *.yaml
├── scripts/
│   ├── utils/
│   ├── *.sh                       # ← English messages
│   ├── DEPLOYMENT_GUIDE.md        # ← English version
│   └── README.md
├── src/
│   ├── bridge/
│   ├── devices/
│   ├── lambda/
│   └── proto/
├── streamlit_app/
│   ├── app.py
│   ├── monitoring_ui.py
│   └── requirements.txt
├── tests/                         # ← New directory
│   └── test_integration.py        # ← Moved from root
├── .gitignore
├── README.md                      # ← English version
└── requirements.txt
```

---

## Execution Order

### Phase 1: Critical Documentation (Week 1)
1. Translate README.md to English
2. Translate agent_instructions.txt to English
3. Translate DEPLOYMENT_GUIDE.md to English
4. Delete internal development documents

### Phase 2: File Organization (Week 1)
1. Move main_agentcore.py → agentcore/main.py
2. Move test_integration.py → tests/
3. Update all file references
4. Clean up root directory

### Phase 3: Script Localization (Week 2)
1. Translate all script messages to English
2. Fix hardcoded paths
3. Improve error handling

### Phase 4: Code Quality (Week 2)
1. Add type hints
2. Translate code comments
3. Add docstrings
4. Optimize implementations

### Phase 5: Final Review (Week 3)
1. Test all deployment scripts
2. Verify documentation accuracy
3. Review code quality
4. Prepare for publication

---

## Success Criteria

Before publication, ensure:

- ✅ All user-facing documentation is in English
- ✅ No Japanese text in public-facing files
- ✅ Clean folder structure
- ✅ All scripts execute successfully
- ✅ README.md is professional and clear
- ✅ No internal development documents remain
- ✅ Code follows consistent style
- ✅ All critical paths are tested

---

## Notes

- Keep internal development history in a separate branch if needed
- Consider creating a `CHANGELOG.md` for version tracking
- Add `CONTRIBUTING.md` if accepting external contributions
- Ensure all AWS resource names follow naming conventions
- Review security best practices before publication

---

## Contact

For questions about this plan, contact the development team.

Last Updated: 2025-01-XX
