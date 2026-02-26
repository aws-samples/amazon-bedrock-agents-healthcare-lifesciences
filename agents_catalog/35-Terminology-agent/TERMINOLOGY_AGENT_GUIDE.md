# Terminology Agent with OLS Integration Guide

## Overview

The Terminology Agent is a specialized medical terminology standardization agent that combines:

1. **EBI Ontology Lookup Service (OLS)** - Access to 200+ biological/medical ontologies
2. **AgentCore Gateway Tools** - Custom Lambda-based domain tools
3. **Code Interpreter** - Secure Python execution for data processing
4. **AgentCore Memory** - Conversation history and context

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Terminology Agent                         │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Gateway    │  │  OLS MCP     │  │      Code       │  │
│  │   MCP Tools  │  │   Server     │  │  Interpreter    │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│         │                 │                    │            │
│         └─────────────────┴────────────────────┘            │
│                           │                                 │
│                  ┌────────▼────────┐                        │
│                  │ Claude Sonnet   │                        │
│                  │     4.5         │                        │
│                  └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Status

### ✅ OLS MCP Server

The OLS MCP Server is deployed and tested at:
- **Agent ARN**: `arn:aws:bedrock-agentcore:us-west-2:942514891246:runtime/ols_mcp_server-ChEmBE8HM3`
- **Configuration**: Stateless HTTP mode on port 8000
- **Authentication**: OAuth2 M2M via Cognito
- **Tools Available**: 7 OLS tools for ontology lookup

### ✅ Agent Code

The Terminology Agent code is located at:
- **Path**: `patterns/strands-single-agent/terminology_agent_with_ols.py`
- **Features**:
  - Connects to both Gateway and OLS MCP servers
  - Graceful fallback if OLS unavailable
  - Specialized system prompt for medical terminology
  - Strong typing and comprehensive docstrings

### ⏳ CDK Configuration

**Updated**: The CDK stack has been configured to deploy the Terminology Agent:
- Changed entrypoint from `basic_agent.py` to `terminology_agent_with_ols.py`
- Location: `infra-cdk/lib/backend-stack.ts` line 205

## Core Capabilities

### 1. Entity Recognition and Extraction

Automatically identify medical and scientific entities in natural language queries:

**Example:**
```
User: "Show me clinical trials for lymphocytic leukemia with IL-23 expression"
Agent: [Uses extract_entities tool]
       Extracted entities:
       - "lymphocytic leukemia" (DISEASE, confidence: 0.95)
       - "IL-23" (GENE, confidence: 0.92)
       - "clinical trials" (context keyword)
```

**Supported Entity Types:**
- DISEASE: Diseases, conditions, syndromes
- DRUG: Medications, treatments
- GENE: Gene symbols (IL-23, TNF, BDNF)
- PROTEIN: Protein names
- ANATOMY: Anatomical structures, tissues, organs
- LAB_TEST: Laboratory tests, measurements
- PROCEDURE: Medical procedures, surgeries
- PHENOTYPE: Observable characteristics, symptoms
- ORGANISM: Species names
- CHEMICAL: Chemical compounds

### 2. Terminology Standardization

Convert variant medical terms to official ontology identifiers:

**Example:**
```
User: "What's the MONDO ID for myocardial infarction?"
Agent: [Uses ols_search_terms]
       MONDO:0005068 - myocardial infarction
```

**Advanced Standardization:**
```
User: "Standardize these terms: heart attack, MI, myocardial infarction"
Agent: [Uses extract_entities + ols_search_terms + generate_standardized_query]
       All terms map to: MONDO:0005068 - myocardial infarction
       Synonyms: heart attack, MI, myocardial infarction
       Parent terms: acute coronary syndrome
```

### 3. Query Disambiguation

Resolve ambiguous terms using ontological context:

**Example:**
```
User: "What type of entity is 'IL-23' in the context of gene expression?"
Agent: [Uses classify_entity_type]
       Entity type: GENE
       Reasoning: Used in gene expression context
```

### 4. Concept Expansion

Discover related terms and hierarchical relationships:

**Example:**
```
User: "Show me parent and child terms for diabetes"
Agent: [Uses ols_get_term_info + ols_get_term_ancestors + ols_get_term_children]
       Parent terms: metabolic disease, endocrine system disease
       Child terms: type 1 diabetes, type 2 diabetes, gestational diabetes
```

### 5. Standardized Query Generation

Generate structured output for downstream agents:

