# SiLA2 Migration Guide

Complete migration from custom gRPC to SiLA2 standard.

---

## Quick Navigation

1. **[Overview](00_OVERVIEW.md)** - Migration strategy and timeline
2. **[Phase 1: Cleanup](01_CLEANUP.md)** - Remove custom gRPC (30min)
3. **[Phase 2: Features](02_FEATURES.md)** - Define SiLA2 Features (5h)
4. **[Phase 3: Devices](03_DEVICES.md)** - Implement SiLA2 Server (12h)
5. **[Phase 4: Bridge](04_BRIDGE.md)** - Implement SiLA2 Client (6h)
6. **[Phase 5: Testing](05_TESTING.md)** - Integration validation (2.5h)

---

## Prerequisites

✅ Backup created  
✅ AWS resources deleted  
✅ Python 3.9+ installed  
✅ Docker installed  
✅ Minimum 5GB disk space  
✅ Internet connection (PyPI access)

---

## Execution Order

**IMPORTANT**: Execute phases sequentially. Do not skip phases.

```bash
# Phase 1: Cleanup (30min)
cd agents_catalog/32-sila2-lab-automation-agent
# Follow: docs/migration/01_CLEANUP.md

# Phase 2: Features (5h)
# Follow: docs/migration/02_FEATURES.md

# Phase 3: Devices (12h)
# Follow: docs/migration/03_DEVICES.md

# Phase 4: Bridge (6h)
# Follow: docs/migration/04_BRIDGE.md

# Phase 5: Testing (2.5h)
# Follow: docs/migration/05_TESTING.md
```

---

## Total Effort

**26 hours** (3-4 working days)

---

## Support

For issues during migration:
1. Check phase-specific validation steps
2. Review error logs
3. Consult SiLA2 documentation: https://sila2.gitlab.io/sila_python/

---

## Success Criteria

✅ All custom gRPC code removed  
✅ 3 SiLA2 Features implemented  
✅ 10 MCP tools functional  
✅ Real-time streaming working  
✅ Docker Compose stack operational


---

## Optional: AWS Deployment

If you need to deploy to AWS in the future:

**[Phase 6: AWS Deployment](06_AWS_DEPLOYMENT.md)** - Deploy to AWS (optional)

**Note**: No script modifications required. Existing deployment scripts work as-is because they automatically use updated requirements.txt files.
