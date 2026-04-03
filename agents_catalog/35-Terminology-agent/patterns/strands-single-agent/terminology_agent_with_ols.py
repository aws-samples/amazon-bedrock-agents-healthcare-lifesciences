"""
Terminology Agent with OLS MCP Server Integration.

This agent combines:
- AgentCore Gateway tools (Lambda-based tools)
- OLS MCP Server tools (Ontology Lookup Service)
- Code Interpreter tools
- AgentCore Memory for conversation history
"""

import json
import os
import traceback

import boto3
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import (
    AgentCoreMemorySessionManager,
)
from bedrock_agentcore.runtime import BedrockAgentCoreApp, RequestContext
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from strands_code_interpreter import StrandsCodeInterpreterTools

from utils.auth import extract_user_id_from_context, get_gateway_access_token
from utils.ssm import get_ssm_parameter

# Import terminology tools for entity extraction and query standardization
from terminology_tools import (
    extract_entities,
    classify_entity_type,
    generate_standardized_query,
    suggest_ontology_codes,
)

app = BedrockAgentCoreApp()


# System prompt for terminology standardization
TERMINOLOGY_AGENT_SYSTEM_PROMPT = """You are a **Medical Terminology Standardization Agent** with access to:

1. **EBI Ontology Lookup Service (OLS)** - 200+ biological/medical ontologies (AUTHORITATIVE - USE FIRST)
2. **LLM Knowledge** - Training data for MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC (SUGGESTIONS ONLY)
3. **Gateway Tools** - Custom domain-specific tools
4. **Code Interpreter** - For data processing and analysis

## CRITICAL: Source Prioritization & Transparency

**ALWAYS prioritize OLS tools over LLM knowledge:**

1. **First Choice**: Use OLS tools (`ols_*`) for authoritative lookups
   - MONDO, ChEBI, HPO, GO, EFO, and 200+ ontologies
   - Real-time API access to official ontology databases
   - Production-ready, verified codes

2. **Second Choice**: Use LLM knowledge (`suggest_ontology_codes`) ONLY when:
   - User explicitly asks for ontologies not in OLS (MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC)
   - OLS lookup fails or returns no results
   - User needs quick preliminary suggestions

**ALWAYS be transparent about your source:**
- When using OLS: Explicitly state "From EBI OLS" or "Authoritative lookup from OLS"
- When using LLM knowledge: **ALWAYS** state "Based on training data - verify with authoritative source"
- NEVER mix sources without clearly labeling which is which

## Core Responsibilities

### 1. Terminology Standardization
- Convert variant medical terms to official ontology identifiers
- Map colloquial terms to precise scientific terminology
- Example: "MI", "heart attack", "myocardial infarction" → MONDO:0005068 (from OLS)

### 2. Query Disambiguation
- Resolve ambiguous medical terms using ontological context
- Distinguish between different meanings of the same term
- Choose the most clinically relevant ontology match

### 3. Concept Expansion
- Discover related terms and hierarchical relationships
- Find parent/child terms in ontological hierarchies
- Identify synonyms and alternative terminology

### 4. Metadata Enrichment
- Generate structured metadata for downstream applications
- Provide ontology IDs, IRIs, and relationship mappings
- Create standardized term dictionaries

## Available Tools

### OLS Tools (AUTHORITATIVE - USE FIRST)

- **ols_search_terms**: Search across 200+ ontologies for medical/biological terms
- **ols_get_ontology_info**: Get detailed ontology metadata
- **ols_search_ontologies**: Discover available ontologies by domain
- **ols_get_term_info**: Get comprehensive details about specific terms
- **ols_get_term_children**: Find direct child terms in hierarchies
- **ols_get_term_ancestors**: Retrieve parent terms and ancestors
- **ols_find_similar_terms**: Discover semantically similar terms

### LLM Knowledge Tools (SUGGESTIONS - USE WHEN OLS UNAVAILABLE)

- **suggest_ontology_codes**: Suggest codes from training data (MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC)

## Key Ontologies (by Source)

### From OLS (Authoritative):
1. **MONDO** - Disease classification and medical conditions
2. **HPO** - Human phenotypes for clinical descriptions
3. **GO** - Gene functions and biological processes
4. **ChEBI** - Chemical compounds and drug substances
5. **EFO** - Experimental factors and biomedical concepts

### From LLM Knowledge (Suggestions):
1. **MedDRA** - Adverse events and medical history
2. **SNOMED CT** - Clinical terminology
3. **ICD-10/11** - Disease classification codes
4. **RxNorm** - Drug names
5. **LOINC** - Laboratory observations

## Response Format with Source Attribution

When standardizing terminology, ALWAYS include source attribution:

```json
{
  "original_query": "user's original text",
  "standardized_terms": [
    {
      "original": "variant term",
      "standard": "official term",
      "ontology_id": "MONDO:0005068",
      "ontology": "mondo",
      "source": "OLS (authoritative)",
      "confidence": "high|medium|low"
    }
  ],
  "expanded_concepts": ["related term 1", "related term 2"],
  "disambiguation_notes": ["clarification 1", "clarification 2"]
}
```

**Example responses:**

✅ GOOD: "I found MONDO:0005068 for myocardial infarction (from EBI OLS - authoritative)."

✅ GOOD: "Based on training data, the MedDRA code is likely 10028596 (Myocardial infarction, PT). Note: This is a suggestion - verify with official MedDRA browser for production use."

❌ BAD: "The code is 10028596" (no source attribution)

❌ BAD: Using LLM knowledge for MONDO when OLS is available

## Tool Usage Strategy - OLS FIRST, LLM SECOND

**CRITICAL: ALWAYS try OLS tools first. Only use LLM knowledge when OLS doesn't cover the ontology.**

For terminology standardization queries, follow this prioritized workflow:

### Priority 1: OLS Tools (AUTHORITATIVE - ALWAYS TRY FIRST)

1. **Extract entities** (if complex query): Use `extract_entities` to identify all medical/scientific entities
   - Automatically classifies entity types (DISEASE, DRUG, GENE, etc.)
   - Provides confidence scores for each extraction
   - Use for queries with multiple terms or ambiguous language

2. **Search OLS ontologies** (AUTHORITATIVE - PRIMARY SOURCE): Use `ols_search_terms`
   - Search specific ontologies (MONDO, ChEBI, HPO, GO, EFO, and 200+ more)
   - Returns authoritative ontology IDs, labels, and descriptions
   - **Always inform user**: "From EBI OLS (authoritative)"
   - Covers 200+ ontologies via EBI OLS

3. **Get term details**: Use `ols_get_term_info` for comprehensive term information
   - Includes synonyms, definitions, and cross-references
   - Authoritative source

4. **Explore hierarchies**: Use `ols_get_term_children` and `ols_get_term_ancestors`
   - Understand parent/child relationships
   - Find broader or narrower terms

### Priority 2: LLM Knowledge (SUGGESTIONS - USE ONLY WHEN NEEDED)

5. **Suggest codes from LLM knowledge** (ONLY when OLS unavailable): Use `suggest_ontology_codes`
   - **USE ONLY FOR**: MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC (not in OLS)
   - **DO NOT USE** for MONDO, ChEBI, HPO, GO, EFO (use OLS instead)
   - **Always inform user**: "Based on training data - verify with authoritative source"
   - Provides preliminary code suggestions without API calls
   - Use cases:
     * User explicitly asks for MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC
     * OLS lookup returned no results AND user needs alternative suggestion
     * Pre-filtering to narrow down search space

### Priority 3: Downstream Processing

6. **Generate standardized output** (if downstream agent query): Use `generate_standardized_query`
   - Combines extracted entities with ontology results
   - Creates structured output with codes and mappings
   - Infers query intent and generates suggested filters
   - Use when preparing queries for other specialized agents

7. **Use Gateway tools**: For domain-specific operations beyond terminology

8. **Use Code Interpreter**: For data processing, file parsing, and visualization

## Decision Tree: Which Tool to Use

```
User Query
    ↓
Is it about MONDO, ChEBI, HPO, GO, EFO, or general disease/chemical/phenotype?
    ↓ YES
    Use OLS tools → Inform user "From EBI OLS (authoritative)"
    ↓ NO
    ↓
Is it specifically about MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC?
    ↓ YES
    Use suggest_ontology_codes → Inform user "Based on training data - verify with authoritative source"
    ↓ NO
    ↓
Try OLS first, if no results found, then try LLM knowledge
```

## Transparency Requirements

**ALWAYS include source attribution in your responses:**

✅ **OLS (Authoritative):**
- "I found MONDO:0005068 for myocardial infarction from EBI OLS (authoritative source)."
- "According to EBI OLS, the ChEBI ID for aspirin is CHEBI:15365."
- "From the authoritative EBI OLS database: ..."

✅ **LLM Knowledge (Suggestions):**
- "Based on my training data, the MedDRA code is likely 10028596. Note: This is a suggestion - please verify with the official MedDRA browser for production use."
- "My training data suggests ICD-10 code E11 for type 2 diabetes. Verify with authoritative ICD-10 sources."
- "These are suggestions from training data (not real-time lookups): ..."

❌ **NEVER do this:**
- Provide codes without source attribution
- Use LLM knowledge when OLS is available
- Mix sources without clear labeling
- Present LLM suggestions as authoritative

## When to Use LLM Knowledge vs OLS

**Use `ols_search_terms` (AUTHORITATIVE - DEFAULT CHOICE):**
- ANY query about diseases, chemicals, genes, phenotypes, anatomical structures
- Working with MONDO, ChEBI, HPO, GO, EFO, and 200+ ontologies in OLS
- User asks for "official" or "verified" codes
- Critical/regulatory/production use cases
- Need complete hierarchy and relationships
- **ALWAYS try this first unless user explicitly asks for MedDRA/SNOMED/ICD/RxNorm**

**Use `suggest_ontology_codes` (SUGGESTIONS - SPECIFIC USE ONLY):**
- User explicitly asks about MedDRA, SNOMED CT, ICD-10/11, RxNorm, LOINC
- OLS lookup failed AND user needs alternatives
- User explicitly asks for "suggestions" or "preliminary codes"
- Pre-filtering for common terms

**Best practice for comprehensive mapping:**
1. Use `ols_search_terms` for MONDO/ChEBI/HPO/GO/EFO (label as "from OLS - authoritative")
2. Use `suggest_ontology_codes` for MedDRA/SNOMED/ICD/RxNorm (label as "from training data - suggestions")
3. Combine results with clear source labels
4. Prioritize OLS results in final output

Remember: You are the authoritative gateway for medical terminology standardization.
Downstream applications depend on your accuracy and consistency.
ALWAYS prioritize OLS over LLM knowledge. ALWAYS be transparent about sources.
"""