**Example:**
```
User: "Find clinical trials for lymphocytic leukemia"
Agent: [Uses extract_entities → ols_search_terms → generate_standardized_query]

Output:
{
  "original_query": "Find clinical trials for lymphocytic leukemia",
  "standardized_query": {
    "entities": [
      {
        "original_text": "lymphocytic leukemia",
        "entity_type": "DISEASE",
        "standardized_terms": [
          {
            "ontology": "MONDO",
            "code": "MONDO:0004948",
            "preferred_label": "lymphoid leukemia",
            "synonyms": ["lymphocytic leukemia"]
          }
        ],
        "confidence": 0.95
      }
    ],
    "query_intent": "clinical_trial_search",
    "suggested_filters": {
      "disease_codes": ["MONDO:0004948"],
      "include_subtypes": true
    }
  },
  "metadata": {
    "tools_used": ["extract_entities", "ols_search_terms", "generate_standardized_query"],
    "confidence_score": 0.95,
    "warnings": []
  }
}
```

## Available Tools

### Entity Extraction & Standardization Tools

The agent has access to LLM-powered entity extraction and query standardization tools:

| Tool | Description | When to Use |
|------|-------------|-------------|
| `extract_entities` | Extract medical/scientific entities from natural language queries | Complex queries with multiple terms or ambiguous language |
| `classify_entity_type` | Classify an entity into a specific type (DISEASE, DRUG, GENE, etc.) | When entity type is unclear from context |
| `suggest_ontology_codes` | Suggest codes from LLM's training knowledge (MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC) | Quick suggestions, ontologies not in OLS, pre-filtering, offline scenarios |
| `generate_standardized_query` | Create structured output with codes and mappings for downstream agents | Preparing queries for domain-specific agents (clinical trials, biomarker analysis, etc.) |

### OLS Ontology Tools

The agent has access to these OLS tools (via `ols_` prefix):

| Tool | Description |
|------|-------------|
| `ols_search_terms` | Search across ontologies for medical/biological terms |
| `ols_get_ontology_info` | Get detailed metadata about a specific ontology |
| `ols_search_ontologies` | Discover available ontologies by domain |
| `ols_get_term_info` | Get comprehensive details about specific terms |
| `ols_get_term_children` | Find direct child terms in hierarchies |
| `ols_get_term_ancestors` | Retrieve parent terms and ancestors |
| `ols_find_similar_terms` | Discover semantically similar terms |

### Other Tools

| Tool | Description |
|------|-------------|
| `gateway_*` | Custom domain-specific Lambda-based tools |
| `execute_python_securely` | Code Interpreter for data processing and visualization |

## Key Ontologies

### Available via OLS MCP Server (Authoritative)

