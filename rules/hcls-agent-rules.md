# HCLS Agent Rules

Global behavior guidance for AI assistants working with healthcare and life sciences content.

## Domain Awareness

- Healthcare and life sciences data is sensitive. Never include real patient identifiers (PHI) in generated code, examples, or outputs unless working with explicitly de-identified data.
- Clinical outputs are informational only. Always include appropriate disclaimers — this toolkit is not a substitute for professional medical advice, diagnosis, or treatment.
- When working with genomic variants, always reference the source annotation database and version. Interpretations change as databases are updated.
- Medical ontologies have specific versioning. When mapping terms, note the ontology version used.

## Tool Usage

- Prefer HCLS MCP tools over general web search for biomedical questions. Domain-specific tools (PubMed, Open Targets, ChEMBL) provide curated, citable data.
- When HCLS skills reference AWS MCP servers for infrastructure actions (deploying, querying, storing), use those servers rather than generating raw CLI commands.
- For deployed AgentCore Gateway tools, always authenticate with the appropriate JWT token. Never bypass authentication.

## Data Handling

- Do not store or log patient health information (PHI) in development environments.
- When generating sample data for testing, use synthetic/fictional data that is clearly marked as such.
- Clinical trial data from ClinicalTrials.gov is public. Patient-level data from clinical studies is not.
- Genomic data (VCF files, sequence data) may contain identifiable information. Treat as sensitive.

## Code Generation

- When generating agent code, follow the Strands Agents + AgentCore pattern from this repository.
- Default model: `us.anthropic.claude-sonnet-4-20250514-v1:0` (or latest available).
- Include appropriate error handling for external API calls (EBI, NCBI, ClinicalTrials.gov) — these services have rate limits and may be unavailable.
- For CloudFormation templates, include deletion policies for stateful resources (databases, S3 buckets with data).

## Compliance Awareness

- This toolkit operates under MIT-0 license with explicit disclaimer: not for clinical use without appropriate compliance review.
- HIPAA applicability depends on the customer's specific use case and data. Each customer is responsible for determining applicability and entering an AWS BAA.
- When generating deployment code, include comments noting where HIPAA-relevant configurations (encryption, audit logging, access controls) should be reviewed.
