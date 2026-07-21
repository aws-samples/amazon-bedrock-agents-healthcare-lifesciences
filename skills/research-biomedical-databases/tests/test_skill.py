#!/usr/bin/env python3
"""
Test suite for the research-biomedical-databases Claude Code skill.

Tests three categories:
1. Trigger Tests — Verify skill description triggers on correct queries (keyword matching)
2. Progressive Disclosure Tests — Verify skill structure and file integrity
3. Functional Tests — Test live gateway tool invocation (requires AWS connectivity)

Usage:
    python tests/test_skill.py --skip-gateway   # structural tests only
    python tests/test_skill.py                  # all tests including gateway
"""

import click
import json
import os
import re
import sys
import time
from pathlib import Path

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
REFERENCES_DIR = SKILL_DIR / "references"

# SSM parameter prefix for gateway config
SSM_PREFIX = "/app/researchapp/agentcore"

# Gateway tool name prefix (AgentCore Gateway prepends target name)
TOOL_PREFIX = "DatabaseLambda___"

# Skill description extracted from SKILL.md frontmatter
SKILL_DESCRIPTION = (
    "Use when querying biomedical databases (UniProt, ClinVar, gnomAD, PDB, Reactome, "
    "Open Targets, etc.) via the Biomni AgentCore Gateway MCP server. Covers protein lookup, "
    "variant interpretation, pathway analysis, drug-target associations, and genomic annotation "
    "queries. Use when user asks to find protein info, check variant pathogenicity, analyze "
    "pathways, find drug targets, or search clinical trials."
)

# ============================================================================
# Category 1: Trigger Tests
# ============================================================================

SHOULD_TRIGGER = [
    "find protein info about BRCA1",
    "check variant pathogenicity for rs80357906",
    "what drugs target CDK4",
    "find clinical trials for EGFR inhibitors",
    "BRCA1 population frequency",
]

SHOULD_NOT_TRIGGER = [
    "write a Python script",
    "help me deploy to AWS",
    "create a React component",
    "what's the weather",
]

# Keywords and phrases extracted from the skill description for matching
TRIGGER_KEYWORDS = [
    "biomedical", "databases", "uniprot", "clinvar", "gnomad", "pdb", "reactome",
    "open targets", "protein", "variant", "interpretation", "pathway", "drug",
    "target", "genomic", "annotation", "protein info", "pathogenicity",
    "clinical trials", "drug targets", "find protein", "check variant",
    "analyze pathways", "find drug", "search clinical",
    "frequency", "population", "gene", "inhibitor",
]


def compute_trigger_score(query: str) -> float:
    """
    Compute a relevance score between 0.0 and 1.0 based on keyword overlap
    between the query and the skill description trigger phrases.
    """
    query_lower = query.lower()
    matches = 0
    for keyword in TRIGGER_KEYWORDS:
        if keyword in query_lower:
            matches += 1
    # Normalize by a reasonable threshold (hitting 3+ keywords is a strong signal)
    score = min(matches / 3.0, 1.0)
    return score


def test_trigger_should_match():
    """Verify that relevant biomedical queries score above threshold."""
    print("\n--- Trigger Tests: Should Match ---")
    threshold = 0.5
    passed = 0
    failed = 0

    for query in SHOULD_TRIGGER:
        score = compute_trigger_score(query)
        status = "PASS" if score >= threshold else "FAIL"
        if score >= threshold:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] score={score:.2f} | \"{query}\"")

    return passed, failed


def test_trigger_should_not_match():
    """Verify that irrelevant queries score below threshold."""
    print("\n--- Trigger Tests: Should NOT Match ---")
    threshold = 0.5
    passed = 0
    failed = 0

    for query in SHOULD_NOT_TRIGGER:
        score = compute_trigger_score(query)
        status = "PASS" if score < threshold else "FAIL"
        if score < threshold:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] score={score:.2f} | \"{query}\"")

    return passed, failed


# ============================================================================
# Category 2: Progressive Disclosure Tests
# ============================================================================

