# Clinical Ops Assistant — AI-Powered Veeva Vault Clinical Access

## Overview

The Clinical Ops Assistant is an AI agent that provides natural language access to your Veeva Vault Clinical environment (CTMS and eTMF). Clinical operations teams can ask questions in plain English and get instant answers with direct links back to Vault — no VQL expertise or Vault UI navigation required.

## Problem Statement

Clinical operations teams spend significant time navigating Vault to answer routine questions:
- "Which of my Phase 3 studies are actively enrolling?"
- "Is site 042 on track for their next milestone?"
- "Where's the latest investigator brochure for study X?"

These queries require knowing where to look in Vault, how to filter, and often involve cross-referencing multiple objects (studies → sites → milestones → documents). The Clinical Ops Assistant eliminates this friction.

## Capabilities (v1)

| Capability | What you can ask | What you get back |
|-----------|-----------------|-------------------|
| **Study Portfolio** | "What active phase 3 studies do I have?" | Study list with status, phase, therapeutic area, sponsor + Vault links |
| **Study Details** | "Tell me about study BMS-986365-001" | Full metadata: indication, enrollment (planned vs actual), start date |
| **Site Performance** | "Which sites in Germany are below 50% enrollment?" | Site list with enrollment metrics, PI name, status |
| **Milestone Tracking** | "Show me milestones for study X" | Timeline with planned vs actual dates, status (on track / delayed) |
| **Document Search** | "Find the latest investigator brochure for study X" | Document metadata, version, last modified date + Vault deep link |
| **Document Details** | "Get me details on document 12345" | Full document metadata with study association |

Every response includes a **Vault deep link** — click to open the record directly in your Vault UI.

## Example Conversations

**Clinical Operations Manager:**
> "What's the enrollment status across my oncology portfolio?"

→ Returns all oncology studies with planned vs actual enrollment, highlighting those below target.

**Clinical Trial Manager:**
> "Which milestones for ONCO-2025 are overdue?"

→ Returns milestones where actual_date is blank and planned_date has passed.

**Regulatory/TMF Coordinator:**
> "Find all protocol amendments for study BMS-986365-001"

→ Searches eTMF for documents of type "Protocol Amendment" associated with that study.

**VP Clinical Operations:**
> "How many active studies do we have by therapeutic area?"

→ Aggregated study counts grouped by therapeutic area and phase.

## Architecture

```
Clinical Ops Team
       │
       ▼
  AI Agent (Claude Sonnet)
       │
       ▼
  Veeva Vault REST API (v26.1)
       │
       ▼
  Your Vault Clinical Environment
  (CTMS + eTMF)
```

**Key design principles:**
- **Read-only** — The agent cannot create, update, or delete anything in Vault
- **No PHI** — No subject-level data is returned (aggregate metrics only)
- **Secure** — Vault credentials stored in AWS Secrets Manager, sessions cached with TTL
- **Auditable** — All queries logged in CloudWatch (credentials redacted)
- **Your data stays in your Vault** — The agent queries on demand; no data is copied or stored

## Security & Compliance

| Concern | How it's addressed |
|---------|-------------------|
| Data access | Read-only service account; no write permissions in Vault |
| PHI exposure | No subject-level fields returned; aggregate metrics only |
| Credentials | AWS Secrets Manager with encryption at rest |
| Session management | DynamoDB cache with 15-min TTL; auto-refresh on expiry |
| Audit trail | CloudWatch logs for all agent invocations |
| GxP / 21 CFR Part 11 | Write operations intentionally excluded from v1 |
| Network | HTTPS only; no VPC required (public Vault API endpoint) |

## What We Need From You

To configure the agent for your environment:

| Item | Description | Example |
|------|-------------|---------|
| Vault URL | Your Vault subdomain | `https://yourcompany.veevavault.com` |
| Service account | Read-only API user credentials | Username + password for `svc_bedrock` |
| Object confirmation | Confirm standard vs custom object names | `study__v`, `study_site__v`, `milestone__v` |
| Sample study names | 2-3 study names for testing | Used to validate queries work correctly |
| Therapeutic areas | List of values used in your Vault | For filtering validation |

## Proposed Enhancements (v2+)

Based on common clinical operations workflows, these are candidates for future iterations:

| Enhancement | Description | Priority |
|-------------|-------------|----------|
| **Enrollment forecasting** | "At current rate, when will study X hit target?" | High |
| **Site risk scoring** | Flag sites at risk of missing milestones based on trends | High |
| **Cross-study comparison** | "Compare enrollment rates across my oncology portfolio" | Medium |
| **Protocol deviation summary** | "Sites with >3 deviations this quarter" | Medium |
| **Document expiry alerts** | "Which IBs need update in the next 30 days?" | Medium |
| **Country-level rollup** | "Enrollment by country for study X" | Medium |
| **Investigator workload** | "Which PIs are running >3 active studies?" | Low |
| **Write operations** | Update site status, add milestones (requires GxP review) | Future |

## Questions for Your Team

1. **Which workflows matter most?** — Are there specific questions your team asks daily that we should prioritize?
2. **Custom objects/fields** — Does your Vault have custom objects beyond the standard CTMS model?
3. **Access scope** — Should the agent see all studies, or be restricted to specific therapeutic areas/programs?
4. **Users** — Who would use this? CTMs only, or broader (medical monitors, regulatory, leadership)?
5. **Integration** — Would you want this accessible via Slack, Teams, a web UI, or AWS console only?
6. **Enrollment data** — Do you track enrollment at the site level in Vault, or in a separate system (e.g., IXRS)?

## Timeline

| Phase | Scope | Duration |
|-------|-------|----------|
| **Configuration** | Vault URL, credentials, object name confirmation | 1-2 days |
| **Deployment** | Deploy agent to your AWS account | 1 day |
| **Validation** | Test with real study names, iterate on prompts | 2-3 days |
| **Pilot** | 3-5 users testing for 2 weeks | 2 weeks |
| **Feedback → v2** | Prioritize enhancements based on pilot feedback | Ongoing |

## Next Steps

1. Review this document — does it cover the right capabilities?
2. Confirm the "Questions for Your Team" section
3. Provide Vault configuration details
4. We deploy and validate together