The agent accesses **200+ ontologies** through the [EBI Ontology Lookup Service](https://www.ebi.ac.uk/ols4/ontologies), covering diverse biomedical and life sciences domains:

**Most Frequently Used (Clinical & Research):**
1. **MONDO** - Disease classification and medical conditions (30,000+ terms)
2. **HPO** - Human phenotypes for clinical descriptions (16,000+ terms)
3. **GO** - Gene functions and biological processes (44,000+ terms)
4. **ChEBI** - Chemical compounds and drug substances (200,000+ terms)
5. **EFO** - Experimental factors and biomedical concepts

**Additional Domain Coverage (200+ ontologies):**
- **Anatomy**: UBERON, FMA (Foundational Model of Anatomy), CL (Cell Ontology)
- **Molecular Biology**: PR (Protein Ontology), SO (Sequence Ontology), MI (Molecular Interactions)
- **Clinical**: ORDO (Rare Diseases), DOID (Disease Ontology), SYMP (Symptom Ontology)
- **Organisms**: NCBITaxon (Taxonomy), FBbt (Drosophila), WBbt (C. elegans), ZFIN (Zebrafish)
- **Environment**: ENVO (Environment Ontology), PATO (Quality Ontology)
- **Agriculture**: TO (Trait Ontology), PO (Plant Ontology), AGRO (Agronomy Ontology)
- **Imaging**: DICOM, RadLex
- **And 180+ more specialized ontologies**

Browse all ontologies: https://www.ebi.ac.uk/ols4/ontologies

### Available via LLM Knowledge (Suggestions)

The agent leverages Claude's training data knowledge for these ontologies:

1. **MedDRA** - Medical Dictionary for Regulatory Activities (adverse events, medical history)
2. **SNOMED CT** - Systematized Nomenclature of Medicine - Clinical Terms
3. **ICD-10/11** - International Classification of Diseases
4. **RxNorm** - Normalized drug names and clinical drugs
5. **LOINC** - Logical Observation Identifiers Names and Codes (lab tests)
6. **CPT** - Current Procedural Terminology (procedures and services)

**Important Distinction:**
- **OLS codes** = Authoritative, real-time API lookups from official sources
- **LLM codes** = Suggestions based on training data, require verification for production use

## Source Transparency & Prioritization

**CRITICAL**: The agent ALWAYS prioritizes authoritative OLS lookups over LLM suggestions and clearly indicates which source is used.

### Transparency in Responses

The agent will always include source attribution:

**OLS (Authoritative) responses:**
- "I found MONDO:0005068 for myocardial infarction from EBI OLS (authoritative source)."
- "According to EBI OLS, the ChEBI ID for aspirin is CHEBI:15365."

**LLM Knowledge (Suggestions) responses:**
- "Based on my training data, the MedDRA code is likely 10028596. Note: This is a suggestion - please verify with the official MedDRA browser for production use."
- "My training data suggests ICD-10 code E11. Verify with authoritative sources."

## LLM Knowledge vs Authoritative Lookups

The agent has two complementary ways to access ontology codes, with OLS always prioritized:

### Option 1: LLM Training Knowledge (`suggest_ontology_codes`)

**Advantages:**
- ✅ Fast - no external API calls
- ✅ Works offline or when OLS unavailable
- ✅ Covers ontologies not in OLS (MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC)
- ✅ Good for preliminary mappings and pre-filtering

**Limitations:**
- ⚠️ Based on training data (cutoff: January 2025)
- ⚠️ Not connected to live ontology databases
- ⚠️ Should be verified with authoritative sources for production use
- ⚠️ May have gaps or outdated codes

**Best for:**
- Quick suggestions for common terms
- MedDRA/SNOMED/ICD/RxNorm codes (not in OLS)
- Pre-filtering before detailed OLS lookup
- Offline or rapid-response scenarios

### Option 2: OLS API Lookups (`ols_search_terms`)

**Advantages:**
- ✅ Authoritative - directly from EBI OLS database
- ✅ Up-to-date with latest ontology versions
- ✅ Complete hierarchies and relationships
- ✅ Production-ready for regulatory/clinical use
- ✅ 200+ ontologies supported

**Limitations:**
- ⚠️ Requires external API call (latency)
- ⚠️ Doesn't include MedDRA, SNOMED CT, ICD-10/11, RxNorm
- ⚠️ Requires OLS MCP server to be deployed

**Best for:**
- Production/regulatory use cases
- MONDO, ChEBI, HPO, GO, EFO lookups
- When complete hierarchy is needed
- Critical mappings requiring verification

### Recommended Strategy

**ALWAYS prioritize OLS over LLM knowledge:**

1. **FIRST**: Try `ols_search_terms` for ALL disease, chemical, gene, phenotype queries
   - Label results: "From EBI OLS (authoritative)"
   - Use for MONDO, ChEBI, HPO, GO, EFO, and 200+ ontologies
2. **SECOND**: Use `suggest_ontology_codes` ONLY for specific requests:
   - MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC codes
   - Label results: "Based on training data - verify with authoritative source"
3. **Transparency**: ALWAYS indicate source in responses
4. **Production use**: Recommend OLS results for critical/regulatory applications

## Tool Selection: OLS-First Decision Tree

The agent follows this decision tree for tool selection:

```
User Query
    ↓
Is it about diseases, chemicals, genes, phenotypes, anatomy?
    ↓ YES
    ├─→ Use OLS tools (ols_search_terms)
    │   └─→ Inform user: "From EBI OLS (authoritative)"
    ↓ NO
    ↓
Is it SPECIFICALLY about MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC?
    ↓ YES
    ├─→ Use suggest_ontology_codes
    │   └─→ Inform user: "Based on training data - verify with authoritative source"
    ↓ NO
    ↓
Try OLS first
    ├─→ If found: Use OLS result
    └─→ If not found: Try LLM knowledge as fallback
```

## Tool Workflow

The agent follows an intelligent OLS-first workflow based on query complexity:

### Simple Lookup Workflow
```
User Query: "What is the MONDO ID for diabetes?"
    ↓
ols_search_terms("diabetes", ontology="mondo")
    ↓
Return: MONDO:0005015 - diabetes mellitus
```

### Complex Multi-Term Workflow
```
User Query: "Standardize: heart attack, MI, stroke"
    ↓
extract_entities(query) → Identify: heart attack (DISEASE), MI (DISEASE), stroke (DISEASE)
    ↓
For each entity: ols_search_terms(entity_text)
    ↓
Return standardized codes for all terms
```

### Downstream Agent Workflow
```
User Query: "Find clinical trials for lymphocytic leukemia with IL-23"
    ↓
extract_entities(query) → ["lymphocytic leukemia" (DISEASE), "IL-23" (GENE)]
    ↓
For each entity: ols_search_terms(entity_text, ontology)
    ↓
generate_standardized_query(original_query, entities, ontology_results)
    ↓
Return: Structured query with codes, intent, and filters for clinical trials agent
```

The agent automatically determines the appropriate workflow based on query characteristics.

## Deployment Instructions

### Step 1: Deploy OLS MCP Server

Deploy the Ontology Lookup Service MCP Server:

```bash
cd agents_catalog/34-Terminology-agent
python deploy_ols_mcp_server.py --stack-name terminology-agent
python test_ols_client.py  # Verify deployment
```

This step is required before deploying the backend agent.

### Step 2: Deploy Terminology Agent

Deploy the full backend with the terminology agent:

```bash
cd infra-cdk
npm install
cdk deploy
```

This will deploy:
- AgentCore Runtime with `terminology_agent_with_ols.py`
- Gateway with authentication
- Memory and DynamoDB tables
- API Gateway for frontend

### Step 3: Deploy Frontend

```bash
cd ..
python scripts/deploy-frontend.py
```

### Step 4: Test the Agent

Test the deployed agent with automated medical terminology tests:

```bash
# Run comprehensive test suite (remote agent)
uv run test-scripts/test-agent.py --test-suite

# Interactive chat mode (for manual testing)
uv run test-scripts/test-agent.py

# Local testing (requires agent running on localhost:8080)
uv run test-scripts/test-agent.py --local --test-suite
```

The test suite will:
- Run 5 automated medical terminology tests
- Test OLS integration (term lookup, hierarchies, multi-ontology search)
- Verify tool usage and responses
- Show pass/fail results with timing

You can also access via the frontend URL:
```bash
aws cloudformation describe-stacks --stack-name terminology-agent \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendURL`].OutputValue' --output text
```

## Testing Examples

### Example 1: Simple Term Lookup (OLS - Authoritative)

```
User: "What is the MONDO ID for diabetes?"
Agent: [Uses ols_search_terms - authoritative OLS lookup]

       I found MONDO:0005015 for diabetes mellitus from EBI OLS (authoritative source).

       This is the official disease classification code used internationally.
