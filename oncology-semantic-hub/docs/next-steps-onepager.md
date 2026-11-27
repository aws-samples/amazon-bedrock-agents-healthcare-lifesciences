# One-Pager — Positioning A1 & A2: Strategic Next Steps (7-day alignment sprint)

**Objective:** In **7 working days**, align our two oncology accelerators with the team's parallel
semantic-layer streams, confirm their differentiated roles, and produce a shared collaboration plan — so we
can move to field-ready without duplicating effort. Detail: `accelerator-positioning.md`.

## Positioning in one line
- **A1 = KG + L3 semantic-layer constructs + BYOD onboarding** (RODA open data *and* customer cohorts); TCGA is the reference, not the value.
- **A2 = the measurement module** of the semantic layer (today: *attempt-and-attribute*; governance/gating → CI-gate is a next step) — proves value + flags context-poisoning; **our grounding is a superset of Bedrock Contextual Grounding** (tool-provenance across lake/graph/OLS/KB/RODA, tier-aware, no KB/Gateway dependency).

## The 7-day alignment sprint (live tracker)

| Day | Activity | Owner | Status |
|---|---|---|---|
| 1 | Circulate `accelerator-positioning.md` + this one-pager + exec summary to Lisa & Indradeep | Hasan | ☐ |
| 1–2 | **Indradeep sync** — define A1 per semantic-hub architecture/patterns (#20) | Hasan + Indradeep | ☐ |
| 2–3 | **Stan sync** — observability/governance integration; grounding-metric alignment (#18) | Hasan + Stan | ☐ |
| 3–4 | **Chaitanya sync** — learn benchmark-app scope; identify merge vs complement | Hasan + Chaitanya | ☐ |
| 3–4 | **Ariella & Michael sync** — learn framework scope; position A2 as measurement module | Hasan + A/M | ☐ |
| 4–5 | **Nadeem sync** — bioinformatics-workflow skill + RODA + graduated automation (#19) | Hasan + Nadeem | ☐ |
| 6 | **Group meeting** — consolidate into one framework; assign owners; resolve overlaps | All | ☐ |
| 7 | Update positioning + backlog with agreed integration plan; publish decision | Hasan | ☐ |

## Outreach snippets (copy-paste)
- **Indradeep:** "Following our accelerator discussion — can we grab 30 min this week to anchor A1 to the semantic-layer architecture/patterns you're shaping, so it's positioned as a reference implementation rather than a one-off hub?"
- **Stan:** "Your observability/governance work and our benchmark grounding look complementary — ours is a superset of Bedrock Contextual Grounding (tool-provenance across lake/graph/OLS/KB, tier-aware, no KB/Gateway dependency). Can we sync 30 min to align the grounding metric across dev + runtime and scope the gating roadmap?"
- **Chaitanya:** "I hear you've built a benchmarking app — we've built one too (tier-ladder + provenance metrics for semantic-hub value). Can we compare notes for 30 min so we converge on one tool rather than two?"
- **Ariella & Michael:** "I'd like to understand the full evaluation framework you're putting together — we have a semantic-hub-value benchmark (correctness/reproducibility/grounding) that may fit as a measurement module. 30 min to explore where it plugs in?"
- **Nadeem:** "Picking up your graduated-automation idea — want to scope a RODA → HealthOmics bioinformatics-workflow skill with step-by-step human-in-the-loop? Happy to have you drive hands-on; can we sync + get you into the channel?"

## Individual-meeting TODOs (objective + key question)
- [ ] **Indradeep** — anchor A1 to the enterprise semantic-layer construct (federated / governance / quality / CI-CD). *Q: what patterns must A1 conform to as the reference implementation?*
- [ ] **Stan** — align our grounding (superset) with his Bedrock Contextual Grounding runtime guardrail. *Q: how do dev-time benchmark (ours) + runtime guardrail (his) compose; can our tool-provenance grounding become the shared definition beyond KB-literature?* Note his current scope: KB-only, literature-only, Gateway-dependent.
- [ ] **Chaitanya** — understand existing benchmarking app. *Q: merge harnesses or complement? what does his measure that ours doesn't (and vice versa)?*
- [ ] **Ariella & Michael** — understand the "full framework." *Q: where does A2 (tier ladder + provenance-faithfulness + context-poisoning) plug in as the measurement module?*
- [ ] **Nadeem** — scope the workflow skill + RODA + graduated HITL. *Q: what will he build hands-on; which of #2/#11/#17/#19 does he own?*

## Group-meeting TODOs
- [ ] Confirm the single cohesive framework (A1 reference impl + A2 measurement + Stan observability + Chaitanya/A-M streams).
- [ ] Resolve benchmarking overlap (one harness).
- [ ] Assign owners per module + a shared Slack channel (Nadeem requested access).
- [ ] Agree publish scope + timeline.

## Deliverables by Day 7
1. Confirmed positioning (A1/A2 roles) endorsed by Lisa & Indradeep.
2. Integration map with real scope for Chaitanya + Ariella/Michael (replaces placeholders).
3. Owner assignments + shared channel.
4. Updated `accelerator-positioning.md` + `backlog.md` priorities.
