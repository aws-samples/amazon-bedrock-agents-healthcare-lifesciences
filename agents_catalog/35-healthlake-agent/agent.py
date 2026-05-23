"""
HealthLake Agent - Combined implementation with direct AWS SDK access.

This module creates a Strands Agent with:
- Direct AWS SDK calls (no MCP dependency)
- Comprehensive FHIR and S3 tools
- Proper authentication and error handling
- Session context and authorization
"""

import os
import json
import base64
from typing import Optional, Dict, Any
from urllib.parse import quote
from strands import Agent, tool
from strands.models import BedrockModel
import boto3
from botocore.exceptions import ClientError
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests
import logging

from config import CONFIG
from models.session import SessionContext
from utils.auth_helpers import validate_patient_scope
from utils.retry_handler import execute_with_retry, DEFAULT_RETRY_CONFIG
from utils.fhir_code_translator import translate_fhir_codes
from prompts.healthcare_assistant_prompt import HEALTHCARE_ASSISTANT_PROMPT

logger = logging.getLogger(__name__)

# Configuration
HEALTHLAKE_DATASTORE_ID = CONFIG['healthlake'].datastore_id
AWS_REGION = CONFIG['aws_region']


def get_s3_client():
    """Get S3 client (lazy initialization)"""
    profile_name = os.environ.get('AWS_PROFILE')
    if profile_name:
        session = boto3.Session(profile_name=profile_name, region_name=AWS_REGION)
        return session.client('s3')
    return boto3.client('s3', region_name=AWS_REGION)


def get_healthlake_client():
    """Get HealthLake client (lazy initialization)"""
    profile_name = os.environ.get('AWS_PROFILE')
    if profile_name:
        session = boto3.Session(profile_name=profile_name, region_name=AWS_REGION)
        return session.client('healthlake')
    return boto3.client('healthlake', region_name=AWS_REGION)


def make_signed_request(url: str, method: str = "GET") -> requests.Response:
    """
    Make a signed AWS request to HealthLake FHIR endpoint.
    
    Args:
        url: The full URL to request
        method: HTTP method (GET, POST, etc.)
    
    Returns:
        Response object
    """
    # Get AWS session with profile if specified
    profile_name = os.environ.get('AWS_PROFILE')
    if profile_name:
        session = boto3.Session(profile_name=profile_name, region_name=AWS_REGION)
    else:
        session = boto3.Session(region_name=AWS_REGION)
    
    credentials = session.get_credentials()
    
    request = AWSRequest(method=method, url=url, headers={"Accept": "application/fhir+json"})
    SigV4Auth(credentials, "healthlake", session.region_name).add_auth(request)
    
    return requests.request(
        method=request.method,
        url=request.url,
        headers=dict(request.headers)
    )


# ============================================================================
# FHIR Tools
# ============================================================================

@tool
def search_fhir_resources(
    resource_type: str,
    search_params: Optional[Dict[str, Any]] = None,
    count: int = 100
) -> str:
    """
    Search for FHIR resources in HealthLake.
    
    Args:
        resource_type: FHIR resource type (e.g., Patient, Observation, Condition, 
                      Coverage, Claim, Procedure, MedicationRequest, AllergyIntolerance)
        search_params: Search parameters (e.g., {"patient": "123", "code": "diabetes"})
        count: Maximum number of results (default: 100)
    
    Returns:
        JSON string with search results summary
    """
    try:
        def _search():
            client = get_healthlake_client()
            
            # Get datastore endpoint
            datastore_info = client.describe_fhir_datastore(DatastoreId=HEALTHLAKE_DATASTORE_ID)
            endpoint = datastore_info["DatastoreProperties"]["DatastoreEndpoint"]
            
            # Build search URL
            search_url = f"{endpoint}/{resource_type}?_count={count}"
            if search_params:
                for key, value in search_params.items():
                    # URL encode both key and value to handle special characters and modifiers
                    encoded_key = quote(str(key), safe='')
                    encoded_value = quote(str(value), safe='')
                    search_url += f"&{encoded_key}={encoded_value}"
            
            # Make signed request
            response = make_signed_request(search_url)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract summary
            result = {
                "resourceType": data.get("resourceType"),
                "total": data.get("total", 0),
                "count": len(data.get("entry", [])),
                "resources": []
            }
            
            # Extract key fields for each resource
            for entry in data.get("entry", []):
                resource = entry.get("resource", {})
                resource_summary = {
                    "id": resource.get("id"),
                    "resourceType": resource.get("resourceType")
                }
                
                # Add resource-specific fields
                if resource_type == "Patient":
                    name = resource.get("name", [{}])[0]
                    resource_summary.update({
                        "name": f"{name.get('given', [''])[0]} {name.get('family', '')}",
                        "gender": resource.get("gender"),
                        "birthDate": resource.get("birthDate")
                    })
                elif resource_type == "Observation":
                    resource_summary.update({
                        "code": resource.get("code", {}).get("text"),
                        "value": resource.get("valueQuantity", {}).get("value"),
                        "unit": resource.get("valueQuantity", {}).get("unit"),
                        "effectiveDateTime": resource.get("effectiveDateTime")
                    })
                elif resource_type == "Condition":
                    resource_summary.update({
                        "code": resource.get("code", {}).get("text"),
                        "clinicalStatus": resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code"),
                        "onsetDateTime": resource.get("onsetDateTime")
                    })
                elif resource_type in ["Medication", "MedicationRequest"]:
                    resource_summary.update({
                        "medication": resource.get("medicationCodeableConcept", {}).get("text"),
                        "status": resource.get("status")
                    })
                
                result["resources"].append(resource_summary)
            
            result["note"] = f"Showing summary of {len(result['resources'])} resources. Use read_fhir_resource(resource_type, resource_id) for full details."
            
            return result
        
        result = execute_with_retry(_search, retry_config=DEFAULT_RETRY_CONFIG)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error searching FHIR resources: {str(e)}", exc_info=True)
        return json.dumps({
            "error": f"Error searching resources: {str(e)}",
            "resource_type": resource_type
        })


