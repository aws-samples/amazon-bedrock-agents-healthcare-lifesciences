"""Tool: Retrieve patient insights from AgentCore Memory long-term storage."""

import os
import boto3
from strands import tool
from .phi_access import check_phi_access, phi_access_denied_response

MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

try:
    agentcore_client = boto3.client("bedrock-agentcore", region_name=REGION)
except Exception:
    agentcore_client = None


@tool
def recall_patient_memory(patient_id: str, query: str) -> dict:
    """Search AgentCore Memory for relevant long-term memories about a patient.

    Uses semantic search to find the most relevant clinical observations, medication
    responses, and care notes stored in AgentCore Memory's long-term storage.

    Args:
        patient_id: The patient identifier (e.g., P-10001)
        query: What you want to know about the patient (e.g., "medication response to Furosemide", "fall risk factors", "discharge readiness")

    Returns:
        Relevant memory records from AgentCore Memory with relevance scores.
    """
    if not check_phi_access(patient_id):
        return phi_access_denied_response(patient_id)

    if not MEMORY_ID or not agentcore_client:
        return {
            "patient_id": patient_id,
            "source": "agentcore_memory",
            "available": False,
            "records": [],
            "message": "AgentCore Memory not configured. Use get_patient_timeline for DynamoDB-based timeline.",
        }

    try:
        namespace = f"/patient-{patient_id}/"
        response = agentcore_client.retrieve_memory_records(
            memoryId=MEMORY_ID,
            namespace=namespace,
            searchCriteria={
                "searchQuery": query,
                "topK": 10,
            },
        )

        records = []
        for record in response.get("memoryRecordSummaries", []):
            records.append({
                "content": record.get("content", ""),
                "relevance_score": float(record.get("score", 0)),
                "created_at": str(record.get("createdAt", "")),
                "namespace": record.get("namespace", ""),
            })

        return {
            "patient_id": patient_id,
            "query": query,
            "source": "agentcore_memory",
            "available": True,
            "total_records": len(records),
            "records": records,
            "message": f"Retrieved {len(records)} memory records from AgentCore Memory for {patient_id}.",
        }

    except Exception as e:
        # Fall back gracefully — AgentCore Memory might not have records yet
        error_msg = str(e)
        if "ResourceNotFoundException" in error_msg or "no records" in error_msg.lower():
            return {
                "patient_id": patient_id,
                "source": "agentcore_memory",
                "available": True,
                "total_records": 0,
                "records": [],
                "message": f"No long-term memory records found for {patient_id}. Records may still be processing.",
            }
        return {
            "patient_id": patient_id,
            "source": "agentcore_memory",
            "available": False,
            "records": [],
            "error": error_msg,
            "message": f"AgentCore Memory retrieval failed: {error_msg}",
        }