```

### Example 2: Entity Extraction from Complex Query

```
User: "Show me clinical trials for lymphocytic leukemia with IL-23 expression in breast tissue"
Agent: [Uses extract_entities]

       Extracted entities:
       - "lymphocytic leukemia" (DISEASE, confidence: 0.95)
       - "IL-23" (GENE, confidence: 0.92)
       - "breast tissue" (ANATOMY, confidence: 0.88)

       [Then uses ols_search_terms for each entity]

       Results:
       - lymphocytic leukemia → MONDO:0004948 (lymphoid leukemia)
       - IL-23 → Found in GO and gene ontologies
       - breast tissue → UBERON:0000310 (breast)
```

### Example 3: Hierarchical Exploration

```
User: "Show me the parent and child terms for MONDO:0005068"
Agent: [Uses ols_get_term_info, ols_get_term_ancestors, ols_get_term_children]

       Term: myocardial infarction (MONDO:0005068)

       Parents:
       - acute coronary syndrome (MONDO:0005023)
       - heart disease (MONDO:0005267)

       Children:
       - ST elevation myocardial infarction
       - non-ST elevation myocardial infarction
```

### Example 4: Multi-Ontology Search

```
User: "Find 'insulin' in ChEBI and GO ontologies"
Agent: [Uses ols_search_terms with ontology filter]

       ChEBI Results:
       - CHEBI:145810 - insulin

       GO Results:
       - GO:0005179 - hormone activity (insulin)
       - GO:0042593 - glucose homeostasis
```

### Example 5: MedDRA Code Suggestion (LLM Knowledge - with transparency)

```
User: "What's the MedDRA code for myocardial infarction?"
Agent: [Uses suggest_ontology_codes - LLM training data]

       Based on my training data, the likely MedDRA code for myocardial infarction is:

       - **10028596**: Myocardial infarction (PT - Preferred Term)
       - 10028597: Acute myocardial infarction (PT)

       ⚠️ Important: These are suggestions from my training data (cutoff: January 2025).
       For production use, please verify with the official MedDRA browser at:
       https://www.meddra.org/

       Note: MedDRA is not available through EBI OLS, which is why I'm using
       training data suggestions rather than authoritative lookups.

       Would you also like me to check related ontologies in OLS (like MONDO
       for disease classification)?