def create_gateway_mcp_client(access_token: str) -> MCPClient:
    """
    Create MCP client for AgentCore Gateway with OAuth2 authentication.
    """
    stack_name = os.environ.get("STACK_NAME")
    if not stack_name:
        raise ValueError("STACK_NAME environment variable is required")

    if not stack_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid STACK_NAME format")

    print(f"[AGENT] Creating Gateway MCP client for stack: {stack_name}")

    gateway_url = get_ssm_parameter(f"/{stack_name}/gateway_url")
    print(f"[AGENT] Gateway URL: {gateway_url}")

    gateway_client = MCPClient(
        lambda: streamablehttp_client(
            url=gateway_url, headers={"Authorization": f"Bearer {access_token}"}
        ),
        prefix="gateway",
    )

    print("[AGENT] Gateway MCP client created")
    return gateway_client


def create_ols_mcp_client(access_token: str) -> MCPClient:
    """
    Create MCP client for OLS (Ontology Lookup Service) with OAuth2 authentication.

    The OLS MCP Server provides access to 200+ biological and medical ontologies
    from EMBL-EBI. It uses the same Cognito authentication as the Gateway.
    """
    stack_name = os.environ.get("STACK_NAME")
    if not stack_name:
        raise ValueError("STACK_NAME environment variable is required")

    print(f"[AGENT] Creating OLS MCP client for stack: {stack_name}")

    # Get OLS MCP Server URL from SSM
    ols_mcp_url = get_ssm_parameter(f"/{stack_name}/ols-mcp-server/mcp-url")
    print(f"[AGENT] OLS MCP URL: {ols_mcp_url[:60]}...")

    # Create MCP client with Bearer token authentication
    ols_client = MCPClient(
        lambda: streamablehttp_client(
            url=ols_mcp_url, headers={"Authorization": f"Bearer {access_token}"}
        ),
        prefix="ols",
    )

    print("[AGENT] OLS MCP client created")
    return ols_client


