"""
IAM-authenticated HTTP client for MCP gateway using AWS SigV4 signing.
"""
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import httpx
from typing import AsyncIterator
from contextlib import asynccontextmanager


class IAMSignedHTTPClient:
    """HTTP client that signs requests with AWS SigV4 for IAM authentication."""
    
    def __init__(self, gateway_url: str, region: str = "us-east-1"):
        self.gateway_url = gateway_url
        self.region = region
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        
    def _sign_request(self, method: str, url: str, headers: dict, body: bytes = b""):
        """Sign an HTTP request using AWS SigV4."""
        request = AWSRequest(method=method, url=url, headers=headers, data=body)
        SigV4Auth(self.credentials, "bedrock-agentcore", self.region).add_auth(request)
        return dict(request.headers)
    
    async def post(self, endpoint: str, json_data: dict = None, headers: dict = None):
        """Make a signed POST request."""
        import json as json_lib
        
        url = f"{self.gateway_url}{endpoint}"
        body = json_lib.dumps(json_data).encode() if json_data else b""
        
        request_headers = headers or {}
        request_headers["Content-Type"] = "application/json"
        
        # Sign the request
        signed_headers = self._sign_request("POST", url, request_headers, body)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, content=body, headers=signed_headers)
            return response
    
    async def stream_post(self, endpoint: str, json_data: dict = None, headers: dict = None) -> AsyncIterator[bytes]:
        """Make a signed streaming POST request."""
        import json as json_lib
        
        url = f"{self.gateway_url}{endpoint}"
        body = json_lib.dumps(json_data).encode() if json_data else b""
        
        request_headers = headers or {}
        request_headers["Content-Type"] = "application/json"
        
        # Sign the request
        signed_headers = self._sign_request("POST", url, request_headers, body)
        
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, content=body, headers=signed_headers) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk


@asynccontextmanager
async def iam_signed_http_client(gateway_url: str, region: str = "us-east-1"):
    """Context manager for IAM-signed HTTP client."""
    client = IAMSignedHTTPClient(gateway_url, region)
    try:
        yield client
    finally:
        pass  # Cleanup if needed