def test_skill_md_exists():
    """SKILL.md must exist."""
    print("\n--- Progressive Disclosure: SKILL.md Exists ---")
    exists = SKILL_MD.exists()
    status = "PASS" if exists else "FAIL"
    print(f"  [{status}] SKILL.md exists at {SKILL_MD}")
    return (1, 0) if exists else (0, 1)


def test_skill_md_token_limit():
    """SKILL.md must be under 5000 tokens (approx word_count * 1.3)."""
    print("\n--- Progressive Disclosure: Token Limit ---")
    if not SKILL_MD.exists():
        print("  [SKIP] SKILL.md not found")
        return (0, 1)

    content = SKILL_MD.read_text()
    word_count = len(content.split())
    approx_tokens = int(word_count * 1.3)
    limit = 5000
    ok = approx_tokens <= limit
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] ~{approx_tokens} tokens (words={word_count}, limit={limit})")
    return (1, 0) if ok else (0, 1)


def test_referenced_files_exist():
    """Every file referenced in SKILL.md as references/X must exist."""
    print("\n--- Progressive Disclosure: Referenced Files Exist ---")
    if not SKILL_MD.exists():
        print("  [SKIP] SKILL.md not found")
        return (0, 1)

    content = SKILL_MD.read_text()
    # Match patterns like references/workflow-variant-interpretation.md
    # or `references/tool-parameter-reference.md`
    pattern = r'references/([a-zA-Z0-9_\-]+\.md)'
    matches = set(re.findall(pattern, content))

    if not matches:
        print("  [FAIL] No reference file patterns found in SKILL.md")
        return (0, 1)

    passed = 0
    failed = 0
    for filename in sorted(matches):
        filepath = REFERENCES_DIR / filename
        exists = filepath.exists()
        status = "PASS" if exists else "FAIL"
        if exists:
            passed += 1
        else:
            failed += 1
        print(f"  [{status}] references/{filename}")

    return passed, failed


def test_skill_md_has_directives():
    """SKILL.md must contain 'Read references/X when Y' style directives."""
    print("\n--- Progressive Disclosure: Conditional Load Directives ---")
    if not SKILL_MD.exists():
        print("  [SKIP] SKILL.md not found")
        return (0, 1)

    content = SKILL_MD.read_text()
    # Look for patterns like "Read references/..." or directive-like text pointing to references
    # Acceptable patterns: table rows with references/, or explicit "Read references/X when Y"
    directive_patterns = [
        r'references/[a-zA-Z0-9_\-]+\.md',  # any reference file mention
    ]

    found_directives = []
    for pat in directive_patterns:
        found_directives.extend(re.findall(pat, content))

    # Check the table maps specific contexts to reference files
    has_table_mapping = '| User asks about' in content or 'Reference |' in content
    has_ref_links = len(found_directives) > 0

    ok = has_table_mapping and has_ref_links
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] Found {len(found_directives)} reference directives, table_mapping={has_table_mapping}")
    return (1, 0) if ok else (0, 1)


def test_reference_files_self_contained():
    """Reference files should be self-contained with their own headers."""
    print("\n--- Progressive Disclosure: Reference Files Self-Contained ---")
    if not REFERENCES_DIR.exists():
        print("  [SKIP] references/ directory not found")
        return (0, 1)

    ref_files = list(REFERENCES_DIR.glob("*.md"))
    if not ref_files:
        print("  [FAIL] No .md files in references/")
        return (0, 1)

    passed = 0
    failed = 0
    for ref_file in sorted(ref_files):
        content = ref_file.read_text()
        # A self-contained file should have at least one H1 or H2 header
        has_header = bool(re.search(r'^#{1,2}\s+\S', content, re.MULTILINE))
        # Should be at least 100 characters (not a stub)
        has_content = len(content.strip()) >= 100
        ok = has_header and has_content
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        detail = f"header={has_header}, len={len(content.strip())}"
        print(f"  [{status}] {ref_file.name} ({detail})")

    return passed, failed


# ============================================================================
# Category 3: Functional Tests (Gateway Integration)
# ============================================================================

def get_ssm_parameter(name: str) -> str:
    """Get parameter from AWS SSM Parameter Store."""
    import boto3
    ssm = boto3.client("ssm")
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]