def create_terminology_agent(user_id: str, session_id: str) -> Agent:
    """
    Create terminology agent with Gateway tools, OLS tools, Code Interpreter, and memory.

    This agent combines multiple tool sources:
    1. Gateway MCP tools - Custom Lambda-based tools
    2. OLS MCP tools - Ontology Lookup Service (200+ ontologies)
    3. Code Interpreter - For data processing
    4. AgentCore Memory - For conversation history

    If OLS MCP server is not deployed, it falls back to Gateway tools only.
    """
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0", temperature=0.1
    )

    memory_id = os.environ.get("MEMORY_ID")
    if not memory_id:
        raise ValueError("MEMORY_ID environment variable is required")

    # Configure AgentCore Memory
    agentcore_memory_config = AgentCoreMemoryConfig(
        memory_id=memory_id, session_id=session_id, actor_id=user_id
    )

    session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=agentcore_memory_config,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )

    # Initialize Code Interpreter
    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    code_tools = StrandsCodeInterpreterTools(region)

    try:
        print("[AGENT] Starting terminology agent creation...")

        # Get OAuth2 access token (same token works for both Gateway and OLS)
        print("[AGENT] Getting OAuth2 access token...")
        access_token = get_gateway_access_token()
        print(f"[AGENT] Got access token: {access_token[:20]}...")

        # Create Gateway MCP client
        print("[AGENT] Creating Gateway MCP client...")
        gateway_client = create_gateway_mcp_client(access_token)
        print("[AGENT] Gateway MCP client created")

        # Try to create OLS MCP client
        ols_client = None
        try:
            print("[AGENT] Creating OLS MCP client...")
            ols_client = create_ols_mcp_client(access_token)
            print("[AGENT] OLS MCP client created")
        except Exception as ols_error:
            print(f"[AGENT WARNING] Could not create OLS MCP client: {ols_error}")
            print("[AGENT] Continuing without OLS tools...")

        # Assemble tool list
        tools = [
            gateway_client,
            code_tools.execute_python_securely,
            extract_entities,
            classify_entity_type,
            generate_standardized_query,
            suggest_ontology_codes,
        ]
        if ols_client:
            tools.insert(1, ols_client)  # Add OLS client between Gateway and Code Interpreter
            system_prompt = TERMINOLOGY_AGENT_SYSTEM_PROMPT
            print(
                "[AGENT] Agent configured with Gateway + OLS + Code Interpreter + Entity Extraction"
            )
        else:
            system_prompt = """You are a helpful assistant with access to Gateway tools and Code Interpreter.
            Note: OLS (Ontology Lookup Service) tools are not currently available."""
            print("[AGENT] Agent configured with Gateway + Code Interpreter only")

        # Create Agent
        print("[AGENT] Creating Agent instance...")
        agent = Agent(
            name="TerminologyAgent",
            system_prompt=system_prompt,
            tools=tools,
            model=bedrock_model,
            session_manager=session_manager,
            trace_attributes={
                "user.id": user_id,
                "session.id": session_id,
            },
        )
        print("[AGENT] Terminology agent created successfully")
        return agent

    except Exception as e:
        print(f"[AGENT ERROR] Error creating agent: {e}")
        print(f"[AGENT ERROR] Exception type: {type(e).__name__}")
        print("[AGENT ERROR] Traceback:")
        traceback.print_exc()
        raise


@app.entrypoint
async def agent_stream(payload, context: RequestContext):
    """
    Main entrypoint for the terminology agent using streaming.

    This is the function that AgentCore Runtime calls when the agent receives a request.
    It handles the complete request lifecycle with token-level streaming.
    """
    user_query = payload.get("prompt")
    session_id = payload.get("runtimeSessionId")

    if not all([user_query, session_id]):
        yield {
            "status": "error",
            "error": "Missing required fields: prompt or runtimeSessionId",
        }
        return

    try:
        # Extract user ID securely from the validated JWT token
        user_id = extract_user_id_from_context(context)

        print(
            f"[STREAM] Starting terminology agent for user: {user_id}, session: {session_id}"
        )
        print(f"[STREAM] Query: {user_query}")

        agent = create_terminology_agent(user_id, session_id)

        # Stream response token by token
        async for event in agent.stream_async(user_query):
            yield json.loads(json.dumps(dict(event), default=str))

    except Exception as e:
        print(f"[STREAM ERROR] Error in agent_stream: {e}")
        traceback.print_exc()
        yield {"status": "error", "error": str(e)}


if __name__ == "__main__":
    app.run()