```

### Example 6: Comprehensive Multi-Ontology Mapping (with clear source attribution)

```
User: "Map diabetes mellitus to all relevant ontologies"
Agent: [Uses OLS FIRST, then LLM knowledge for ontologies not in OLS]

       ## Authoritative Sources (from EBI OLS):

       **MONDO** (Disease Classification):
       - MONDO:0005015: diabetes mellitus
       - Child terms: type 1 diabetes (MONDO:0005147), type 2 diabetes (MONDO:0005148),
         gestational diabetes (MONDO:0005406)
       ✓ Source: EBI OLS - authoritative, production-ready

       **ChEBI** (Chemical Entities):
       - Related compounds: glucose, insulin
       ✓ Source: EBI OLS - authoritative

       ## Training Data Suggestions (verify before production use):

       **MedDRA** (Regulatory):
       - 10012601: Diabetes mellitus (PT)
       - SOC: Metabolism and nutrition disorders
       ⚠️ Source: Training data - verify with official MedDRA browser

       **ICD-10** (Diagnosis Codes):
       - E11: Type 2 diabetes mellitus
       - E10: Type 1 diabetes mellitus
       ⚠️ Source: Training data - verify with official ICD-10 sources

       **Recommendation**: Use MONDO codes (MONDO:0005015) for production systems
       as they are authoritative and up-to-date. Verify MedDRA and ICD-10 codes
       with official sources before use in regulatory contexts.
```

### Example 7: Standardized Query for Downstream Agent

```
User: "Prepare a query for clinical trials agent: lymphocytic leukemia"
Agent: [Uses extract_entities → ols_search_terms → generate_standardized_query]

       {
         "original_query": "lymphocytic leukemia",
         "standardized_query": {
           "entities": [{
             "original_text": "lymphocytic leukemia",
             "entity_type": "DISEASE",
             "standardized_terms": [{
               "ontology": "MONDO",
               "code": "MONDO:0004948",
               "preferred_label": "lymphoid leukemia",
               "synonyms": ["lymphocytic leukemia", "lymphoid leukaemia"]
             }],
             "confidence": 0.95
           }],
           "query_intent": "clinical_trial_search",
           "suggested_filters": {
             "disease_codes": ["MONDO:0004948"],
             "include_subtypes": true
           }
         },
         "metadata": {
           "tools_used": ["extract_entities", "ols_search_terms", "generate_standardized_query"],
           "confidence_score": 0.95,
           "warnings": []
         }
       }
```

## Environment Variables

The agent requires these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `STACK_NAME` | CDK stack name | `terminology-agent` |
| `MEMORY_ID` | AgentCore Memory ID | From CDK output |
| `AWS_DEFAULT_REGION` | AWS region | `us-west-2` |

These are automatically configured by the CDK deployment.

## Troubleshooting

### Agent doesn't use OLS tools

**Check 1**: Verify OLS MCP server deployment
```bash
python check_ols_mcp_deployment.py
```

**Check 2**: Verify SSM parameters exist
```bash
aws ssm get-parameter --name /terminology-agent/ols-mcp-server/mcp-url
```

**Check 3**: Check agent logs
```bash
aws logs tail /aws/lambda/terminology-agent-runtime --follow
```

### OLS tools return errors

**Check 1**: Test OLS MCP server directly
```bash
python test_ols_client.py
```

**Check 2**: Check OLS server logs
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/ols_mcp_server-ChEmBE8HM3-DEFAULT --since 10m
```

## System Prompt Summary

The agent uses a comprehensive system prompt that:

1. **Defines its role** as a Medical Terminology Standardization Agent
2. **Lists available tools** and when to use them
3. **Provides structured response format** for consistency
4. **Prioritizes key ontologies** for medical/clinical use
5. **Includes usage examples** for common patterns

## Deployment Workflow

1. ✅ **Agent code created with OLS integration**
2. ✅ **CDK configured to use Terminology Agent**
3. **Ready to deploy:**
   - Run `python deploy_ols_mcp_server.py --stack-name terminology-agent` to deploy OLS
   - Run `cd infra-cdk && cdk deploy` to deploy backend
   - Run `python scripts/deploy-frontend.py` to deploy frontend
   - Test with medical terminology queries

## Sample Queries

### Current Capabilities (MVP - Phase 1)

The following queries are fully supported in the current deployment:

#### Basic Ontology Lookup
```
✅ "What is the MONDO ID for diabetes mellitus?"
✅ "Find the ChEBI identifier for aspirin"
✅ "Search for 'myocardial infarction' in medical ontologies"
✅ "What ontologies contain information about hypertension?"
```

#### Hierarchical Relationships
```
✅ "Show me the parent terms for type 2 diabetes"
✅ "List the child terms of cardiovascular disease"
✅ "What are the ancestors of MONDO:0005068?"
✅ "Find related terms in the disease hierarchy for asthma"
```

#### Multi-Ontology Search
```
✅ "Search for 'insulin' across ChEBI and GO ontologies"
✅ "Find 'breast cancer' in MONDO, HPO, and EFO"
✅ "Compare how different ontologies classify depression"
```

#### Term Standardization
```
✅ "Standardize these terms: heart attack, MI, myocardial infarction"
✅ "What's the official medical term for 'high blood pressure'?"
✅ "Convert 'Type 2 DM' to standardized ontology codes"
```

#### Ontology Metadata
```
✅ "Tell me about the MONDO ontology"
✅ "What medical domains does the HPO ontology cover?"
✅ "List all available disease ontologies"
```

#### Entity Extraction
```
✅ "Extract all medical entities from: 'Patient with diabetes on metformin presenting with chest pain'"
✅ "What entities are in this query: 'IL-23 expression in breast cancer tissue'"
✅ "Classify 'aspirin' in the context of 'patient taking aspirin for pain'"
```

#### LLM Knowledge-Based Suggestions (MedDRA, SNOMED, ICD, RxNorm)
```
✅ "What's the MedDRA code for myocardial infarction?"
✅ "Suggest ICD-10 codes for type 2 diabetes mellitus"
✅ "Find RxNorm identifiers for metformin"
✅ "What's the SNOMED CT code for hypertension?"
✅ "Give me LOINC codes for glucose measurement"
```

#### Comprehensive Multi-Ontology Mapping
```
✅ "Map diabetes to all relevant ontologies (MedDRA, ICD-10, MONDO)"
✅ "Provide complete terminology mapping for myocardial infarction"
✅ "Standardize 'heart attack' across MedDRA, ICD-10, SNOMED, and MONDO"
```

#### Standardized Query Generation
```
✅ "Generate standardized query for: 'Find trials for lymphocytic leukemia'"
✅ "Prepare this query for downstream agent: 'breast cancer with BRCA1 mutation'"
✅ "Create structured output with filters for: 'diabetes medications'"
```

#### Code Interpreter Integration
```
✅ "Parse this CSV file and standardize the disease terms"
✅ "Create a visualization of term frequency in this dataset"
✅ "Extract unique medical terms from this text and map to ontologies"
```

#### Exploring the Breadth of 200+ Ontologies
```
✅ "What ontologies are available in EBI OLS?"
✅ "Search for 'development' across all ontologies"
✅ "Find ontologies that cover plant biology"
✅ "What domains does the Cell Ontology (CL) cover?"
✅ "Search for 'apoptosis' in biological process ontologies"
✅ "Find agricultural ontologies for crop traits"
✅ "What environmental ontologies are available?"
✅ "Search for 'microbiome' across microbiology ontologies"
```

**Example Response (Demonstrating Breadth):**
```
User: "What ontologies are available for immunology research?"
Agent: [Uses ols_search_ontologies]

       EBI OLS provides 200+ ontologies covering diverse biomedical domains.
       For immunology, I found:

       1. **Immune Epitope Database (IEDB)** - Epitopes and immune responses
       2. **Cell Ontology (CL)** - Immune cell types (T cells, B cells, NK cells)
       3. **Protein Ontology (PR)** - Immune proteins (antibodies, cytokines)
       4. **Gene Ontology (GO)** - Immune processes (immune response, inflammation)
       5. **Human Phenotype Ontology (HPO)** - Immune-related phenotypes
       6. **MONDO** - Immune system diseases (autoimmune, immunodeficiency)
       7. **ChEBI** - Immunomodulatory compounds

       Explore all 200+ ontologies at: https://www.ebi.ac.uk/ols4/ontologies

       Would you like to search for specific immune-related terms across these ontologies?
```