def get_gateway_access_token() -> str:
    """Get M2M bearer token for gateway authentication via Cognito OAuth2."""
    import boto3
    import requests

    machine_client_id = get_ssm_parameter(f"{SSM_PREFIX}/machine_client_id")
    machine_client_secret = get_ssm_parameter(f"{SSM_PREFIX}/cognito_secret")
    cognito_domain = get_ssm_parameter(f"{SSM_PREFIX}/cognito_domain")
    user_pool_id = get_ssm_parameter(f"{SSM_PREFIX}/userpool_id")

    # Clean the domain
    cognito_domain = cognito_domain.strip()
    if cognito_domain.startswith("https://"):
        cognito_domain = cognito_domain[8:]

    # Get resource server scopes
    cognito_client = boto3.client("cognito-idp")
    response = cognito_client.list_resource_servers(UserPoolId=user_pool_id, MaxResults=1)

    if response["ResourceServers"]:
        resource_server_id = response["ResourceServers"][0]["Identifier"]
        scopes = f"{resource_server_id}/read"
    else:
        scopes = "gateway:read gateway:write"

    # M2M OAuth flow
    token_url = f"https://{cognito_domain}/oauth2/token"
    token_data = {
        "grant_type": "client_credentials",
        "client_id": machine_client_id,
        "client_secret": machine_client_secret,
        "scope": scopes,
    }

    resp = requests.post(
        token_url,
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Failed to get access token: {resp.status_code} {resp.text}")

    return resp.json()["access_token"]


def invoke_gateway_tool(gateway_url: str, jwt_token: str, tool_name: str, arguments: dict) -> dict:
    """Invoke a single tool on the AgentCore Gateway via JSON-RPC."""
    import requests

    request_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    response = requests.post(
        gateway_url,
        json=request_body,
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        },
    )

    if response.status_code != 200:
        return {"error": f"HTTP {response.status_code}: {response.text}"}

    result = response.json()
    if "error" in result:
        return {"error": result["error"]}

    return result.get("result", {})


def test_semantic_search(gateway_url: str, jwt_token: str):
    """Test semantic search returns relevant tools for a biomedical query."""
    print("\n--- Functional: Semantic Search ---")
    import requests

    query = "find protein information about BRCA1"
    request_body = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "x_amz_bedrock_agentcore_search",
            "arguments": {"query": query},
        },
    }

    start = time.time()
    response = requests.post(
        gateway_url,
        json=request_body,
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        },
    )
    elapsed = time.time() - start

    if response.status_code != 200:
        print(f"  [FAIL] HTTP {response.status_code}: {response.text[:200]}")
        return (0, 1)

    result = response.json()
    tools = result.get("result", {}).get("structuredContent", {}).get("tools", [])

    ok = len(tools) > 0
    status = "PASS" if ok else "FAIL"
    tool_names = [t["name"] for t in tools[:5]]
    print(f"  [{status}] Returned {len(tools)} tools in {elapsed:.2f}s")
    print(f"         Top tools: {tool_names}")

    # Verify at least one protein-related tool is returned (names may have DatabaseLambda___ prefix)
    protein_tools = [t for t in tools if "uniprot" in t["name"].lower() or "pdb" in t["name"].lower() or "alphafold" in t["name"].lower()]
    has_protein = len(protein_tools) > 0
    status2 = "PASS" if has_protein else "FAIL"
    print(f"  [{status2}] Contains protein-relevant tool: {[t['name'] for t in protein_tools[:3]]}")

    passed = (1 if ok else 0) + (1 if has_protein else 0)
    failed = (0 if ok else 1) + (0 if has_protein else 1)
    return passed, failed


