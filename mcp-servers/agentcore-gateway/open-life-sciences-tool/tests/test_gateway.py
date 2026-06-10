"""
Integration tests for Open Life Sciences MCP Gateway.

This test suite verifies OAuth2 authentication, tool invocation,
and error handling via the AgentCore Gateway endpoint.
"""

import os
import boto3
import requests
import pytest


APP_NAME = os.environ.get("APP_NAME", "open-life-sciences-tool")
AWS_REGION = os.environ.get("AWS_REGION", boto3.Session().region_name or "us-west-2")

ssm = boto3.client("ssm", region_name=AWS_REGION)


def get_ssm_parameter(parameter_name: str, with_decryption: bool = False) -> str:
    """Retrieve parameter from SSM Parameter Store."""
    response = ssm.get_parameter(Name=parameter_name, WithDecryption=with_decryption)
    return response["Parameter"]["Value"]


def get_oauth2_token() -> str:
    """Obtain OAuth2 access token using Cognito client credentials flow."""
    client_id = get_ssm_parameter(f"/app/{APP_NAME}/agentcore/machine_client_id")
    client_secret = get_ssm_parameter(f"/app/{APP_NAME}/agentcore/cognito_secret", with_decryption=True)
    cognito_domain = get_ssm_parameter(f"/app/{APP_NAME}/agentcore/cognito_domain")
    auth_scope = get_ssm_parameter(f"/app/{APP_NAME}/agentcore/cognito_auth_scope")
    
    cognito_domain_clean = cognito_domain.replace("https://", "")
    token_url = f"https://{cognito_domain_clean}/oauth2/token"
    
    response = requests.post(
        token_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": auth_scope,
        },
        timeout=30,
    )
    
    response.raise_for_status()
    token_data = response.json()
    return token_data["access_token"]


def get_gateway_url() -> str:
    """Retrieve Gateway URL from SSM."""
    return get_ssm_parameter(f"/app/{APP_NAME}/agentcore/gateway_url")


def mcp_call(gateway_url: str, token: str, method: str, params: dict = None) -> dict:
    """
    Make an MCP JSON-RPC call to the Gateway.
    
    Args:
        gateway_url: Gateway endpoint URL
        token: OAuth2 access token
        method: MCP method name (e.g., "tools/call", "tools/list")
        params: Method parameters
    
    Returns:
        JSON-RPC response dict
    """
    body = {
        "jsonrpc": "2.0",
        "method": method,
        "id": 1
    }
    if params:
        body["params"] = params
    
    response = requests.post(
        gateway_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=60,
    )
    
    response.raise_for_status()
    return response.json()


class TestGatewayToolInvocation:
    """Test MCP tool invocation via Gateway."""
    
    def test_uniprot_search(self):
        """
        Verify database tool invocation via Gateway.
        
        This test obtains an OAuth2 token and invokes the uniprot_search
        tool via the Gateway using MCP JSON-RPC protocol. It asserts that
        the response status is 200 and that the results format matches the
        Tool Schema expectations.
        
        Validates: Requirements 10.2
        """
        gateway_url = get_gateway_url()
        token = get_oauth2_token()
        
        # Call tool using MCP JSON-RPC protocol
        result = mcp_call(
            gateway_url,
            token,
            "tools/call",
            {
                "name": "DatabaseLambda___uniprot_search",
                "arguments": {
                    "query": "TP53",
                    "max_results": 5
                }
            }
        )
        
        # Verify JSON-RPC response structure
        assert "result" in result, "Response should contain 'result' field"
        
        # Extract tool result
        tool_result = result["result"]
        
        # Verify result format (MCP tools return content array)
        assert "content" in tool_result, "Tool result should contain 'content' field"
        assert isinstance(tool_result["content"], list), "Content should be a list"
        
        # Verify content contains results
        if len(tool_result["content"]) > 0:
            content_item = tool_result["content"][0]
            assert content_item.get("type") == "text", "Content type should be 'text'"
            
            # Parse the text content (should be JSON)
            import json
            data = json.loads(content_item["text"])
            assert "results" in data, "Response should contain 'results' field"
            assert isinstance(data["results"], list), "Results should be a list"
            
            if len(data["results"]) > 0:
                assert len(data["results"]) <= 5, "Should respect max_results parameter"
    
    def test_unknown_tool_returns_404(self):
        """
        Verify error handling for invalid tool names.
        
        This test invokes a non-existent tool via the Gateway and
        verifies that an error is returned with an appropriate
        error message.
        
        Validates: Requirements 10.3
        """
        gateway_url = get_gateway_url()
        token = get_oauth2_token()
        
        # Attempt to call non-existent tool
        try:
            result = mcp_call(
                gateway_url,
                token,
                "tools/call",
                {
                    "name": "nonexistent_tool_that_does_not_exist",
                    "arguments": {}
                }
            )
            
            # If we get a response, it should contain an error
            assert "error" in result, "Response should contain 'error' field for unknown tool"
            
        except requests.exceptions.HTTPError as e:
            # HTTP error is also acceptable (404 or 400)
            assert e.response.status_code in [400, 404], \
                f"Expected 400 or 404 for unknown tool, got {e.response.status_code}"
    
    def test_invalid_jwt_rejected(self):
        """
        Verify JWT validation rejects invalid tokens.
        
        This test attempts to invoke a tool with an invalid JWT token
        and verifies that the Gateway rejects the request with a 401
        Unauthorized status.
        
        Validates: Requirements 10.4
        """
        gateway_url = get_gateway_url()
        invalid_token = "invalid_token_that_should_fail_validation"
        
        # Attempt to call tool with invalid JWT
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            mcp_call(
                gateway_url,
                invalid_token,
                "tools/call",
                {
                    "name": "DatabaseLambda___uniprot_search",
                    "arguments": {
                        "query": "TP53",
                        "max_results": 5
                    }
                }
            )
        
        # Verify 401 Unauthorized
        assert exc_info.value.response.status_code == 401, \
            f"Expected 401 for invalid JWT, got {exc_info.value.response.status_code}"


