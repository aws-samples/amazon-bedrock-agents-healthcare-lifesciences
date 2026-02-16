"""Tests for MCP Server Gateway format handling"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from mcp_server import app

client = TestClient(app)

@patch('mcp_server.grpc_client')
def test_gateway_prefix_removal(mock_grpc):
    """Test Gateway prefix removal (gateway-id___tool_name -> tool_name)"""
    mock_grpc.list_devices.return_value = {"devices": []}
    
    response = client.post("/mcp", json={
        "name": "gateway-abc123___list_devices",
        "arguments": {}
    })
    
    assert response.status_code == 200
    assert mock_grpc.list_devices.called

@patch('mcp_server.grpc_client')
def test_empty_event_handling(mock_grpc):
    """Test empty event defaults to list_devices"""
    mock_grpc.list_devices.return_value = {"devices": []}
    
    response = client.post("/mcp", json={})
    
    assert response.status_code == 200
    assert mock_grpc.list_devices.called

@patch('mcp_server.grpc_client')
def test_arguments_only_format(mock_grpc):
    """Test arguments-only format defaults to list_devices"""
    mock_grpc.list_devices.return_value = {"devices": []}
    
    response = client.post("/mcp", json={"some_arg": "value"})
    
    assert response.status_code == 200
    assert mock_grpc.list_devices.called
