"""Tool: Search clinical practice guidelines knowledge base.

Queries the Bedrock Knowledge Base containing 37K clinical guidelines
from WHO, CDC, NICE, PubMed, and other medical sources.
Used for procedure setup, troubleshooting, and treatment protocols.
"""

import os
import boto3
from strands import tool

KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

if KNOWLEDGE_BASE_ID:
    bedrock_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)


@tool
def search_clinical_guidelines(query: str) -> dict:
    """Search clinical practice guidelines for procedures, protocols, and treatment guidance.

    Searches a knowledge base of 37,000+ clinical guidelines from WHO, CDC, NICE,
    PubMed, and other authoritative medical sources. Use this for:
    - Device setup procedures (ventilators, infusion pumps, monitors)
    - Clinical treatment protocols
    - Troubleshooting guidance
    - Best practices for specific conditions or procedures

    Args:
        query: Natural language search query describing what you need

    Returns:
        Relevant clinical guideline excerpts with source attribution.
    """
    if not KNOWLEDGE_BASE_ID:
        return {"error": "Knowledge base not configured. Set KNOWLEDGE_BASE_ID environment variable."}

    try:
        response = bedrock_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 5,
                }
            },
        )

        results = []
        for r in response.get("retrievalResults", []):
            content = r.get("content", {}).get("text", "")
            score = r.get("score", 0)
            location = r.get("location", {})
            s3_uri = location.get("s3Location", {}).get("uri", "")

            results.append({
                "text": content[:1000],
                "relevance_score": round(score, 3),
                "source": s3_uri.split("/")[-1] if s3_uri else "unknown",
            })

        return {
            "query": query,
            "results_count": len(results),
            "results": results,
        }

    except Exception as e:
        return {"error": f"Knowledge base search failed: {str(e)}"}