class TestMultipleCategoryTools:
    """Test at least 5 tools across different categories."""
    
    def test_genomics_clinvar_search(self):
        """
        Test genomics tool: ClinVar search.
        
        Validates: Clinical/genomics database access.
        """
        gateway_url = get_gateway_url()
        token = get_oauth2_token()
        
        result = mcp_call(
            gateway_url,
            token,
            "tools/call",
            {
                "name": "DatabaseLambda___clinvar_search",
                "arguments": {
                    "query": "BRCA1",
                    "max_results": 3
                }
            }
        )
        
        assert "result" in result, "Response should contain 'result' field"
        tool_result = result["result"]
        assert "content" in tool_result, "Tool result should contain 'content' field"
    
    def test_proteomics_uniprot_search(self):
        """
        Test proteomics tool: UniProt search.
        
        Validates: Proteomics database access.
        """
        gateway_url = get_gateway_url()
        token = get_oauth2_token()
        
        result = mcp_call(
            gateway_url,
            token,
            "tools/call",
            {
                "name": "DatabaseLambda___uniprot_search",
                "arguments": {
                    "query": "TP53",
                    "max_results": 3
                }
            }
        )
        
        assert "result" in result, "Response should contain 'result' field"
        tool_result = result["result"]
        assert "content" in tool_result, "Tool result should contain 'content' field"
    
    def test_structural_pdb_search(self):
        """
        Test structural biology tool: PDB search.
        
        Validates: Structural database access.
        """
        gateway_url = get_gateway_url()
        token = get_oauth2_token()
        
        result = mcp_call(
            gateway_url,
            token,
            "tools/call",
            {
                "name": "DatabaseLambda___pdb_search",
                "arguments": {
                    "query": "hemoglobin",
                    "max_results": 3
                }
            }
        )
        
        assert "result" in result, "Response should contain 'result' field"
        tool_result = result["result"]
        assert "content" in tool_result, "Tool result should contain 'content' field"
    
    def test_clinical_drugbank_search(self):
        """
        Test clinical tool: DrugBank search.
        
        Validates: Clinical database access.
        """
        gateway_url = get_gateway_url()
        token = get_oauth2_token()
        
        result = mcp_call(
            gateway_url,
            token,
            "tools/call",
            {
                "name": "DatabaseLambda___drugbank_search",
                "arguments": {
                    "query": "aspirin"
                }
            }
        )
        
        assert "result" in result, "Response should contain 'result' field"
        tool_result = result["result"]
        assert "content" in tool_result, "Tool result should contain 'content' field"
    
    def test_genomics_ncbi_search(self):
        """
        Test genomics tool: NCBI search.
        
        Validates: Genomics database access via NCBI Entrez.
        """
        gateway_url = get_gateway_url()
        token = get_oauth2_token()
        
        result = mcp_call(
            gateway_url,
            token,
            "tools/call",
            {
                "name": "DatabaseLambda___ncbi_search",
                "arguments": {
                    "database": "gene",
                    "term": "BRCA2",
                    "max_results": 3
                }
            }
        )
        
        assert "result" in result, "Response should contain 'result' field"
        tool_result = result["result"]
        assert "content" in tool_result, "Tool result should contain 'content' field"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
