---
name: clinical-protocol-drafting
description: Use when drafting clinical trial protocol sections (objectives, background, study design) grounded in ICH guidelines (E6, E8, E9) and FDA regulations (21 CFR Part 312). Generates IRB-ready protocol documents from grant documents or study synopses.
---

# Clinical Trial Protocol Drafting

## When to use this skill

- Draft protocol sections from a grant document or study synopsis
- Generate objectives, background/rationale, or study design sections
- Ensure protocol language complies with ICH E6(R2), E8(R1), E9
- Check regulatory requirements from 21 CFR Part 312 for IND protocols
- Assemble multiple sections into a cohesive protocol document

## MCP Dependencies

| MCP Server | Tool | Purpose |
|---|---|---|
| fda-ecfr | `get_cfr_section` | Retrieve 21 CFR regulatory text |
| fda-ecfr | `search_cfr` | Search across CFR titles |
| awslabs.bedrock-kb-retrieval-mcp-server | `retrieve` | Query ICH E6/E8/E9 content via Bedrock Knowledge Base |

The fda-ecfr server is in `mcp-servers/agentcore-gateway/fda-ecfr/` — deploy it first.
For ICH guidelines, set up a Bedrock Knowledge Base per `mcp-servers/agentcore-gateway/ich-guidelines/README.md` and use the existing awslabs MCP server.

## Workflow: Protocol Drafting from Grant Document

### Step 1: Objectives Section

Generate the draft Objectives section of a clinical trial protocol.

1. Extract from the grant: specific aims, primary endpoint, secondary endpoints.
2. Use `retrieve` with query "protocol objectives requirements ICH E6(R2) Section 6" to retrieve guidance on how protocol objectives should be stated.

**Output structure:**
- Primary Objective (linked to the primary endpoint)
- Secondary Objectives (linked to each secondary endpoint)
- Exploratory Objectives (if any are implied by the grant aims)

Each objective: clear, measurable, single-sentence statement following ICH conventions. Map each objective to its corresponding endpoint.

### Step 2: Background & Rationale Section

Generate the draft Background and Rationale section.

1. Extract from the grant: disease context, preliminary data (preclinical and Phase 1 results), unmet medical need, scientific rationale for the investigational agent.
2. Use `get_cfr_section` with part "312" and section "23" to retrieve 21 CFR 312.23 requirements on nonclinical and clinical background information for an IND protocol.
3. Use `retrieve` with query "protocol background section requirements ICH E6(R2) E8(R1)" to retrieve guidance.

**Output structure:**
- Disease Overview (epidemiology, molecular subtype prevalence, current standard of care)
- Unmet Medical Need (limitations of existing therapies)
- Investigational Agent Summary (mechanism of action, selectivity profile)
- Relevant Nonclinical Findings (IC50 data, selectivity over wild-type)
- Clinical Experience to Date (Phase 1 dose-escalation results, RP2D, preliminary efficacy and safety signals)
- Study Rationale (why this agent, this population, this design)

Tone: scientific, appropriate for IRB submission. Cite grant preliminary data where applicable.

### Step 3: Study Design Section

Generate the draft Study Design section.

1. Extract from the grant: study design type, randomization scheme, treatment arms, dosing, sample size, study duration, number of sites, target population.
2. Use `retrieve` with query "general study design considerations randomization ICH E8(R1)" for design guidance.
3. Use `retrieve` with query "statistical design principles sample size ICH E9" for statistical principles.
4. Use `get_cfr_section` with part "312" and section "23" for 21 CFR 312.23(a)(6) requirements on protocol design elements.

**Output structure:**
- Overall Design (phase, randomization ratio, open-label justification, multicenter)
- Treatment Arms (experimental arm with dose/schedule, control arm with regimen options)
- Study Schema (text-based visual flow: screening → randomization → treatment → follow-up)
- Randomization and Stratification (method, stratification factors if applicable)
- Sample Size Justification (statistical basis, power, expected effect size)
- Study Duration (enrollment period, treatment duration, follow-up period)

### Step 4: Assembly

Assemble all drafted sections into a single cohesive protocol document.

**Formatting:**
- Protocol title page (study title, PI, funding source, protocol version/date)
- Sequential section numbering
- Consistent formatting, tense, and terminology
- Table of Contents
- Cross-reference harmonization (objectives referenced in study design)
- Flag inconsistencies as reviewer comments

Do not alter scientific content. Only harmonize language and ensure smooth transitions.

## Conventions

- Lead with the most clinically relevant information in each section
- Use ICH-compliant terminology throughout (e.g., "investigational medicinal product" not "drug")
- Distinguish primary from secondary objectives clearly
- Include regulatory citations inline (e.g., "per 21 CFR 312.23(a)(6)")
- For VUS or uncertain data: note limitations and recommend additional review
- Never fabricate clinical data — use only what is provided in the source document
- Flag sections where the grant provides insufficient detail for protocol-level specificity

## Regulatory References

- ICH E6(R2): Good Clinical Practice, Integrated Addendum
- ICH E8(R1): General Considerations for Clinical Studies
- ICH E9: Statistical Principles for Clinical Trials
- 21 CFR Part 312: Investigational New Drug Application
- 21 CFR Part 50: Protection of Human Subjects
- 21 CFR Part 56: Institutional Review Boards