@tool
def read_fhir_resource(resource_type: str, resource_id: str) -> str:
    """
    Read a specific FHIR resource by ID.
    
    Args:
        resource_type: FHIR resource type (e.g., Patient, Condition, Observation)
        resource_id: Resource identifier
    
    Returns:
        JSON string with the FHIR resource
    """
    try:
        def _read():
            client = get_healthlake_client()
            
            # Get datastore endpoint
            datastore_info = client.describe_fhir_datastore(DatastoreId=HEALTHLAKE_DATASTORE_ID)
            endpoint = datastore_info["DatastoreProperties"]["DatastoreEndpoint"]
            
            # Build read URL
            url = f"{endpoint}/{resource_type}/{resource_id}"
            
            # Make signed request
            response = make_signed_request(url)
            response.raise_for_status()
            
            return response.json()
        
        result = execute_with_retry(_read, retry_config=DEFAULT_RETRY_CONFIG)
        
        # Translate codes to human-readable text
        result = translate_fhir_codes(result)
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error reading FHIR resource: {str(e)}", exc_info=True)
        return json.dumps({
            "error": f"Error reading resource: {str(e)}",
            "resource_type": resource_type,
            "resource_id": resource_id
        })


@tool
def patient_everything(
    patient_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Retrieve all resources related to a patient using $patient-everything operation.
    
    Args:
        patient_id: Patient resource ID
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    
    Returns:
        JSON string with all patient-related resources
    """
    try:
        def _get_everything():
            client = get_healthlake_client()
            
            # Get datastore endpoint
            datastore_info = client.describe_fhir_datastore(DatastoreId=HEALTHLAKE_DATASTORE_ID)
            endpoint = datastore_info["DatastoreProperties"]["DatastoreEndpoint"]
            
            # Build $everything URL
            url = f"{endpoint}/Patient/{patient_id}/$everything"
            params = []
            if start_date:
                params.append(f"start={start_date}")
            if end_date:
                params.append(f"end={end_date}")
            if params:
                url += "?" + "&".join(params)
            
            # Make signed request
            response = make_signed_request(url)
            response.raise_for_status()
            
            return response.json()
        
        result = execute_with_retry(_get_everything, retry_config=DEFAULT_RETRY_CONFIG)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting patient everything: {str(e)}", exc_info=True)
        return json.dumps({
            "error": f"Error getting patient data: {str(e)}",
            "patient_id": patient_id
        })


@tool
def get_datastore_info() -> str:
    """
    Get information about the current HealthLake datastore.
    
    Returns:
        JSON string with datastore information
    """
    try:
        client = get_healthlake_client()
        response = client.describe_fhir_datastore(DatastoreId=HEALTHLAKE_DATASTORE_ID)
        datastore = response.get("DatastoreProperties", {})
        
        result = {
            "datastore_id": HEALTHLAKE_DATASTORE_ID,
            "status": datastore.get("DatastoreStatus"),
            "fhir_version": datastore.get("DatastoreTypeVersion"),
            "created": str(datastore.get("CreatedAt", "")),
            "endpoint": datastore.get("DatastoreEndpoint"),
            "preloaded_data": datastore.get("PreloadDataConfig", {}).get("PreloadDataType")
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Error getting datastore info: {str(e)}"})


# ============================================================================
# S3 Tools
# ============================================================================

@tool
def list_s3_documents(bucket_name: str, prefix: str = "") -> str:
    """
    List documents in an S3 bucket.
    
    Args:
        bucket_name: S3 bucket name
        prefix: Optional prefix/folder path
    
    Returns:
        JSON string with list of documents
    """
    try:
        s3_client = get_s3_client()
        
        params = {"Bucket": bucket_name}
        if prefix:
            params["Prefix"] = prefix
        
        response = s3_client.list_objects_v2(**params)
        
        if "Contents" not in response:
            return json.dumps({
                "bucket": bucket_name,
                "prefix": prefix,
                "count": 0,
                "documents": [],
                "message": "No documents found"
            })
        
        documents = [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "size_mb": round(obj["Size"] / (1024 * 1024), 2),
                "last_modified": obj["LastModified"].isoformat()
            }
            for obj in response["Contents"]
        ]
        
        return json.dumps({
            "bucket": bucket_name,
            "prefix": prefix,
            "count": len(documents),
            "documents": documents
        }, indent=2)
    
    except ClientError as e:
        return json.dumps({
            "error": f"S3 Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        })


@tool
def read_s3_document(bucket_name: str, document_key: str, max_size_mb: int = 10) -> str:
    """
    Read and return the content of an S3 document.
    
    Args:
        bucket_name: S3 bucket name
        document_key: S3 object key
        max_size_mb: Maximum file size in MB (default: 10MB, max: 50MB)
    
    Returns:
        JSON string with document content
    """
    try:
        s3_client = get_s3_client()
        
        # Validate max size
        if max_size_mb > 50:
            max_size_mb = 50
        
        # Get object metadata
        head_response = s3_client.head_object(Bucket=bucket_name, Key=document_key)
        file_size = head_response["ContentLength"]
        content_type = head_response.get("ContentType", "application/octet-stream")
        
        # Check size limit
        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return json.dumps({
                "error": f"Document too large: {round(file_size / (1024 * 1024), 2)}MB (max: {max_size_mb}MB)",
                "bucket": bucket_name,
                "key": document_key
            })
        
        # Get object content
        response = s3_client.get_object(Bucket=bucket_name, Key=document_key)
        content_bytes = response["Body"].read()
        
        # Determine if text or binary
        text_types = ["text/", "application/json", "application/xml", "application/fhir+json"]
        is_text = any(content_type.startswith(t) for t in text_types)
        
        result = {
            "bucket": bucket_name,
            "key": document_key,
            "content_type": content_type,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "is_text": is_text
        }
        
        if is_text:
            try:
                result["content"] = content_bytes.decode("utf-8")
                result["encoding"] = "utf-8"
            except UnicodeDecodeError:
                result["content"] = base64.b64encode(content_bytes).decode("ascii")
                result["encoding"] = "base64"
        else:
            result["content"] = base64.b64encode(content_bytes).decode("ascii")
            result["encoding"] = "base64"
        
        return json.dumps(result, indent=2)
    
    except ClientError as e:
        return json.dumps({
            "error": f"S3 Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        })


@tool
def generate_s3_presigned_url(bucket_name: str, document_key: str, expiration: int = 3600) -> str:
    """
    Generate a presigned URL for temporary access to an S3 document.
    
    Args:
        bucket_name: S3 bucket name
        document_key: S3 object key
        expiration: URL expiration in seconds (default: 3600 = 1 hour)
    
    Returns:
        JSON string with presigned URL
    """
    try:
        s3_client = get_s3_client()
        
        # Validate expiration
        if expiration > 604800:  # 7 days max
            expiration = 604800
        
        # Generate presigned URL
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': document_key},
            ExpiresIn=expiration
        )
        
        # Get metadata
        head_response = s3_client.head_object(Bucket=bucket_name, Key=document_key)
        
        result = {
            "bucket": bucket_name,
            "key": document_key,
            "presigned_url": url,
            "expires_in_seconds": expiration,
            "expires_in_hours": round(expiration / 3600, 2),
            "content_type": head_response.get("ContentType", "unknown"),
            "size_mb": round(head_response["ContentLength"] / (1024 * 1024), 2)
        }
        
        return json.dumps(result, indent=2)
    
    except ClientError as e:
        return json.dumps({
            "error": f"S3 Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}"
        })


# ============================================================================
# Agent Creation
# ============================================================================

def create_healthlake_agent() -> Agent:
    """Create and configure the HealthLake agent"""
    
    bedrock_config = CONFIG['bedrock']
    
    model = BedrockModel(
        model_id=bedrock_config.model_id,
        region_name=AWS_REGION,
        temperature=bedrock_config.temperature,
        max_tokens=bedrock_config.max_tokens,
    )
    
    agent = Agent(
        model=model,
        tools=[
            # FHIR tools
            get_datastore_info,
            search_fhir_resources,
            read_fhir_resource,
            patient_everything,
            # S3 tools
            list_s3_documents,
            read_s3_document,
            generate_s3_presigned_url,
        ],
        system_prompt=HEALTHCARE_ASSISTANT_PROMPT
    )
    
    return agent


# Global agent instance
_agent_instance: Optional[Agent] = None


def get_agent_instance() -> Agent:
    """Get the singleton agent instance"""
    global _agent_instance
    
    if _agent_instance is None:
        _agent_instance = create_healthlake_agent()
    
    return _agent_instance


def process_query(query: str, session_id: str, context: dict) -> dict:
    """
    Process a natural language query using the agent.
    
    Args:
        query: Natural language query text
        session_id: Unique session identifier
        context: User context dictionary with user_id, user_role, active_member_id
    
    Returns:
        Agent response dictionary
    """
    from models.session import SessionContext
    
    # Convert dict to SessionContext
    if isinstance(context, dict):
        session_context = SessionContext.from_dict(context)
    else:
        session_context = context
    
    # Validate patient scope
    validate_patient_scope(
        user_role=session_context.user_role.value,
        user_id=session_context.user_id,
        active_member_id=session_context.active_member_id
    )
    
    # Get agent
    agent = get_agent_instance()
    
    # Process query
    agent_result = agent(
        query,
        invocation_state={
            "session_id": session_id,
            **session_context.to_dict()
        }
    )
    
    # Convert to dict
    result_dict = agent_result.to_dict()
    
    return {
        'text': str(agent_result),
        'session_id': session_id,
        'metadata': {
            'type': result_dict.get('type'),
            'stop_reason': result_dict.get('stop_reason'),
        }
    }


async def stream_query(query: str, session_id: str, context: dict):
    """
    Stream a natural language query using the agent with thinking process.
    
    Uses Strands' native stream_async for real-time events.
    
    Args:
        query: Natural language query text
        session_id: Unique session identifier
        context: User context dictionary with user_id, user_role, active_member_id
    
    Yields:
        Event dictionaries with type and content
    """
    from models.session import SessionContext
    import asyncio
    import time
    
    # Convert dict to SessionContext
    if isinstance(context, dict):
        session_context = SessionContext.from_dict(context)
    else:
        session_context = context
    
    try:
        # Validate patient scope
        validate_patient_scope(
            user_role=session_context.user_role.value,
            user_id=session_context.user_id,
            active_member_id=session_context.active_member_id
        )
        
        # Get agent
        agent = get_agent_instance()
        
        # Track execution
        start_time = time.time()
        full_response = ""
        has_started = False
        
        # Stream using Strands' native streaming
        agent_stream = agent.stream_async(
            query,
            invocation_state={
                "session_id": session_id,
                **session_context.to_dict()
            }
        )
        
        async for event in agent_stream:
            # Event loop initialization - only show once
            if event.get('init_event_loop', False) and not has_started:
                has_started = True
                yield {
                    'type': 'thinking',
                    'content': '🤔 Analyzing your question...'
                }
                await asyncio.sleep(0.1)
            
            # Tool usage events - show actual tool calls
            if 'current_tool_use' in event and event['current_tool_use'].get('name'):
                tool_name = event['current_tool_use']['name']
                
                # Map tool names to friendly descriptions
                tool_descriptions = {
                    'get_datastore_info': 'Getting HealthLake datastore information',
                    'search_fhir_resources': 'Searching FHIR resources',
                    'read_fhir_resource': 'Reading detailed FHIR resource',
                    'patient_everything': 'Retrieving complete patient record',
                    'list_s3_documents': 'Listing S3 documents',
                    'read_s3_document': 'Reading S3 document content',
                    'generate_s3_presigned_url': 'Generating S3 presigned URL'
                }
                
                description = tool_descriptions.get(tool_name, tool_name)
                
                yield {
                    'type': 'tool_use',
                    'tool': tool_name,
                    'input': {'description': description}
                }
                await asyncio.sleep(0.1)
            
            # Text generation events - stream character by character
            if 'data' in event:
                text_chunk = event['data']
                
                # Filter out tool usage lines that Strands prints to stdout
                # These lines look like "Tool #1: tool_name"
                if text_chunk.strip().startswith('Tool #') and ':' in text_chunk:
                    # Skip this chunk - it's a tool usage print statement
                    continue
                
                full_response += text_chunk
                
                yield {
                    'type': 'content',
                    'content': text_chunk
                }
                await asyncio.sleep(0.02)
            
            # Result event - show completion
            if 'result' in event:
                elapsed_time = time.time() - start_time
                yield {
                    'type': 'thinking',
                    'content': f'✅ Completed in {elapsed_time:.1f}s'
                }
                await asyncio.sleep(0.1)
    
    except Exception as e:
        logger.error(f"Error in stream_query: {str(e)}", exc_info=True)
        yield {
            'type': 'error',
            'error': str(e)
        }