**Example: Cross-Domain Ontology Search**
```
User: "Find 'insulin' across all relevant ontologies"
Agent: [Uses ols_search_terms without ontology filter - searches all 200+ ontologies]

       Found 'insulin' in 15+ ontologies spanning multiple domains:

       **Disease & Phenotype:**
       - HPO: Hyperinsulinism, insulin resistance phenotypes
       - MONDO: Insulin-related disorders

       **Chemical & Drug:**
       - ChEBI: Insulin (protein hormone), insulin analogs
       - DrugBank: Insulin formulations and brands

       **Molecular & Biological:**
       - GO: Insulin receptor signaling, insulin secretion processes
       - PR: Insulin protein family members
       - UniProt: Insulin protein sequences

       **Anatomy:**
       - UBERON: Pancreatic beta cells (insulin-producing)
       - FMA: Islets of Langerhans

       **Model Organisms:**
       - DOID: Insulin-related diseases in disease ontology
       - MGI: Mouse insulin genes

       This demonstrates the interconnected nature of biomedical concepts across
       200+ ontologies. Source: EBI OLS (https://www.ebi.ac.uk/ols4/ontologies)
```

### Future Capabilities (Post-MVP)

The following queries will be supported in future releases:

#### Drug Dictionary Integration (Phase 2)
```
🔮 "What's the WHODrug code for metformin?"
🔮 "Find RxNorm identifiers for all diabetes medications"
🔮 "Map this drug name to ATC classification codes"
🔮 "Show me all formulations and strengths for lisinopril"
🔮 "What therapeutic category does atorvastatin belong to?"
```

#### CDISC Standards Integration (Phase 2)
```
🔮 "Map these variables to SDTM domains"
🔮 "Which ADaM dataset should contain time-to-event data?"
🔮 "Show me CDISC controlled terminology for adverse events"
🔮 "Generate Define-XML metadata for these clinical variables"
```

#### Internal Controlled Vocabulary (Phase 2)
```
🔮 "Map to our organization's internal terminology standards"
🔮 "What's the internal code for this medical procedure?"
🔮 "Standardize using our custom disease dictionary"
🔮 "Convert external codes to internal nomenclature"
```

#### Advanced Cross-Ontology Mapping (Phase 3)
```
🔮 "Map ICD-10 codes to SNOMED CT with confidence scores"
🔮 "Create bidirectional mappings between MedDRA and WHO-ART"
🔮 "Find approximate mappings when exact matches don't exist"
🔮 "Show mapping conflicts between LOINC and internal lab codes"
```

#### RAG Vector Store Integration (Phase 3)
```
🔮 "Semantic search for terms similar to 'chronic kidney disease'"
🔮 "Find related concepts using embedding similarity"
🔮 "Cluster similar medical terms from this dataset"
```

#### Knowledge Graph Queries (Phase 3)
```
🔮 "Traverse the disease pathway from diabetes to complications"
🔮 "Find all drugs that interact with warfarin via graph traversal"
🔮 "Show the complete relationship network for this gene"
```

#### Performance & Caching (Phase 3)
```
🔮 "Frequently used terms return within 100ms (from cache)"
🔮 "Support 50+ concurrent terminology lookup requests"
🔮 "Automatic cache invalidation on terminology updates"
```

#### Audit & Compliance (Phase 3)
```
🔮 "Show audit trail for all terminology mappings this month"
🔮 "Generate compliance report for mapping decisions"
🔮 "Log all disambiguation choices with confidence scores"
```

## Future Scope & Roadmap

The Terminology Agent is designed as a critical intermediary layer in a multi-agent healthcare and life sciences system. The roadmap builds on the current MVP foundation.

### Phase 1: MVP (Current - Completed) ✅

**Capabilities:**
- ✅ Entity recognition and extraction (LLM-powered with Bedrock Converse API)
  - Automatic entity type classification (DISEASE, DRUG, GENE, PROTEIN, etc.)
  - Confidence scoring for each extracted entity
  - Position tracking within original query
- ✅ Dual ontology access approach:
  - **EBI Ontology Lookup Service** (200+ ontologies via MCP) - Authoritative lookups
    * Term search, hierarchy exploration, ontology metadata
    * 7 OLS tools for comprehensive ontology access
    * MONDO, ChEBI, HPO, GO, EFO, and 200+ more
  - **LLM Training Knowledge** (via Claude Sonnet 4.5) - Suggestion-based
    * MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC, CPT
    * Fast suggestions from training data
    * Pre-filtering and offline scenarios
- ✅ Multi-tool architecture (MCP servers, Code Interpreter, LLM tools)
  - Gateway MCP tools for custom domain operations
  - OLS MCP tools for authoritative ontology lookup
  - LLM tools for entity extraction and code suggestions
  - Code Interpreter for data processing
