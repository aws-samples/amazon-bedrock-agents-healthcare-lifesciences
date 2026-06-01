"""
FDA eCFR MCP Server — Lambda Handler

Wraps the public eCFR REST API to retrieve FDA regulations (Title 21 CFR).
No authentication required. All data is US Government public domain.

eCFR API docs: https://www.ecfr.gov/developers
Base URL: https://www.ecfr.gov/api/versioner/v1/
"""

import json
import urllib.request
import urllib.parse


ECFR_BASE = "https://www.ecfr.gov/api/versioner/v1"


def handler(event, context):
    """Lambda entry point for AgentCore Gateway invocation."""
    action = event.get("action_name", "")

    if action == "get_cfr_section":
        return _get_cfr_section(event)
    elif action == "search_cfr":
        return _search_cfr(event)
    elif action == "get_cfr_part_structure":
        return _get_cfr_part_structure(event)

    return {"error": f"Unknown action: {action}"}


def _get_cfr_section(event):
    """
    Retrieve the full text of a specific CFR section.
    Example: title=21, part=312, section=23 returns 21 CFR 312.23
    """
    title = event.get("title", "21")
    part = event.get("part", "312")
    section = event.get("section", "")

    path = f"/full/current/title-{title}"
    if section:
        url = f"{ECFR_BASE}{path}?part={part}&section={part}.{section}"
    else:
        url = f"{ECFR_BASE}{path}?part={part}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return {
            "title": f"21 CFR Part {part}" + (f".{section}" if section else ""),
            "content": _extract_text(data),
            "source_url": (
                f"https://www.ecfr.gov/current/title-{title}/part-{part}"
                + (f"/section-{part}.{section}" if section else "")
            ),
        }
    except Exception as e:
        return {"error": str(e), "url_attempted": url}


def _search_cfr(event):
    """
    Search across CFR text for a query term within a specific title/part.
    Uses the eCFR search endpoint.
    """
    query = event.get("query", "")
    title = event.get("title", "21")
    part = event.get("part", "")

    params = {"query": query, "per_page": "5"}
    if title:
        params["title"] = title
    if part:
        params["hierarchy__part"] = part

    url = f"{ECFR_BASE}/search?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        results = []
        for hit in data.get("results", [])[:5]:
            results.append({
                "title": hit.get("hierarchy_title", ""),
                "snippet": hit.get("full_text_excerpt", "")[:500],
                "section": hit.get("section_number", ""),
                "url": hit.get("url", ""),
            })
        return {"results": results, "total": data.get("count", 0)}
    except Exception as e:
        return {"error": str(e), "url_attempted": url}


def _get_cfr_part_structure(event):
    """
    Get the table of contents / structure of a CFR part.
    Useful for understanding what sections exist within a part.
    """
    title = event.get("title", "21")
    part = event.get("part", "312")

    url = f"{ECFR_BASE}/structure/current/title-{title}?part={part}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return {"structure": data}
    except Exception as e:
        return {"error": str(e), "url_attempted": url}


def _extract_text(data):
    """Extract readable text from eCFR JSON response."""
    if isinstance(data, str):
        return data[:5000]
    if isinstance(data, dict):
        text_parts = []
        for key in ["text", "content", "body"]:
            if key in data:
                text_parts.append(str(data[key])[:5000])
        if not text_parts:
            return json.dumps(data, indent=2)[:5000]
        return "\n".join(text_parts)
    return str(data)[:5000]