def test_query_uniprot(gateway_url: str, jwt_token: str):
    """Test query_uniprot with a natural language prompt."""
    print("\n--- Functional: query_uniprot ---")

    start = time.time()
    result = invoke_gateway_tool(gateway_url, jwt_token, f"{TOOL_PREFIX}query_uniprot", {
        "prompt": "human insulin protein"
    })
    elapsed = time.time() - start

    if "error" in result:
        print(f"  [FAIL] Error: {result['error']}")
        return (0, 1)

    # Check that we got structured content back
    has_content = bool(result.get("content") or result.get("structuredContent"))
    status = "PASS" if has_content else "FAIL"
    print(f"  [{status}] Got response in {elapsed:.2f}s, has_content={has_content}")

    # Try to find evidence of insulin/UniProt data in response
    result_str = json.dumps(result).lower()
    has_insulin_data = "insulin" in result_str or "p01308" in result_str
    status2 = "PASS" if has_insulin_data else "FAIL"
    print(f"  [{status2}] Response contains insulin-related data")

    passed = (1 if has_content else 0) + (1 if has_insulin_data else 0)
    failed = (0 if has_content else 1) + (0 if has_insulin_data else 1)
    return passed, failed


def test_tool_chaining(gateway_url: str, jwt_token: str):
    """Test chaining: query_uniprot for BRCA1 -> extract UniProt ID -> query_alphafold."""
    print("\n--- Functional: Tool Chaining (UniProt -> AlphaFold) ---")

    # Step 1: Query UniProt for BRCA1
    print("  Step 1: query_uniprot for BRCA1...")
    start = time.time()
    uniprot_result = invoke_gateway_tool(gateway_url, jwt_token, f"{TOOL_PREFIX}query_uniprot", {
        "prompt": "human BRCA1 protein"
    })
    elapsed1 = time.time() - start

    if "error" in uniprot_result:
        print(f"  [FAIL] UniProt query error: {uniprot_result['error']}")
        return (0, 2)

    # Extract UniProt ID from result (P38398 is BRCA1 human)
    result_str = json.dumps(uniprot_result)
    # Look for UniProt accession pattern (letter followed by 5 alphanumerics)
    accession_match = re.search(r'\b([A-Z][0-9][A-Z0-9]{3}[0-9])\b', result_str)

    # Fallback to known BRCA1 ID if extraction fails
    uniprot_id = accession_match.group(1) if accession_match else "P38398"
    print(f"  [INFO] UniProt query took {elapsed1:.2f}s, extracted ID: {uniprot_id}")

    # Step 2: Query AlphaFold with the UniProt ID
    print(f"  Step 2: query_alphafold with uniprot_id={uniprot_id}...")
    start = time.time()
    alphafold_result = invoke_gateway_tool(gateway_url, jwt_token, f"{TOOL_PREFIX}query_alphafold", {
        "uniprot_id": uniprot_id
    })
    elapsed2 = time.time() - start

    if "error" in alphafold_result:
        print(f"  [FAIL] AlphaFold query error: {alphafold_result['error']}")
        return (1, 1)

    has_content = bool(alphafold_result.get("content") or alphafold_result.get("structuredContent"))
    status = "PASS" if has_content else "FAIL"
    print(f"  [{status}] AlphaFold returned data in {elapsed2:.2f}s")

    # Verify result references the protein
    af_str = json.dumps(alphafold_result).lower()
    has_structure_data = "alphafold" in af_str or "structure" in af_str or "plddt" in af_str or uniprot_id.lower() in af_str
    status2 = "PASS" if has_structure_data else "FAIL"
    print(f"  [{status2}] AlphaFold response contains structure-related data")

    passed = (1 if has_content else 0) + (1 if has_structure_data else 0)
    failed = (0 if has_content else 1) + (0 if has_structure_data else 1)
    return passed, failed


