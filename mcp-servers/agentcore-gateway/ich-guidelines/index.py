"""
ICH Guidelines MCP Server — Lambda Handler

Semantic search over ICH guideline documents using Bedrock Knowledge Base.
Requires deployment of the associated CloudFormation stacks to create the KB.

Data source: ICH E6(R2), E8(R1), E9 PDFs from FDA.gov (public domain).
"""

import json
import os

import boto3


bedrock = boto3.client("bedrock-agent-runtime")

# Set via environment variable during deployment, or override for local testing
KB_ID = os.environ.get("ICH_KB_ID", "REPLACE_WITH_KB_ID")


def handler(event, context):
    """Lambda entry point for AgentCore Gateway invocation."""
    action = event.get("action_name", "")

    if action == "search_ich_guidance":
        return _search_ich(event)

    return {"error": f"Unknown action: {action}"}


def _search_ich(event):
    """
    Search ICH guidelines for relevant sections.
    Returns passages from E6(R2), E8(R1), or E9 matching the query.
    """
    query = event.get("query", "")
    guideline = event.get("guideline", "")  # Optional: filter to specific guideline

    if not query:
        return {"error": "No query provided"}

    # If a specific guideline is requested, prepend it to improve retrieval
    search_query = query
    if guideline:
        search_query = f"ICH {guideline}: {query}"

    try:
        resp = bedrock.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={"text": search_query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": 5}
            },
        )

        results = []
        for r in resp.get("retrievalResults", []):
            results.append(
                {
                    "text": r["content"]["text"],
                    "score": r.get("score", 0),
                    "source": r.get("location", {})
                    .get("s3Location", {})
                    .get("uri", ""),
                }
            )

        return {
            "results": results,
            "query": search_query,
            "guideline_filter": guideline or "all",
        }
    except Exception as e:
        return {"error": str(e), "kb_id": KB_ID}