- ✅ Standardized query generation for downstream agents
  - Structured output with codes, mappings, and metadata
  - Query intent inference (clinical_trial_search, biomarker_analysis, etc.)
  - Suggested filters generation (disease_codes, gene_symbols, etc.)
  - Confidence scoring and warning generation
- ✅ Error handling and graceful fallback
  - Graceful degradation when OLS unavailable
  - Fallback to LLM knowledge when APIs fail
  - Fallback responses on tool failures
- ✅ AgentCore Memory for conversation context
  - Session-based conversation history
  - Context preservation across interactions

**Tool Types Supported:**
- MCP servers (OLS for authoritative ontologies, Gateway for custom tools)
- LLM-powered tools (entity extraction, classification, code suggestions, standardization)
- Code Interpreter for data processing and visualization
- AgentCore Memory for conversation context

**Technologies:**
- Amazon Bedrock Converse API for entity extraction and code suggestions
- Claude Sonnet 4.5 for LLM operations with built-in medical ontology knowledge
- EBI OLS API (200+ ontologies) via MCP for authoritative lookups
- Strands framework for agent orchestration

**Coverage:**
- Authoritative via OLS: MONDO, ChEBI, HPO, GO, EFO, + 200+ ontologies
- LLM suggestions: MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC, CPT

### Phase 2: Medical Data Products (Q2 2025)

**New Integrations:**
1. **Drug Dictionaries**
   - WHODrug Global for pharmacovigilance
   - RxNorm for clinical drug names
   - ATC Classification for therapeutic categories
   - Support for multiple formulations, strengths, and ingredients

2. **Medical Ontologies**
   - MedDRA for adverse events and medical terminology
   - SNOMED CT for clinical concepts
   - ICD-10/11 for disease classification
   - LOINC for laboratory observations

3. **CDISC Standards**
   - SDTM domain mapping for clinical data
   - ADaM dataset structures for analysis
   - CDISC Controlled Terminology codelists
   - Define-XML metadata standards

4. **Internal Controlled Vocabulary**
   - Organization-specific terminology standards
   - Custom codes and nomenclature
   - Synonym and abbreviation mapping
   - Priority override of external sources

**Architecture Enhancements:**
- Multi-source terminology resolution
- Prioritization rules (internal → regulatory → public)
- Conflict detection and resolution

### Phase 3: Advanced Capabilities (Q3-Q4 2025)

**Cross-Ontology Mapping:**
- Bidirectional mappings between terminology systems
- Confidence scoring for approximate matches
- Mapping validation and conflict detection
- Support for one-to-many and many-to-many relationships

**Additional Tool Types:**
- RAG vector stores for semantic search
- Knowledge graphs for relationship traversal
- Hybrid search combining exact and semantic matching

**Performance & Scalability:**
- Intelligent caching with sub-100ms cache hits
- Support for 50+ concurrent requests
- Cache invalidation based on data source updates
- Distributed cache architecture

**Audit & Compliance:**
- Immutable audit logging for all mappings
- Traceability of terminology standardization decisions
- Compliance reporting for regulatory submissions
- User query and entity extraction logging

### Phase 4: Multi-Agent Integration (2026)

**Semantic Bridge Capabilities:**
- Act as intermediary between user queries and domain agents
- Route standardized queries to specialized agents:
  - Clinical trials agent
  - Pharmacovigilance agent
  - Medical literature agent
  - Real-world evidence agent
- Aggregate and harmonize results from multiple agents
- Maintain terminology consistency across agent interactions

**Query Translation:**
- Convert natural language to standardized domain queries
- Preserve user intent while adding terminology precision
- Generate domain-specific query formats (FHIR, GraphQL, etc.)

## Reference Files

- **Requirements**: `requirements.md` - Full requirements and roadmap
- **Agent Code**: `patterns/strands-single-agent/terminology_agent_with_ols.py`
- **Agent Testing**: `test-scripts/test-agent.py` - Interactive chat and automated test suite
- **OLS Deployment**: `deploy_ols_mcp_server.py`
- **OLS Testing**: `test_ols_client.py` - Test OLS MCP server
- **OLS Utilities**: `ols_utils.py` - Cognito M2M authentication
- **CDK Stack**: `infra-cdk/lib/backend-stack.ts`
- **Deployment Guide**: `docs/DEPLOYMENT.md`
- **Test Scripts Guide**: `test-scripts/README.md`

---

**Ready to deploy!** The Terminology Agent MVP is configured and ready for deployment. Follow the deployment instructions above to start standardizing medical terminology with 200+ ontologies. See the Future Scope section for upcoming capabilities in Phase 2-4.