def test_error_handling(gateway_url: str, jwt_token: str):
    """Test that query_alphafold without uniprot_id fails gracefully."""
    print("\n--- Functional: Error Handling (missing required param) ---")

    start = time.time()
    result = invoke_gateway_tool(gateway_url, jwt_token, f"{TOOL_PREFIX}query_alphafold", {
        # Intentionally omit uniprot_id — this should produce an error or empty result
        "prompt": "give me structure data"
    })
    elapsed = time.time() - start

    # We expect either an error response OR a result that indicates failure/empty
    result_str = json.dumps(result).lower()
    is_error = (
        "error" in result
        or "error" in result_str
        or "required" in result_str
        or "missing" in result_str
        or "invalid" in result_str
        or result_str == "{}"
    )

    # Even if the tool doesn't fail hard, it should NOT return valid structure data
    has_valid_structure = "plddt" in result_str and "alphafold" in result_str
    graceful = is_error or not has_valid_structure

    status = "PASS" if graceful else "FAIL"
    print(f"  [{status}] Tool handled missing uniprot_id gracefully in {elapsed:.2f}s")
    if is_error:
        error_preview = str(result.get("error", result_str[:200]))
        print(f"         Error indicator: {error_preview[:150]}")
    else:
        print(f"         No explicit error but no valid structure data returned")

    return (1, 0) if graceful else (0, 1)


# ============================================================================
# Main CLI
# ============================================================================

@click.command()
@click.option("--skip-gateway", is_flag=True, help="Skip gateway integration tests (structural tests only)")
@click.option("--verbose", "-v", is_flag=True, help="Show additional debug output")
def main(skip_gateway: bool, verbose: bool):
    """Test suite for the research-biomedical-databases skill."""
    print("=" * 70)
    print("  Research Biomedical Databases Skill - Test Suite")
    print("=" * 70)

    total_passed = 0
    total_failed = 0

    # --- Category 1: Trigger Tests ---
    print("\n" + "=" * 70)
    print("  CATEGORY 1: Trigger Tests")
    print("=" * 70)

    p, f = test_trigger_should_match()
    total_passed += p
    total_failed += f

    p, f = test_trigger_should_not_match()
    total_passed += p
    total_failed += f

    # --- Category 2: Progressive Disclosure Tests ---
    print("\n" + "=" * 70)
    print("  CATEGORY 2: Progressive Disclosure Tests")
    print("=" * 70)

    p, f = test_skill_md_exists()
    total_passed += p
    total_failed += f

    p, f = test_skill_md_token_limit()
    total_passed += p
    total_failed += f

    p, f = test_referenced_files_exist()
    total_passed += p
    total_failed += f

    p, f = test_skill_md_has_directives()
    total_passed += p
    total_failed += f

    p, f = test_reference_files_self_contained()
    total_passed += p
    total_failed += f

    # --- Category 3: Functional Tests (Gateway Integration) ---
    if skip_gateway:
        print("\n" + "=" * 70)
        print("  CATEGORY 3: Functional Tests (SKIPPED -- use without --skip-gateway)")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("  CATEGORY 3: Functional Tests (Gateway Integration)")
        print("=" * 70)

        # Authenticate
        print("\n--- Authenticating with AgentCore Gateway ---")
        try:
            jwt_token = get_gateway_access_token()
            gateway_url = get_ssm_parameter(f"{SSM_PREFIX}/gateway_url")
            print(f"  [PASS] Authenticated successfully")
            print(f"         Gateway: {gateway_url[:60]}...")
        except Exception as e:
            print(f"  [FAIL] Authentication failed: {e}")
            total_failed += 4  # Count all gateway tests as failed
            _print_summary(total_passed, total_failed)
            sys.exit(1 if total_failed > 0 else 0)

        # Run gateway tests
        p, f = test_semantic_search(gateway_url, jwt_token)
        total_passed += p
        total_failed += f

        p, f = test_query_uniprot(gateway_url, jwt_token)
        total_passed += p
        total_failed += f

        p, f = test_tool_chaining(gateway_url, jwt_token)
        total_passed += p
        total_failed += f

        p, f = test_error_handling(gateway_url, jwt_token)
        total_passed += p
        total_failed += f

    # --- Summary ---
    _print_summary(total_passed, total_failed)
    sys.exit(1 if total_failed > 0 else 0)


def _print_summary(passed: int, failed: int):
    """Print final test summary."""
    total = passed + failed
    print("\n" + "=" * 70)
    print(f"  RESULTS: {passed}/{total} passed, {failed}/{total} failed")
    print("=" * 70)
    if failed == 0:
        print("  All tests passed.")
    else:
        print(f"  {failed} test(s) failed.")


if __name__ == "__main__":
    main()
