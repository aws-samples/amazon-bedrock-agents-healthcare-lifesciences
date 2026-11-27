# Comprehensive Threat Model Report

**Generated**: 2026-09-14 17:40:33
**Current Phase**: 1 - Business Context Analysis
**Overall Completion**: 80.0%

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Business Context](#business-context)
3. [Classification Profiles](#classification-profiles)
4. [System Architecture](#system-architecture)
5. [Threat Actors](#threat-actors)
6. [Trust Boundaries](#trust-boundaries)
7. [Assets and Flows](#assets-and-flows)
8. [Threats](#threats)
9. [Mitigations](#mitigations)
10. [Assumptions](#assumptions)
11. [Phase Progress](#phase-progress)

## Executive Summary

Oncology Semantic Hub - an open-source (MIT-0) AWS solution accelerator that unifies cancer genomics (TCGA, cBioPortal), curated biomedical knowledge (PrimeKG), variant annotations (CIViC, ClinVar) and literature into a governed semantic layer queried by an agentic AI application. Accelerator 1 is a Strands agent on Amazon Bedrock AgentCore Runtime (Claude Sonnet 4.5) with env-gated tool tiers L0-L3 (Neptune knowledge-graph queries, Athena patient-data/variant SQL, Bedrock Knowledge Base retrieval, OLS ontology lookup via remote MCP, AWS-managed web search). Accelerator 2 is an agentic dataset-onboarding pipeline (Streamlit + LLM curation agent) that discovers AWS Registry of Open Data (RODA) datasets via a live MCP client, LLM-curates column-to-hub mappings, generates declarative transform specs, and executes ETL inside an AgentCore Code Interpreter sandbox to write additive *_staging tables. Data plane: Neptune Analytics, Athena/Glue/S3 (Lake Formation governed), Bedrock Knowledge Base. Shipped demo uses PUBLIC de-identified TCGA data (no PHI); a documented Bring-Your-Own-Data path lets customers substitute their own cohort, which may be PHI. Explicitly demonstrative - not for clinical use or production per the repo legal note.

### Key Statistics

- **Total Threats**: 20
- **Total Mitigations**: 19
- **Total Assumptions**: 9
- **System Components**: 14
- **Assets**: 9
- **Threat Actors**: 14

## Business Context

**Description**: Oncology Semantic Hub - an open-source (MIT-0) AWS solution accelerator that unifies cancer genomics (TCGA, cBioPortal), curated biomedical knowledge (PrimeKG), variant annotations (CIViC, ClinVar) and literature into a governed semantic layer queried by an agentic AI application. Accelerator 1 is a Strands agent on Amazon Bedrock AgentCore Runtime (Claude Sonnet 4.5) with env-gated tool tiers L0-L3 (Neptune knowledge-graph queries, Athena patient-data/variant SQL, Bedrock Knowledge Base retrieval, OLS ontology lookup via remote MCP, AWS-managed web search). Accelerator 2 is an agentic dataset-onboarding pipeline (Streamlit + LLM curation agent) that discovers AWS Registry of Open Data (RODA) datasets via a live MCP client, LLM-curates column-to-hub mappings, generates declarative transform specs, and executes ETL inside an AgentCore Code Interpreter sandbox to write additive *_staging tables. Data plane: Neptune Analytics, Athena/Glue/S3 (Lake Formation governed), Bedrock Knowledge Base. Shipped demo uses PUBLIC de-identified TCGA data (no PHI); a documented Bring-Your-Own-Data path lets customers substitute their own cohort, which may be PHI. Explicitly demonstrative - not for clinical use or production per the repo legal note.

### Business Features

- **Industry Sector**: Healthcare
- **Data Sensitivity**: Public
- **User Base Size**: Micro
- **Geographic Scope**: Multi-Continental / International
- **Regulatory Requirements**: HIPAA
- **System Criticality**: Medium
- **Financial Impact**: Low
- **Authentication Requirement**: Basic
- **Deployment Model**: Serverless / FaaS
- **User Base Metric**: Organizational customers
- **Revenue Band**: Enterprise
- **Data Residency**: National / Single-Country
- **Compute Location**: National / Single-Country
- **User Base Location**: Multi-Continental / International
- **Organizational HQ**: Multi-Continental / International

## Classification Profiles

### Software Profile

- **Software Type**: AI / ML System
- **Deployment Model**: Serverless / FaaS
- **Architecture Style**: Microservices
- **Platform / Runtime**: Cloud runtime
- **User Domain**: Healthcare
- **Licensing / Ownership**: Open source
- **Modern Paradigms**: Agentic AI, AI/ML, Cloud-native, Event-driven architecture
- **Description**: Agentic AI system: Strands agent on Bedrock AgentCore Runtime invoking read-only data tools plus remote MCP servers (OLS, planned oncology-hub-data) and a live RODA MCP client; LLM-driven data onboarding executing ETL in an AgentCore Code Interpreter sandbox. Untrusted external content (RODA datasets, web search, KB passages, graph/lake tool outputs) flows into the LLM context - a prompt-injection surface. Read-only guards (Cypher mutation rejection, SQL SELECT-only) provide defense-in-depth over least-privilege IAM.

### Data Asset Profiles

| ID | Name | Asset | Category | Content Types | Sensitivity | Compliance | States | Volume | Lifecycle | Business Domain | Description |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DP001 | TCGA patient cohort data (mutations/expression/CNA) | N/A | Structured Data | Non-sensitive / other, System metadata | Public | None | At rest, In transit, In use | Big data | Active | Healthcare | De-identified public TCGA somatic mutations, gene expression, copy-number in Athena/S3 (Parquet), Lake Formation governed. Queried read-only by query_patient_data. BYOD path may replace this with customer PHI cohort. |
| DP002 | Neptune knowledge graph (PrimeKG + TCGA case/sample nodes) | N/A | Structured Data | System metadata, Non-sensitive / other | Public | None | At rest, In transit, In use | Big data | Active | Healthcare | Neptune Analytics graph: PrimeKG biomedical relationships plus TCGA case/sample nodes with clinical properties (age, gender, vital_status). Queried read-only via openCypher (query_knowledge_graph). |
| DP003 | Bedrock Knowledge Base literature corpus | N/A | Unstructured Data | Non-sensitive / other | Public | None | At rest, In use | Medium | Active | Healthcare | PubMed abstracts + TCGA study descriptions vectorized in a Bedrock Knowledge Base; retrieved passages feed the LLM (knowledge_search) - untrusted-content/prompt-injection surface if corpus is poisoned. |
| DP004 | Shared Cognito M2M client secret (SSM) | N/A | Secrets and Credentials | Authentication credentials | Restricted | None | At rest, In transit, In use | Small | Active | Engineering | Single shared Cognito machine-to-machine OAuth client_id/secret used to mint JWTs for the OLS (and planned data) MCP endpoints. Stored in SSM as a PLAINTEXT String (not SecureString) per per-user-auth-design.md - anyone with ssm:GetParameter can mint a token. |
| DP005 | RODA open-data datasets (untrusted external) | N/A | Semi-Structured Data | Non-sensitive / other | Public | None | In transit, In use | Big data | Active | Healthcare | Third-party AWS Registry of Open Data datasets discovered via the live RODA MCP client and ingested (schema, samples, content) into the LLM curation agent and the Code Interpreter ETL sandbox. Untrusted content - prompt-injection and malicious-data surface. |
| DP006 | BYOD customer cohort (latent PHI) | N/A | Structured Data | PHI, PII | Restricted | HIPAA | At rest, In transit, In use | Big data | Quarantined | Healthcare | Latent asset: the documented Bring-Your-Own-Data path lets a customer swap TCGA for their own patient cohort, which may contain PHI. Not present in the shipped demo but a first-class risk for production deployments (single shared IAM role, no per-user scoping). |
| DP007 | Agent answers, prompts and provenance telemetry | N/A | API Data | Operational / telemetry data | Internal | None | In transit, In use | Medium | Active | Healthcare | User prompts, tool inputs/outputs, agent answers with inline provenance tags, and CloudWatch/EMF grounding metrics emitted for observability. Basis for faithfulness/grounding scoring. |

### User Personas

| ID | Persona | Name | Privilege | Affiliation | Roles | Intent | Entity Type | Authentication | Threat Actor Overlay | In Scope | Description |
|---|---|---|---|---|---|---|---|---|---|---|---|
| UP001 | Authenticated Standard User | Researcher / clinician-scientist | Low | Customer | End User | Legitimate | Human | OAuth | N/A | Yes | Oncology researcher querying the hub in natural language via Amazon Quick / chat UI / MCP client. Untrusted prompt source. |
| UP002 | Developer / DevOps User | Hub deployer / data engineer | Elevated | Customer | Developer, Operator | Legitimate | Human | IAM Role | N/A | Yes | Deploys the agent + MCP servers via deploy.py, runs the data pipeline, drives the Streamlit onboarding UI. Holds AWS credentials with IAM/Lake Formation/Bedrock permissions. |
| UP003 | Non-Human Identity / Service Account | AgentCore runtime execution role | Elevated | Customer | Service Account | Legitimate | Non-Human | IAM Role | N/A | Yes | The single IAM execution role the AgentCore Runtime assumes to reach Neptune/Athena/Glue/S3/SSM/Bedrock (Resource:*). Also the Code Interpreter scoped role (agentcore-onboarding-ci-role). No per-user scoping. |
| UP004 | Anonymous / Unauthenticated User | Internet actor (PUBLIC network endpoints) | None | Public / Unknown | End User | Malicious | Human | None | N/A | Yes | The AgentCore runtimes are networkMode PUBLIC. If the CUSTOM_JWT authorizer is missing/misconfigured (design explicitly warns against shipping unauthenticated), an internet actor can reach the MCP/agent endpoints. |
| UP005 | External Service / Third-Party Integration | External content/data sources (RODA, OLS, web, PubMed) | None | Vendor | Integration Endpoint | Compromised | External System | None | N/A | Yes | AWS Registry of Open Data datasets, OLS MCP server, AWS-managed web search, PubMed corpus. Their content flows into the LLM context and the ETL sandbox; treated as untrusted (prompt-injection / data-poisoning source). |
| UP006 | Support / Operator User | Dataset onboarding operator | Elevated | Customer | Operator | Legitimate | Human | IAM Role | N/A | Yes | Operates the agentic onboarding pipeline: selects RODA datasets, reviews LLM-curated mappings/specs (HITL), applies additive staging tables via the Code Interpreter sandbox. |

### Non-Functional Requirements

- **Faultlessness**: High — Provenance faithfulness / grounding is the core value proposition; fabricated citations or ungrounded oncology claims are the primary quality risk.
- **Availability**: 99% — Demonstrative accelerator; no production SLA.
- **Scalability**: Elastic — Serverless AgentCore Runtime scales per-session microVMs.
- **Interoperability**: Standards-based — MCP (Model Context Protocol) over HTTPS+JWT; boto3 to AWS services.
- **Safety Criticality**: Non-safety-related — Repo legal note: not for clinical use, not a substitute for medical advice; research/demo only. Accuracy risk captured under Faultlessness.
- **Testability**: High — Unit tests for guards/queries/schema plus an 84-question benchmark and provenance-faithfulness scorers.

## System Architecture

### Components

| ID | Name | Type | Service Provider | Description |
|---|---|---|---|---|
| C001 | Semantic Hub Agent (AgentCore Runtime) | Serverless | AWS | Single-file Strands agent (semantic_hub_agent.py), env-gated tool tiers L0-L3. Entry point invoke(); reuses per-session Agent objects in an in-memory _SESSIONS dict in the warm container. networkMode PUBLIC. |
| C002 | Claude Sonnet 4.5 (Bedrock model) | Serverless | AWS | Foundation model backing the agent and the onboarding curation/NL/text-to-SQL calls. temperature 0.0. |
| C003 | OLS MCP Server (remote) | Serverless | AWS | Remote EBI Ontology Lookup Service MCP server; separate component. CUSTOM_JWT (Cognito M2M) authorizer. Agent calls search_terms over streamable-http with Bearer token. |
| C004 | oncology-hub-data MCP Server (planned) | Serverless | AWS | Planned remote MCP server exposing 4 read-only tools (graph/lake/variant/schema) over HTTPS+JWT, reusing OLS Cognito. In-process read-only guards. networkMode PUBLIC. |
| C005 | AWS-managed Web Search (AgentCore Gateway) | Serverless | AWS | L0-web tool: web_search calls the AWS-managed Web Search Tool via AgentCore Gateway (us-east-1) using an OAuth client-credentials token. Returns untrusted web content into the LLM context. |
| C006 | Cognito User Pool (M2M auth) | Security | AWS | Machine-to-machine OAuth2 client_credentials pool (shared with OLS). Issues short-lived JWTs validated by the CUSTOM_JWT authorizer. Single shared app-client; no per-user identity. |
| C007 | SSM Parameter Store | Security | AWS | Holds OLS/data MCP config + Cognito client_id/secret and KB id. Secret stored as plaintext String (not SecureString) per current-state design. |
| C008 | Dataset Onboarding UI (Streamlit) | Compute | On-Premise | 5-stage onboarding UI (discover->align->plan->execute->wire). Human-in-the-loop review of LLM-curated mappings and transform specs before apply. |
| C009 | Onboarding Curation Agent (orchestration) | Compute | AWS | LLM-backed: curate_mapping (columns->hub constructs), generate_transform_spec (declarative), nl_answer, and guarded text-to-SQL (answer_question/answer_hub: SELECT-only + write-keyword reject + table allowlist + LIMIT). Ingests untrusted RODA samples. |
| C010 | AgentCore Code Interpreter sandbox | Serverless | AWS | Runs the FIXED dynamic.py ETL harness (LLM supplies only a validated declarative spec, not code). Scoped role agentcore-onboarding-ci-role. networkMode PUBLIC. Reads arbitrary public RODA S3, writes additive *_staging Parquet + Glue tables. |
| C011 | RODA MCP client (uvx subprocess) | Other | Other | Live discovery client spawned as a uvx subprocess; searches the AWS Registry of Open Data (search_datasets/preview_dataset/sample_dataset). Returns untrusted third-party dataset metadata/content. |
| C012 | Athena query engine | Analytics | AWS | Executes read-only SQL (SELECT/WITH/SHOW/DESCRIBE/EXPLAIN) against the Lake Formation-governed lake databases; results to an S3 athena-results prefix. |
| C013 | Glue Data Catalog + Lake Formation | Security | AWS | Table metadata + fine-grained governance. Runtime role granted DESCRIBE/SELECT via best-effort Lake Formation grants at deploy time. |
| C014 | Observability (CloudWatch/X-Ray) | Analytics | AWS | OpenTelemetry traces/spans, EMF/PutMetricData grounding metrics, agent logs. Prompts and answers may appear in traces/logs. |

### Connections

| ID | Source | Destination | Protocol | Port | Encrypted | Description |
|---|---|---|---|---|---|---|
| CN001 | Semantic Hub Agent (AgentCore Runtime) (C001) | Claude Sonnet 4.5 (Bedrock model) (C002) | HTTPS | N/A | Yes | Agent invokes Claude Sonnet 4.5 (streaming) for reasoning + tool selection. |
| CN002 | Semantic Hub Agent (AgentCore Runtime) (C001) | Athena query engine (C012) | HTTPS | N/A | Yes | query_patient_data / query_variant_annotation / query_primekg -> Athena (SQL passes require_select guard). |
| CN003 | Athena query engine (C012) | TCGA patient data lake (S3/Athena oncology_semantic_hub) (D002) | HTTPS | N/A | Yes | Athena reads TCGA patient lake (Lake Formation governed). |
| CN004 | Athena query engine (C012) | RODA/staging DB (S3/Athena oncology_semantic_hub_roda) (D003) | HTTPS | N/A | Yes | Athena reads RODA/staging DB. |
| CN005 | Athena query engine (C012) | Raw flat PrimeKG DB (S3/Athena oncology_semantic_hub_raw) (D004) | HTTPS | N/A | Yes | Athena reads raw flat PrimeKG (L2). |
| CN006 | Athena query engine (C012) | Athena query-results S3 prefix (D007) | HTTPS | N/A | Yes | Athena writes query results to the athena-results S3 prefix. |
| CN007 | Semantic Hub Agent (AgentCore Runtime) (C001) | Neptune Analytics knowledge graph (D001) | HTTPS | N/A | Yes | query_knowledge_graph -> Neptune openCypher (read; passes reject_mutations guard). |
| CN008 | Semantic Hub Agent (AgentCore Runtime) (C001) | Bedrock Knowledge Base vector store (D005) | HTTPS | N/A | Yes | knowledge_search -> Bedrock Knowledge Base retrieve; passages returned into LLM context. |
| CN009 | Semantic Hub Agent (AgentCore Runtime) (C001) | SSM Parameter Store (C007) | HTTPS | N/A | Yes | Agent reads SSM params (OLS/KB config + Cognito client_id/secret). |
| CN010 | Semantic Hub Agent (AgentCore Runtime) (C001) | Cognito User Pool (M2M auth) (C006) | HTTPS | N/A | Yes | Agent mints a Cognito M2M JWT (client_credentials) to call the OLS MCP server. |
| CN011 | Semantic Hub Agent (AgentCore Runtime) (C001) | OLS MCP Server (remote) (C003) | HTTPS | N/A | Yes | ontology_lookup -> OLS MCP server (streamable-http, Bearer JWT); returns external content into LLM context. |
| CN012 | Semantic Hub Agent (AgentCore Runtime) (C001) | AWS-managed Web Search (AgentCore Gateway) (C005) | HTTPS | N/A | Yes | web_search -> AWS-managed Web Search via AgentCore Gateway (L0-web); untrusted web content into LLM context. |
| CN013 | Semantic Hub Agent (AgentCore Runtime) (C001) | Glue Data Catalog + Lake Formation (C013) | HTTPS | N/A | Yes | get_hub_schema live introspection: Glue GetDatabases/GetTables + Neptune GetGraphSummary. |
| CN014 | Semantic Hub Agent (AgentCore Runtime) (C001) | Observability (CloudWatch/X-Ray) (C014) | HTTPS | N/A | Yes | OTel traces/spans + EMF/PutMetricData grounding metrics; prompts/answers may appear in logs/traces. |
| CN015 | OLS MCP Server (remote) (C003) | Cognito User Pool (M2M auth) (C006) | HTTPS | N/A | Yes | OLS MCP server validates the inbound JWT against the Cognito issuer (CUSTOM_JWT authorizer). |
| CN016 | oncology-hub-data MCP Server (planned) (C004) | Neptune Analytics knowledge graph (D001) | HTTPS | N/A | Yes | Planned data MCP server: query_knowledge_graph -> Neptune (read-only guarded). |
| CN017 | oncology-hub-data MCP Server (planned) (C004) | Athena query engine (C012) | HTTPS | N/A | Yes | Planned data MCP server: query_patient_data/variant -> Athena (read-only guarded). |
| CN018 | Dataset Onboarding UI (Streamlit) (C008) | Onboarding Curation Agent (orchestration) (C009) | HTTPS | N/A | Yes | Streamlit UI drives the onboarding curation agent through the 5 stages (HITL review). |
| CN019 | Onboarding Curation Agent (orchestration) (C009) | Claude Sonnet 4.5 (Bedrock model) (C002) | HTTPS | N/A | Yes | Curation agent calls Bedrock Converse for mapping, transform-spec generation, NL answers, text-to-SQL. |
| CN020 | Onboarding Curation Agent (orchestration) (C009) | RODA MCP client (uvx subprocess) (C011) | Other | N/A | No | Onboarding discovery via the live RODA MCP client (uvx stdio subprocess). |
| CN021 | RODA MCP client (uvx subprocess) (C011) | External RODA public S3 buckets (D006) | HTTPS | N/A | Yes | RODA MCP client searches/previews/samples third-party public open-data S3 buckets (anonymous). |
| CN022 | Onboarding Curation Agent (orchestration) (C009) | AgentCore Code Interpreter sandbox (C010) | HTTPS | N/A | Yes | Curation agent invokes the Code Interpreter sandbox to run the fixed ETL harness (executeCode). |
| CN023 | AgentCore Code Interpreter sandbox (C010) | External RODA public S3 buckets (D006) | HTTPS | N/A | Yes | ETL sandbox reads source data from arbitrary public RODA S3 buckets (UNSIGNED/anonymous). |
| CN024 | AgentCore Code Interpreter sandbox (C010) | RODA/staging DB (S3/Athena oncology_semantic_hub_roda) (D003) | HTTPS | N/A | Yes | ETL sandbox writes additive *_staging Parquet to S3 and registers Glue tables (additive only). |
| CN025 | AgentCore Code Interpreter sandbox (C010) | Glue Data Catalog + Lake Formation (C013) | HTTPS | N/A | Yes | ETL sandbox creates/replaces Glue tables for the new staging dataset. |
| CN026 | Onboarding Curation Agent (orchestration) (C009) | Athena query engine (C012) | HTTPS | N/A | Yes | Onboarding text-to-SQL (answer_question/answer_hub) runs generated SELECTs against staging via Athena. |
| CN027 | Onboarding Curation Agent (orchestration) (C009) | Semantic Hub Agent (AgentCore Runtime) (C001) | HTTPS | N/A | Yes | onboard_runner.ask_l3 invokes the live deployed L3 agent runtime to answer over the augmented hub. |

### Data Stores

| ID | Name | Type | Classification | Encrypted at Rest | Description |
|---|---|---|---|---|---|
| D001 | Neptune Analytics knowledge graph | Graph | Public | Yes | Neptune Analytics graph: PrimeKG relationships + TCGA case/sample nodes (clinical properties). Read via openCypher. BYOD could load enterprise KG. |
| D002 | TCGA patient data lake (S3/Athena oncology_semantic_hub) | Object Storage | Public | Yes | TCGA patient data lake (Parquet on S3, database oncology_semantic_hub): tcga_mutations/expression/copy-number. Lake Formation governed. BYOD may hold PHI. |
| D003 | RODA/staging DB (S3/Athena oncology_semantic_hub_roda) | Object Storage | Public | Yes | RODA variant-annotation + onboarded additive *_staging tables (database oncology_semantic_hub_roda) on S3. Written by the onboarding ETL sandbox. |
| D004 | Raw flat PrimeKG DB (S3/Athena oncology_semantic_hub_raw) | Object Storage | Public | Yes | Flat PrimeKG for the L2 baseline (database oncology_semantic_hub_raw) on S3. |
| D005 | Bedrock Knowledge Base vector store | Other | Public | Yes | Bedrock Knowledge Base vector store over PubMed abstracts + TCGA study descriptions. Passages retrieved into LLM context (knowledge_search). |
| D006 | External RODA public S3 buckets | Object Storage | Public | Yes | Third-party public S3 buckets on the AWS Registry of Open Data (e.g. civic-aws-opendata, genoxus-annotation-release) read anonymously (UNSIGNED) by the ETL sandbox. Untrusted external source. |
| D007 | Athena query-results S3 prefix | Object Storage | Internal | Yes | S3 athena-results/ prefix holding query outputs (read/write by the runtime role). |

## Threat Actors

### Insider

- **Type**: Insider Threat
- **Motivations**: Financial gain, Revenge / grievance
- **Resources**: Individual
- **Relationship to Target**: Internal
- **Sophistication Tier**: Tier 2 - Hacktivist / campaign-driven
- **State Nexus**: None
- **Targeting Specificity**: Targeted
- **Relevant**: Yes
- **Priority**: 6/10
- **Description**: Deployer/operator/data-engineer with legitimate broad AWS access to Bedrock/Neptune/Athena/Glue/SSM and the onboarding pipeline.

### External Attacker

- **Type**: External Attacker
- **Motivations**: Financial gain
- **Resources**: Club / small group
- **Relationship to Target**: External
- **Sophistication Tier**: Tier 1 - Opportunistic / script kiddie
- **State Nexus**: None
- **Targeting Specificity**: Opportunistic
- **Relevant**: Yes
- **Priority**: 3/10
- **Description**: External individual/group reaching the PUBLIC AgentCore endpoints; primary conventional external threat given networkMode PUBLIC + shared M2M auth.

### Nation-state Actor

- **Type**: Nation-State / APT
- **Motivations**: Espionage / intelligence collection
- **Resources**: Government
- **Relationship to Target**: External
- **Sophistication Tier**: Tier 5 - Nation-state APT / elite
- **State Nexus**: State-executed
- **Targeting Specificity**: Targeted
- **Relevant**: Yes
- **Description**: Genomics/health research can draw state espionage interest, but low likelihood against the public-data demo; relevant mainly for BYOD production.

### Hacktivist

- **Type**: Hacktivist
- **Motivations**: Ideological / hacktivism
- **Resources**: Contest / crowd
- **Relationship to Target**: External
- **Sophistication Tier**: Tier 2 - Hacktivist / campaign-driven
- **State Nexus**: None
- **Targeting Specificity**: Sector-focused
- **Relevant**: Yes
- **Priority**: 9/10
- **Description**: Healthcare is a sector-focused hacktivist target; could aim to discredit or deface a research tool.

### Organized Crime

- **Type**: Financially Motivated Cybercriminal / Organized Crime
- **Motivations**: Financial gain
- **Resources**: Organization
- **Relationship to Target**: External
- **Sophistication Tier**: Tier 3 - Organized cybercrime
- **State Nexus**: None
- **Targeting Specificity**: Opportunistic
- **Relevant**: Yes
- **Priority**: 8/10
- **Description**: Financially motivated; low value against public TCGA, but material for BYOD/PHI production deployments (exfiltration/ransomware of a patient cohort).

### Competitor

- **Type**: Competitor / Corporate Espionage
- **Motivations**: Competitive advantage, Espionage / intelligence collection
- **Resources**: Organization
- **Relationship to Target**: External
- **Sophistication Tier**: Tier 3 - Organized cybercrime
- **State Nexus**: None
- **Targeting Specificity**: Targeted
- **Relevant**: Yes
- **Description**: Low: data is public and the value proposition is a methodology; limited IP to steal in the shipped demo.

### Script Kiddie

- **Type**: Script Kiddie / Novice
- **Motivations**: Thrill-seeking / notoriety
- **Resources**: Individual
- **Relationship to Target**: External
- **Sophistication Tier**: Tier 1 - Opportunistic / script kiddie
- **State Nexus**: None
- **Targeting Specificity**: Opportunistic
- **Relevant**: Yes
- **Priority**: 7/10
- **Description**: Opportunistic scanning of the internet-exposed AgentCore endpoints; low sophistication but relevant due to PUBLIC exposure.

### Disgruntled Employee

- **Type**: Disgruntled Employee
- **Motivations**: Revenge / grievance
- **Resources**: Individual
- **Relationship to Target**: Internal
- **Sophistication Tier**: Tier 1 - Opportunistic / script kiddie
- **State Nexus**: None
- **Targeting Specificity**: Targeted
- **Relevant**: Yes
- **Priority**: 10/10
- **Description**: Former deployer/operator retaining knowledge of the shared M2M secret / SSM params or role access.

### Privileged User

- **Type**: Privileged User
- **Motivations**: Financial gain
- **Resources**: Individual
- **Relationship to Target**: Internal
- **Sophistication Tier**: Tier 2 - Hacktivist / campaign-driven
- **State Nexus**: None
- **Targeting Specificity**: Targeted
- **Relevant**: Yes
- **Priority**: 5/10
- **Description**: The single elevated IAM execution role (Resource:*) and deployer credentials; abuse or error has broad blast radius with no per-user scoping.

### Third Party

- **Type**: Third Party
- **Motivations**: Financial gain
- **Resources**: Organization
- **Relationship to Target**: Partner / third-party
- **Sophistication Tier**: Tier 2 - Hacktivist / campaign-driven
- **State Nexus**: None
- **Targeting Specificity**: Opportunistic
- **Relevant**: Yes
- **Priority**: 4/10
- **Description**: Supply-chain / third-party surface: unpinned deps, uvx-spawned awslabs.roda-mcp-server, external OLS/web-search/RODA services whose content and availability the agents depend on.

### Terrorist Organization

- **Type**: Terrorist Organization
- **Motivations**: Ideological / hacktivism, Disruption / destruction
- **Resources**: Club / small group
- **Relationship to Target**: External
- **Sophistication Tier**: Tier 2 - Hacktivist / campaign-driven
- **State Nexus**: None
- **Targeting Specificity**: Sector-focused
- **Relevant**: No
- **Description**: Not relevant: no critical-infrastructure or destructive target profile for a public-data research accelerator.

### Private Sector Offensive Actor

- **Type**: Private Sector Offensive Actor / Cyber Mercenary
- **Motivations**: Financial gain
- **Resources**: Organization
- **Relationship to Target**: External
- **Sophistication Tier**: Tier 4 - State-nexus / advanced
- **State Nexus**: State-aligned
- **Targeting Specificity**: Targeted
- **Relevant**: No
- **Description**: Not relevant to the shipped public-data demo; mercenary zero-day operations are disproportionate to the target value.

### Adversarial open-data / content author (indirect prompt injection)

- **Type**: Third Party
- **Motivations**: Disruption / destruction, Ideological / hacktivism
- **Resources**: Organization
- **Relationship to Target**: Partner / third-party
- **Sophistication Tier**: Tier 3 - Organized cybercrime
- **State Nexus**: None
- **Targeting Specificity**: Sector-focused
- **Relevant**: Yes
- **Priority**: 1/10
- **Description**: An actor who plants indirect prompt-injection payloads or poisoned/misleading records in content the agents ingest: AWS Registry of Open Data datasets (discovered/sampled by the onboarding agent), the PubMed/TCGA Knowledge Base corpus, web-search results, or OLS responses. Goal: manipulate the LLM to fabricate oncology findings/citations, exfiltrate data, misroute tool calls, or steer the onboarding curation/text-to-SQL. Distinctive top actor for this agentic system.

### Malicious hub user (prompt injection / jailbreak / tool abuse)

- **Type**: External Attacker
- **Motivations**: Thrill-seeking / notoriety, Espionage / intelligence collection
- **Resources**: Individual
- **Relationship to Target**: External
- **Sophistication Tier**: Tier 2 - Hacktivist / campaign-driven
- **State Nexus**: None
- **Targeting Specificity**: Targeted
- **Relevant**: Yes
- **Priority**: 2/10
- **Description**: A user (authenticated researcher or, given PUBLIC endpoints, an anonymous internet actor) who crafts adversarial prompts to jailbreak the agent, exfiltrate data beyond entitlement, abuse the query tools (resource-exhaustion Cypher/SQL, attempts to bypass the read-only guards), or coerce confident fabricated medical claims that undermine the faithfulness guarantee.

## Trust Boundaries

### Trust Zones

#### External / Untrusted (internet, third-party content & services)

- **Trust Level**: Untrusted
- **Architecture Nodes**: OLS MCP Server (remote) (C003), AWS-managed Web Search (AgentCore Gateway) (C005), RODA MCP client (uvx subprocess) (C011), External RODA public S3 buckets (D006)
- **Description**: Internet-facing untrusted zone: anonymous/authenticated external clients reaching the PUBLIC AgentCore endpoints, plus third-party content/services whose output is treated as untrusted (OLS MCP, AWS web search, RODA MCP client, external RODA public S3 buckets).

#### Agent / LLM Execution (AgentCore Runtime)

- **Trust Level**: Low
- **Architecture Nodes**: Semantic Hub Agent (AgentCore Runtime) (C001), Claude Sonnet 4.5 (Bedrock model) (C002), oncology-hub-data MCP Server (planned) (C004), Onboarding Curation Agent (orchestration) (C009), AgentCore Code Interpreter sandbox (C010)
- **Description**: The LLM/agent execution zone on Bedrock AgentCore: the semantic hub agent, the Bedrock model, the planned data MCP server, the onboarding curation agent, and the Code Interpreter ETL sandbox. Low trust because it processes untrusted prompts and untrusted tool/data outputs and its decisions must not be implicitly trusted.

#### Operator / Deployment

- **Trust Level**: Medium
- **Architecture Nodes**: Dataset Onboarding UI (Streamlit) (C008)
- **Description**: Operator/deployer workstation running the Streamlit onboarding UI and deploy scripts; holds elevated AWS credentials and performs human-in-the-loop approvals.

#### Identity & Secrets

- **Trust Level**: Medium
- **Architecture Nodes**: Cognito User Pool (M2M auth) (C006), SSM Parameter Store (C007)
- **Description**: Identity and secrets services: Cognito M2M user pool and SSM Parameter Store (holds the shared client secret + config).

#### Governed Data Plane (AWS account)

- **Trust Level**: High
- **Architecture Nodes**: Athena query engine (C012), Glue Data Catalog + Lake Formation (C013), Observability (CloudWatch/X-Ray) (C014), Neptune Analytics knowledge graph (D001), TCGA patient data lake (S3/Athena oncology_semantic_hub) (D002), RODA/staging DB (S3/Athena oncology_semantic_hub_roda) (D003), Raw flat PrimeKG DB (S3/Athena oncology_semantic_hub_raw) (D004), Bedrock Knowledge Base vector store (D005), Athena query-results S3 prefix (D007)
- **Description**: Governed AWS data plane inside the account: Athena, Glue Data Catalog + Lake Formation, Neptune Analytics graph, S3 lake databases (TCGA/RODA/raw/results), Bedrock Knowledge Base, and observability. Highest trust; protected by IAM + Lake Formation + read-only guards.

### Trust Boundaries

#### Internet / Untrusted-Content Boundary

- **Type**: Network
- **Controls**: Cognito M2M CUSTOM_JWT authorizer (allowedClients), HTTPS/TLS, networkMode PUBLIC (AWS recommends VPC per BedrockAgentCore.1), System-prompt provenance/citation discipline, No dedicated prompt-injection / content-sanitization filter on tool outputs
- **Description**: Network + content boundary between the internet/third-party content and the agent/LLM zone. Governs inbound API access (JWT) and the flow of untrusted external content (OLS, web search, RODA open data) into the LLM context and ETL sandbox.

#### Agent-to-Data-Plane Boundary

- **Type**: Account
- **Controls**: Single IAM execution role (Resource:*), Lake Formation grants (DESCRIBE/SELECT), In-process read-only guards: reject_mutations (Cypher), require_select (SQL), Onboarding text-to-SQL guard (SELECT-only, write-keyword reject, table allowlist, LIMIT), Additive *_staging writes only; prod tables untouched, Encryption in transit (HTTPS) + at rest
- **Description**: The critical control boundary between the low-trust agent zone and the governed data plane. Read-only enforcement, IAM, and Lake Formation are the primary defenses against excessive agency and data exfiltration. No per-user data scoping (single role).

#### Identity & Secrets Boundary

- **Type**: Account
- **Controls**: IAM execution role, SSM parameter access, Client secret stored as plaintext String (not SecureString), Broad ssm:GetParameter
- **Description**: Boundary to identity/secrets. Weakness: the shared Cognito M2M secret is stored in SSM as plaintext; anyone with ssm:GetParameter can mint valid tokens (per per-user-auth-design.md).

#### Operator / Onboarding-Autonomy Boundary

- **Type**: Process
- **Controls**: Operator AWS credentials / IAM Role, Human-in-the-loop review of LLM-curated mappings and transform specs, Fixed dynamic.py ETL harness (validates declarative spec; no LLM-authored AWS I/O), Code Interpreter sandbox isolation (networkMode PUBLIC; AWS recommends private)
- **Description**: Process/account boundary between the operator zone and the agentic onboarding pipeline. HITL approval and the fixed harness bound the onboarding agent's autonomy; sandbox isolation contains ETL execution.

## Assets and Flows

### Assets

| ID | Name | Type | Classification | Lifecycle | Data States | Criticality | Owner |
|---|---|---|---|---|---|---|---|
| A009 | TCGA patient cohort data | Data | Public | Active | At rest, In transit, In use | 3 | Hub data plane |
| A010 | Neptune knowledge-graph facts | Data | Public | Active | At rest, In use | 3 | Hub data plane |
| A011 | Knowledge Base literature passages | Data | Public | Active | At rest, In use | 2 | Hub data plane |
| A012 | Cognito M2M client secret | Credential | Restricted | Active | At rest, In transit, In use | 5 | Identity & Secrets |
| A013 | Cognito M2M access token (JWT) | Token | Restricted | Active | In transit, In use | 4 | Identity & Secrets |
| A014 | Untrusted external content (RODA/web/OLS) | Data | Public | Active | In transit, In use | 3 | External sources |
| A015 | Agent answer + provenance tags | Data | Internal | Active | In transit, In use | 3 | Agent zone |
| A016 | User prompt + agent session state | Session | Internal | Active | In transit, In use | 2 | Agent zone |
| A017 | BYOD customer PHI cohort (latent) | Data | Restricted | Quarantined | At rest, In transit, In use | 5 | Customer (production) |

### Asset Flows

| ID | Asset | Source | Destination | Protocol | Encrypted | Risk Level |
|---|---|---|---|---|---|---|
| F001 | Untrusted external content (RODA/web/OLS) | External RODA public S3 buckets (D006) | AgentCore Code Interpreter sandbox (C010) | HTTPS | Yes | 4 |
| F002 | Untrusted external content (RODA/web/OLS) | RODA MCP client (uvx subprocess) (C011) | Onboarding Curation Agent (orchestration) (C009) | stdio | No | 4 |
| F003 | Untrusted external content (RODA/web/OLS) | OLS MCP Server (remote) (C003) | Semantic Hub Agent (AgentCore Runtime) (C001) | HTTPS | Yes | 4 |
| F004 | Knowledge Base literature passages | Bedrock Knowledge Base vector store (D005) | Semantic Hub Agent (AgentCore Runtime) (C001) | HTTPS | Yes | 3 |
| F005 | TCGA patient cohort data | Athena query engine (C012) | Semantic Hub Agent (AgentCore Runtime) (C001) | HTTPS | Yes | 2 |
| F006 | Neptune knowledge-graph facts | Neptune Analytics knowledge graph (D001) | Semantic Hub Agent (AgentCore Runtime) (C001) | HTTPS | Yes | 2 |
| F007 | Cognito M2M client secret | SSM Parameter Store (C007) | Semantic Hub Agent (AgentCore Runtime) (C001) | HTTPS | Yes | 4 |
| F008 | Cognito M2M access token (JWT) | Semantic Hub Agent (AgentCore Runtime) (C001) | OLS MCP Server (remote) (C003) | HTTPS | Yes | 3 |
| F009 | Untrusted external content (RODA/web/OLS) | AgentCore Code Interpreter sandbox (C010) | RODA/staging DB (S3/Athena oncology_semantic_hub_roda) (D003) | HTTPS | Yes | 3 |
| F010 | Agent answer + provenance tags | Semantic Hub Agent (AgentCore Runtime) (C001) | Observability (CloudWatch/X-Ray) (C014) | HTTPS | Yes | 2 |
| F011 | BYOD customer PHI cohort (latent) | Athena query engine (C012) | Semantic Hub Agent (AgentCore Runtime) (C001) | HTTPS | Yes | 5 |

## Threats

### Identified Threats

#### T1: Adversarial open-data/content author (TA013)

**Statement**: A Adversarial open-data/content author (TA013) Agent ingests external content (RODA datasets/samples, web-search results, OLS responses, KB passages) into the LLM context with no dedicated prompt-injection/content-sanitization filter on tool can Embed hidden instructions in third-party content that override the system prompt (indirect/LLM01 prompt injection)., which leads to Agent is steered to fabricate oncology findings/citations, misroute tool calls, attempt data exfiltration, or corrupt onboarding curation/spec generation.

- **Prerequisites**: Agent ingests external content (RODA datasets/samples, web-search results, OLS responses, KB passages) into the LLM context with no dedicated prompt-injection/content-sanitization filter on tool
- **Action**: Embed hidden instructions in third-party content that override the system prompt (indirect/LLM01 prompt injection).
- **Impact**: Agent is steered to fabricate oncology findings/citations, misroute tool calls, attempt data exfiltration, or corrupt onboarding curation/spec generation.
- **Impacted Assets**: A014, A011, A015
- **Tags**: LLM01, prompt-injection, agentic
- **Residual Risk Decision**: Open
- **Residual Severity**: High
- **Residual Likelihood**: Likely
- **Residual Risk Rationale**: No preventive control implemented (no Bedrock Guardrails, no content sanitization); only prompt instruction-following. Top agentic risk; must implement M001/M002 before production.
- **Assessment State**: Current

#### T3: Privileged user / insider / disgruntled operator (TA009/TA001/TA008)

**Statement**: A Privileged user / insider / disgruntled operator (TA009/TA001/TA008) Shared Cognito M2M secret stored in SSM as a plaintext String; broad ssm:GetParameter. can Read the secret from SSM and mint valid JWTs., which leads to Unauthorized, unattributable access to the OLS/data MCP endpoints; secret rotation is the only remedy.

- **Prerequisites**: Shared Cognito M2M secret stored in SSM as a plaintext String; broad ssm:GetParameter.
- **Action**: Read the secret from SSM and mint valid JWTs.
- **Impact**: Unauthorized, unattributable access to the OLS/data MCP endpoints; secret rotation is the only remedy.
- **Impacted Assets**: A012, A013
- **Tags**: secrets, SSM-plaintext
- **Residual Risk Decision**: Open
- **Residual Severity**: High
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: Secret stored as plaintext SSM String with Resource:* read; disclosure enables token minting. Fix with SecureString + ARN-scoped SSM (M003) - cheap, high value.
- **Assessment State**: Current

#### T4: External attacker / malicious hub user (TA002/TA014)

**Statement**: A External attacker / malicious hub user (TA002/TA014) Single shared machine identity; no per-user identity or audit. can Present a valid shared JWT (or obtained secret) to impersonate the one machine client., which leads to Full tool access as the shared identity with no per-user attribution; misuse cannot be traced to an individual.

- **Prerequisites**: Single shared machine identity; no per-user identity or audit.
- **Action**: Present a valid shared JWT (or obtained secret) to impersonate the one machine client.
- **Impact**: Full tool access as the shared identity with no per-user attribution; misuse cannot be traced to an individual.
- **Impacted Assets**: A013
- **Tags**: auth, shared-identity
- **Residual Risk Decision**: Open
- **Residual Severity**: High
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: Single shared machine identity; no per-user auth. Acceptable only for a single-operator demo; must adopt per-user SSO (M004) before multi-tenant/production.
- **Assessment State**: Current

#### T5: External attacker / script kiddie (TA002/TA007)

**Statement**: A External attacker / script kiddie (TA002/TA007) AgentCore runtimes are networkMode PUBLIC; the CUSTOM_JWT authorizer is omitted or misconfigured (the design explicitly warns against this). can Reach the internet-exposed agent/MCP endpoint without authentication., which leads to Unauthorized query execution, data access, and compute/cost abuse over the internet.

- **Prerequisites**: AgentCore runtimes are networkMode PUBLIC; the CUSTOM_JWT authorizer is omitted or misconfigured (the design explicitly warns against this).
- **Action**: Reach the internet-exposed agent/MCP endpoint without authentication.
- **Impact**: Unauthorized query execution, data access, and compute/cost abuse over the internet.
- **Impacted Assets**: A009, A010
- **Tags**: public-endpoint, authz
- **Residual Risk Decision**: Open
- **Residual Severity**: High
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: Agent runtime is IAM-SigV4 gated (reduces from Critical) but networkMode is PUBLIC and there is no deploy-time authorizer preflight for the MCP path. Enforce authorizer + VPC (M005) and add WAF (M019).
- **Assessment State**: Current

#### T6: Malicious hub user (TA014)

**Statement**: A Malicious hub user (TA014) Single IAM execution role with no per-user data scoping; agent will query any table/cohort the role can reach. can Craft prompts that direct the agent to query data beyond the user's entitlement., which leads to Disclosure of any data the role can access; Critical under BYOD (whole PHI cohort readable by any authorized caller).

- **Prerequisites**: Single IAM execution role with no per-user data scoping; agent will query any table/cohort the role can reach.
- **Action**: Craft prompts that direct the agent to query data beyond the user's entitlement.
- **Impact**: Disclosure of any data the role can access; Critical under BYOD (whole PHI cohort readable by any authorized caller).
- **Impacted Assets**: A009, A017
- **Tags**: no-per-user-scoping, exfiltration
- **Residual Risk Decision**: Open
- **Residual Severity**: High
- **Residual Likelihood**: Likely
- **Residual Risk Rationale**: Single IAM role, no per-user data scoping; any authorized caller can reach all data the role can. High for demo, Critical under BYOD. Requires M006.
- **Assessment State**: Current

#### T10: Malicious hub user (TA014)

**Statement**: A Malicious hub user (TA014) Query tools accept arbitrary Cypher/Athena SQL with no cost/complexity ceiling. can Submit unbounded graph traversals or full-scan SQL., which leads to Excessive Athena/Neptune cost, latency, and degraded availability for other users.

- **Prerequisites**: Query tools accept arbitrary Cypher/Athena SQL with no cost/complexity ceiling.
- **Action**: Submit unbounded graph traversals or full-scan SQL.
- **Impact**: Excessive Athena/Neptune cost, latency, and degraded availability for other users.
- **Impacted Assets**: A009, A010
- **Tags**: unbounded-consumption, cost
- **Residual Risk Decision**: Open
- **Residual Severity**: Medium
- **Residual Likelihood**: Likely
- **Residual Risk Rationale**: No Athena scan cutoff or Neptune complexity/timeout cap; unbounded queries can drive cost/latency. Implement M010 + edge throttling (M019).
- **Assessment State**: Current

#### T11: Malicious user / injected content (TA014/TA013)

**Statement**: A Malicious user / injected content (TA014/TA013) Agent autonomously chains tool calls; no hard cap on iterations/spend surfaced. can Adversarial prompt or injected instruction induces long tool-call loops / repeated model invocations., which leads to Denial-of-wallet: runaway Bedrock + query costs and resource exhaustion.

- **Prerequisites**: Agent autonomously chains tool calls; no hard cap on iterations/spend surfaced.
- **Action**: Adversarial prompt or injected instruction induces long tool-call loops / repeated model invocations.
- **Impact**: Denial-of-wallet: runaway Bedrock + query costs and resource exhaustion.
- **Impacted Assets**: A015
- **Tags**: excessive-agency, denial-of-wallet
- **Residual Risk Decision**: Open
- **Residual Severity**: Medium
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: No agent iteration/tool-call/spend cap; adversarial prompts or injection can drive denial-of-wallet. Implement M011 + cost alarms.
- **Assessment State**: Current

#### T13: Privileged user / insider (TA009/TA001)

**Statement**: A Privileged user / insider (TA009/TA001) Prompts, answers, and (under BYOD) PHI may appear in OTel traces / CloudWatch logs / EMF metrics. can Read sensitive content from observability data., which leads to Disclosure of user queries/answers; HIPAA-relevant exposure when BYOD PHI is present.

- **Prerequisites**: Prompts, answers, and (under BYOD) PHI may appear in OTel traces / CloudWatch logs / EMF metrics.
- **Action**: Read sensitive content from observability data.
- **Impact**: Disclosure of user queries/answers; HIPAA-relevant exposure when BYOD PHI is present.
- **Impacted Assets**: A015, A016, A017
- **Tags**: observability, log-hygiene
- **Residual Risk Decision**: Open
- **Residual Severity**: Medium
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: Prompts/answers are logged and traced with no redaction. Low sensitivity for public data but High under BYOD PHI; implement redaction + KMS (M013).
- **Assessment State**: Current

#### T14: Privileged user / compromised agent (TA009/TA014)

**Statement**: A Privileged user / compromised agent (TA009/TA014) IAM execution role policy grants actions on Resource:*. can Abuse or leverage a compromise of the agent/role to act across the account's Bedrock/Neptune/Athena/Glue/S3/SSM., which leads to Broad lateral movement and data access beyond the hub's intended scope.

- **Prerequisites**: IAM execution role policy grants actions on Resource:*.
- **Action**: Abuse or leverage a compromise of the agent/role to act across the account's Bedrock/Neptune/Athena/Glue/S3/SSM.
- **Impact**: Broad lateral movement and data access beyond the hub's intended scope.
- **Impacted Assets**: A009, A012
- **Tags**: iam, least-privilege
- **Residual Risk Decision**: Open
- **Residual Severity**: High
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: Resource:* IAM amplifies any agent/role compromise across the account. Scope to ARNs and split roles (M014).
- **Assessment State**: Current

#### T15: Third party / supply chain (TA010)

**Statement**: A Third party / supply chain (TA010) Unpinned Python dependencies; RODA MCP server fetched/run on demand via uvx. can Introduce a malicious package or version that executes in the agent/onboarding process., which leads to Code execution, secret theft, or data tampering inside the trusted runtime.

- **Prerequisites**: Unpinned Python dependencies; RODA MCP server fetched/run on demand via uvx.
- **Action**: Introduce a malicious package or version that executes in the agent/onboarding process.
- **Impact**: Code execution, secret theft, or data tampering inside the trusted runtime.
- **Impacted Assets**: A012, A014
- **Tags**: supply-chain, dependencies
- **Residual Risk Decision**: Open
- **Residual Severity**: High
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: Unpinned deps + on-demand uvx MCP resolution widen the supply-chain surface in a trusted runtime. Pin/hash + lock + SCA (M015).
- **Assessment State**: Current

#### T18: Malicious user or benign model failure (TA014)

**Statement**: A Malicious user or benign model failure (TA014) LLM can hallucinate; an experimental SEMHUB_STRIP_GUARDS toggle removes the citation-discipline/statistical-rigor guardrails. can Coerce (or trigger) confident, ungrounded oncology claims without honest provenance tagging., which leads to Fabricated/ungrounded medical claims presented as grounded, violating the core faithfulness NFR and risking research misinformation.

- **Prerequisites**: LLM can hallucinate; an experimental SEMHUB_STRIP_GUARDS toggle removes the citation-discipline/statistical-rigor guardrails.
- **Action**: Coerce (or trigger) confident, ungrounded oncology claims without honest provenance tagging.
- **Impact**: Fabricated/ungrounded medical claims presented as grounded, violating the core faithfulness NFR and risking research misinformation.
- **Impacted Assets**: A015
- **Tags**: hallucination, faithfulness, guardrail-strip
- **Residual Risk Decision**: Open
- **Residual Severity**: High
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: Faithfulness is the core value proposition; the SEMHUB_STRIP_GUARDS toggle can disable citation discipline at runtime and is not blocked in prod. Gate the toggle + alarm on fabricated grounding (M016).
- **Assessment State**: Current

#### T20: Organized crime / external attacker (TA005/TA002)

**Statement**: A Organized crime / external attacker (TA005/TA002) A customer loads BYOD PHI into the shipped demo-grade posture (single role, no per-user scoping, PUBLIC network, no BAA-aligned config). can Exploit any of the disclosure/exfiltration paths against real PHI., which leads to HIPAA violation and patient-privacy breach; high financial/reputational/legal impact.

- **Prerequisites**: A customer loads BYOD PHI into the shipped demo-grade posture (single role, no per-user scoping, PUBLIC network, no BAA-aligned config).
- **Action**: Exploit any of the disclosure/exfiltration paths against real PHI.
- **Impact**: HIPAA violation and patient-privacy breach; high financial/reputational/legal impact.
- **Impacted Assets**: A017
- **Tags**: byod, phi, hipaa
- **Residual Risk Decision**: Open
- **Residual Severity**: Critical
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: The shipped posture (single role, no per-user scoping, PUBLIC network, no log redaction, no BAA-aligned config) is unsuitable for PHI. BYOD PHI use must be gated behind a hardened profile (M018) + M006/M013; the repo legal note requires a BAA.
- **Assessment State**: Current

### Resolved Threats

#### T2: Adversarial open-data/content author (TA013)

**Statement**: A Adversarial open-data/content author (TA013) Poisoned KB corpus or onboarded open-data records enter the retrieval/answer path. can Inject fake PMIDs / misleading records so the model cites plausible-but-false sources., which leads to Agent emits confident fabricated medical evidence with valid-looking provenance tags, defeating the grounding/faithfulness guarantee (research-misinformation risk).

- **Prerequisites**: Poisoned KB corpus or onboarded open-data records enter the retrieval/answer path.
- **Action**: Inject fake PMIDs / misleading records so the model cites plausible-but-false sources.
- **Impact**: Agent emits confident fabricated medical evidence with valid-looking provenance tags, defeating the grounding/faithfulness guarantee (research-misinformation risk).
- **Impacted Assets**: A011, A015
- **Tags**: data-poisoning, faithfulness
- **Residual Risk Decision**: Accepted
- **Residual Severity**: Medium
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: Citation-discipline prompt + provenance-faithfulness scorer detect fabricated grounding; data is public. Accept for the demo while adding corpus-integrity checks + fabricated-grounding alarms (M016) for production.
- **Assessment State**: Current

#### T7: Malicious hub user / content author (TA014/TA013)

**Statement**: A Malicious hub user / content author (TA014/TA013) Read-only enforcement depends on regex guards (reject_mutations / require_select) plus least-privilege IAM. can Craft Cypher/SQL that evades the regex guard (e.g. obfuscation, comment tricks, unsupported keywords)., which leads to If IAM also lacked write denial, tampering; in practice IAM read-only is the backstop, so impact is limited but the guard is the sole in-process control.

- **Prerequisites**: Read-only enforcement depends on regex guards (reject_mutations / require_select) plus least-privilege IAM.
- **Action**: Craft Cypher/SQL that evades the regex guard (e.g. obfuscation, comment tricks, unsupported keywords).
- **Impact**: If IAM also lacked write denial, tampering; in practice IAM read-only is the backstop, so impact is limited but the guard is the sole in-process control.
- **Impacted Assets**: A009, A010
- **Tags**: guard-bypass, defense-in-depth
- **Residual Risk Decision**: Accepted
- **Residual Severity**: Low
- **Residual Likelihood**: Unlikely
- **Residual Risk Rationale**: Read-only guards are implemented and unit-tested, and IAM grants no write actions (backstop). Residual bypass risk is low for read-only public data; add explicit IAM write-Deny (M007) as hardening.
- **Assessment State**: Current

#### T8: Adversarial content author / malicious user (TA013/TA014)

**Statement**: A Adversarial content author / malicious user (TA013/TA014) Onboarding text-to-SQL (answer_question/answer_hub) generates SQL from NL questions + possibly poisoned schema, guarded by a separate regex/allowlist. can Influence generated SQL to read beyond the intended table or evade the allowlist., which leads to Unauthorized reads within the RODA database; bounded by SELECT-only + LIMIT + IAM but the guard is independently maintained from hub_core.guards.

- **Prerequisites**: Onboarding text-to-SQL (answer_question/answer_hub) generates SQL from NL questions + possibly poisoned schema, guarded by a separate regex/allowlist.
- **Action**: Influence generated SQL to read beyond the intended table or evade the allowlist.
- **Impact**: Unauthorized reads within the RODA database; bounded by SELECT-only + LIMIT + IAM but the guard is independently maintained from hub_core.guards.
- **Impacted Assets**: A014, A009
- **Tags**: text-to-sql, agentic
- **Residual Risk Decision**: Accepted
- **Residual Severity**: Medium
- **Residual Likelihood**: Unlikely
- **Residual Risk Rationale**: Onboarding text-to-SQL is guarded (SELECT-only, write-keyword reject, table allowlist, LIMIT) and confined to the RODA staging DB over public data. Accept for demo; consolidate onto hub_core.guards (M008).
- **Assessment State**: Current

#### T9: Adversarial open-data author (TA013)

**Statement**: A Adversarial open-data author (TA013) LLM emits a declarative transform spec from untrusted data; the fixed dynamic.py harness + validate_spec run it in the Code Interpreter sandbox. can Attempt to coerce a spec/ETL that writes outside staging or exfiltrates via the PUBLIC-network sandbox., which leads to Largely bounded by the fixed harness (additive staging only, allowlisted ops) + IAM; residual risk is poisoned/misleading staging data surfaced later by the agent.

- **Prerequisites**: LLM emits a declarative transform spec from untrusted data; the fixed dynamic.py harness + validate_spec run it in the Code Interpreter sandbox.
- **Action**: Attempt to coerce a spec/ETL that writes outside staging or exfiltrates via the PUBLIC-network sandbox.
- **Impact**: Largely bounded by the fixed harness (additive staging only, allowlisted ops) + IAM; residual risk is poisoned/misleading staging data surfaced later by the agent.
- **Impacted Assets**: A014
- **Tags**: code-interpreter, etl, sandbox
- **Residual Risk Decision**: Accepted
- **Residual Severity**: Medium
- **Residual Likelihood**: Unlikely
- **Residual Risk Rationale**: Strong containment: fixed harness + validate_spec (no LLM-authored AWS I/O), additive staging only, HITL review. Residual is limited to poisoned staging content; harden sandbox network (M009) for production.
- **Assessment State**: Current

#### T12: Malicious hub user (TA014)

**Statement**: A Malicious hub user (TA014) Per-session Agent objects held in an in-memory _SESSIONS dict in the warm container, keyed by session_id. can Reuse or guess a session_id to reach another caller's cached agent/context., which leads to Cross-session leakage of prompts/answers/context between users sharing a warm container.

- **Prerequisites**: Per-session Agent objects held in an in-memory _SESSIONS dict in the warm container, keyed by session_id.
- **Action**: Reuse or guess a session_id to reach another caller's cached agent/context.
- **Impact**: Cross-session leakage of prompts/answers/context between users sharing a warm container.
- **Impacted Assets**: A016
- **Tags**: session-isolation, warm-container
- **Residual Risk Decision**: Accepted
- **Residual Severity**: Low
- **Residual Likelihood**: Unlikely
- **Residual Risk Rationale**: Sessions are keyed by session_id in a warm container; single-tenant demo makes cross-session leakage low-likelihood. Bind to principal + TTL (M012) before multi-tenant use.
- **Assessment State**: Current

#### T16: Compromised third-party service (TA010/TA013)

**Statement**: A Compromised third-party service (TA010/TA013) Agent depends on external OLS / web-search / RODA services for content and availability. can A compromised or hostile external service returns malicious or false responses., which leads to Prompt injection or factual corruption of answers; loss of a tool degrades the hub.

- **Prerequisites**: Agent depends on external OLS / web-search / RODA services for content and availability.
- **Action**: A compromised or hostile external service returns malicious or false responses.
- **Impact**: Prompt injection or factual corruption of answers; loss of a tool degrades the hub.
- **Impacted Assets**: A014
- **Tags**: third-party, integrity
- **Residual Risk Decision**: Accepted
- **Residual Severity**: Medium
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: External services are reputable AWS/EBI/PubMed sources; content is already treated as citation-only and public. Accept for demo; add integrity/allowlist checks with M001/M002 for production.
- **Assessment State**: Current

#### T17: Malicious user / insider (TA014/TA001)

**Statement**: A Malicious user / insider (TA014/TA001) All callers share one machine identity; no per-user JWT or session attribution. can Perform queries/actions under the shared identity., which leads to Actions are not attributable to an individual; weak forensics and non-repudiation, a compliance gap under HIPAA/production.

- **Prerequisites**: All callers share one machine identity; no per-user JWT or session attribution.
- **Action**: Perform queries/actions under the shared identity.
- **Impact**: Actions are not attributable to an individual; weak forensics and non-repudiation, a compliance gap under HIPAA/production.
- **Impacted Assets**: A013
- **Tags**: audit, non-repudiation
- **Residual Risk Decision**: Accepted
- **Residual Severity**: Low
- **Residual Likelihood**: Likely
- **Residual Risk Rationale**: Single shared identity gives no per-user attribution, acceptable for a single-operator public-data demo but a compliance gap for production; addressed by per-user SSO (M004).
- **Assessment State**: Current

#### T19: Privileged user error (TA009)

**Statement**: A Privileged user error (TA009) Lake Formation grants are applied best-effort at deploy; graph/lake availability is unmanaged. can Misconfigure or revoke LF grants / graph availability., which leads to Agent queries fail (often silently), degrading hub availability and answer quality.

- **Prerequisites**: Lake Formation grants are applied best-effort at deploy; graph/lake availability is unmanaged.
- **Action**: Misconfigure or revoke LF grants / graph availability.
- **Impact**: Agent queries fail (often silently), degrading hub availability and answer quality.
- **Impacted Assets**: A009
- **Tags**: lake-formation, availability
- **Residual Risk Decision**: Accepted
- **Residual Severity**: Low
- **Residual Likelihood**: Possible
- **Residual Risk Rationale**: Availability-only, non-security; best-effort LF grants + graceful degradation are acceptable for a demo. Add fail-closed verification + alarms (M017) for production.
- **Assessment State**: Current

## Mitigations

### Identified Mitigations

#### M1: Multi-layer input validation + Amazon Bedrock Guardrails for prompt-injection defense across every agent input surface (user prompt AND tool/retrieved content).

**Addresses Threats**: T1, T2, T16, T18

#### M3: Store the Cognito client secret in SSM SecureString (KMS) or Secrets Manager and scope ssm:GetParameter to the exact parameter ARNs; enable rotation.

**Addresses Threats**: T3

#### M4: Replace the shared M2M identity with per-user SSO/OIDC (authorization_code) so each caller presents their own short-lived JWT (sub/email/groups).

**Addresses Threats**: T4, T6, T17

#### M6: Per-user/tenant data authorization: sts:AssumeRole with session name/tags = user, plus Lake Formation grants scoped per group; restrict cohorts/tables by the caller's claims.

**Addresses Threats**: T6, T20

#### M10: Bound query cost/complexity: Athena workgroup per-query data-scan limits + result caps, and Neptune query timeouts / row limits.

**Addresses Threats**: T10

#### M11: Cap agent autonomy and spend: max tool-call iterations per turn, max tokens, loop detection, and CloudWatch cost/anomaly alarms (denial-of-wallet).

**Addresses Threats**: T11

#### M13: Observability data hygiene: redact prompts/answers/PHI from traces/logs, encrypt log groups with KMS, and least-privilege access to CloudWatch/X-Ray.

**Addresses Threats**: T13, T20

#### M14: Scope the IAM execution role to specific resource ARNs and split per function (agent vs onboarding vs MCP), removing Resource:*.

**Addresses Threats**: T3, T14

#### M15: Software supply-chain hardening: pin dependencies with hashes, vendor/lock the RODA MCP server version, and run SCA/dependency scanning in CI.

**Addresses Threats**: T15

#### M18: BYOD/HIPAA hardening profile: gate PHI onboarding behind a hardened configuration (BAA, VPC network mode, per-user scoping, KMS encryption, audit, log redaction) with explicit documentation.

**Addresses Threats**: T20

#### M19: Edge protection on public endpoints: AWS WAF + rate limiting / throttling in front of the agent and MCP endpoints.

**Addresses Threats**: T5, T10, T11

### In Progress Mitigations

#### M2: Treat all tool outputs / retrieved passages as untrusted data: structurally delimit and label external content in the context, never execute embedded instructions, and keep the existing inline-provenance/citation discipline.

**Addresses Threats**: T1, T2, T16

#### M5: Enforce the CUSTOM_JWT authorizer on every PUBLIC AgentCore endpoint with a deploy-time preflight that fails if the authorizer is absent, and migrate runtimes to VPC network mode.

**Addresses Threats**: T5

#### M7: Keep the in-process read-only guards (reject_mutations / require_select) AND explicitly deny all write actions in IAM as the authoritative backstop; unit-test guards against a bypass corpus.

**Addresses Threats**: T7

#### M8: Harden the onboarding text-to-SQL path: reuse hub_core.guards.require_select, validate/parameterize identifiers, keep the table allowlist + mandatory LIMIT.

**Addresses Threats**: T8

#### M9: Keep the fixed dynamic.py ETL harness + validate_spec (LLM emits only a validated declarative spec) and run the Code Interpreter with a private/VPC network configuration and tightly-scoped egress + role.

**Addresses Threats**: T9

#### M12: Enforce session isolation: bind _SESSIONS entries to the authenticated principal, use unguessable session ids, and apply TTL/eviction so warm containers cannot leak context across users.

**Addresses Threats**: T12

#### M16: Faithfulness assurance: remove/production-gate the SEMHUB_STRIP_GUARDS toggle, and run the provenance-faithfulness / grounding scorer with alerting on fabricated grounding.

**Addresses Threats**: T2, T18

#### M17: Availability assurance for the data plane: make Lake Formation grants explicit + verified post-deploy and alarm on query failures / graph unavailability.

**Addresses Threats**: T19

## Assumptions

### A001: Data sensitivity / compliance

**Description**: The shipped/demo deployment uses only PUBLIC de-identified TCGA data (no PHI). HIPAA is latent, triggered only by the documented Bring-Your-Own-Data path where a customer substitutes their own (possibly PHI) cohort.

- **Impact**: Bounds current data-breach severity to public data; production/BYOD deployments materially raise confidentiality and HIPAA impact.
- **Rationale**: Repo legal note states the solution is demonstrative, not for clinical use; BYOD guide (docs/bring-your-own-data.md) documents cohort substitution.

### A002: Authentication / authorization

**Description**: Authentication is a single shared Cognito M2M (client_credentials) JWT; the client secret is in SSM as a plaintext String; no per-user identity or per-user data scoping; one IAM execution role runs all queries.

- **Impact**: No per-user audit or least-privilege at the identity layer; secret disclosure lets any reader mint valid tokens.
- **Rationale**: docs/per-user-auth-design.md 'Current state' section; SSO/OIDC + per-user STS AssumeRole is target design, not implemented.

### A003: Network exposure

**Description**: AgentCore Runtimes (agent + MCP servers + Code Interpreter) are deployed with networkMode PUBLIC and must ship with the CUSTOM_JWT authorizer.

- **Impact**: A missing/misconfigured authorizer exposes the agent/MCP endpoints to the internet.
- **Rationale**: deploy.py sets networkMode PUBLIC; remote-mcp-server-design.md explicitly warns not to leave the endpoint unauthenticated.

### A004: IAM / least privilege

**Description**: The IAM execution role policy grants actions on Resource:"*" rather than resource-scoped ARNs.

- **Impact**: Compromise or agent misuse operates with broader-than-necessary permissions across the account's Bedrock/Neptune/Athena/Glue/S3/SSM.
- **Rationale**: agentcore/deploy.py POLICY document uses a single statement with Resource:'*'.

### A005: Input validation / injection

**Description**: Read-only enforcement relies on least-privilege IAM plus in-process guards (hub_core/guards.py). The onboarding text-to-SQL path uses a separate regex/allowlist guard in agent.py, not hub_core.guards.

- **Impact**: Divergent guard implementations must both be correct; the onboarding SQL guard is regex-based and independently maintained.
- **Rationale**: guards.py implements reject_mutations/require_select; agent.answer_question/answer_hub implement their own SELECT-only + write-keyword + table-allowlist checks.

### A006: Agentic autonomy / blast radius

**Description**: Data onboarding is human-in-the-loop and writes only additive *_staging tables; ETL runs the fixed dynamic.py harness (LLM emits only a declarative spec, not code) inside an AgentCore Code Interpreter sandbox.

- **Impact**: Bounds the onboarding agent's write blast radius to staging tables and constrains LLM influence to a validated spec, not arbitrary code.
- **Rationale**: onboard_runner.py + dynamic.py: validate_spec allowlists formats/casts; prod tables untouched, enforced by IAM and the harness.

### A007: Supply chain

**Description**: Python dependencies are declared unpinned in requirements.txt; the RODA MCP client runs as a uvx-spawned subprocess of awslabs.roda-mcp-server.

- **Impact**: Unpinned deps and on-demand package resolution widen the software supply-chain attack surface.
- **Rationale**: requirements.txt has no version pins; roda_mcp.py spawns 'uvx awslabs.roda-mcp-server' over stdio.

### A008: AWS documentation validation

**Description**: AWS Security Hub control BedrockAgentCore.1 states AgentCore runtimes should be configured with VPC network mode, and the AWS AI security standard requires the AgentCore Code Interpreter to use a private network configuration. This system deploys runtimes and the Code Interpreter with networkMode PUBLIC.

- **Impact**: PUBLIC network mode is non-compliant with the AWS-recommended VPC/private posture; increases network exposure and data-egress surface for the agent and ETL sandbox.
- **Rationale**: Validated via AWS Documentation MCP: securityhub BedrockAgentCore.1 and standards-ai-security (Code Interpreter private network) controls; agentcore-vpc best-practices guide.

### A018: Residual risk acceptance

**Description**: Risk-acceptance basis: threats were Accepted only where an implemented control (read-only guards+tests, guarded onboarding SQL, fixed ETL harness+HITL, provenance-faithfulness scorer, single-tenant demo) reduces them to Low/Medium AND the shipped data is public TCGA. All Confidentiality/Integrity risks that depend on unbuilt controls (Guardrails, per-user auth/scoping, secret hardening, IAM scoping, cost caps, dep pinning, faithfulness-toggle gating, BYOD hardening) were left Open as must-fix before production or BYOD/PHI use.

- **Impact**: 11 Open threats form the production-readiness backlog; 9 Accepted are contingent on remaining a single-operator public-data demo.
- **Rationale**: Aligns with the repo's own stance (demonstrative, not for clinical/production use; BAA required for PHI) and the code-validation evidence from Phase 7.5.

## Phase Progress

| Phase | Name | Completion |
|---|---|---|
| 1 | Business Context Analysis | 100% ✅ |
| 2 | Architecture Analysis | 100% ✅ |
| 3 | Threat Actor Analysis | 100% ✅ |
| 4 | Trust Boundary Analysis | 0% ⏳ |
| 5 | Asset Flow Analysis | 0% ⏳ |
| 6 | Threat Identification | 100% ✅ |
| 7 | Mitigation Planning | 100% ✅ |
| 7.5 | Code Validation Analysis | 100% ✅ |
| 8 | Residual Risk Analysis | 100% ✅ |
| 9 | Output Generation and Documentation | 100% ✅ |

---

*This threat model report was generated automatically by the Threat Modeling MCP Server.*
