"""OLS ontology-resolution tool for L3, backed by the deployed OLS MCP server
(AgentCore Runtime, EBI Ontology Lookup Service).

Gives the semantic-hub agent authoritative cross-ontology resolution — the fix for
cross-system ontology misalignment (TCGA project codes / gene symbols -> MONDO / other
ontology ids). Credentials + endpoint are read from SSM (same params the deploy created);
the Cognito M2M token is fetched on first use and cached.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import urllib.parse
import urllib.request

import boto3
from strands import tool

from . import config as C

_SSM_PREFIX = "/app/ontology-lookup-service/agentcore"
_cfg: dict = {}


def _safe_urlopen(req_or_url, **kwargs):
    """urllib.request.urlopen, restricted to https:// (Bandit B310). URL comes from SSM (OLS Cognito
    token endpoint), never end-user input, but validating the scheme is the correct hardening."""
    url = req_or_url.full_url if isinstance(req_or_url, urllib.request.Request) else req_or_url
    scheme = urllib.parse.urlsplit(url).scheme
    if scheme != "https":
        raise ValueError(f"refusing to open non-https URL (scheme={scheme!r}): {url}")
    return urllib.request.urlopen(req_or_url, **kwargs)  # nosec B310 — scheme validated above


def _config() -> dict:
    if _cfg:
        return _cfg
    ssm = boto3.client("ssm", region_name=C.REGION)
    names = ["mcp_url", "cognito_token_url", "machine_client_id",
             "cognito_secret", "cognito_auth_scope"]
    p = {n: ssm.get_parameter(Name=f"{_SSM_PREFIX}/{n}", WithDecryption=True)["Parameter"]["Value"]
         for n in names}
    form = {"grant_type": "client_credentials",
            "client_id": p["machine_client_id"],
            "client_secret": p["cognito_secret"]}
    if p.get("cognito_auth_scope"):
        form["scope"] = p["cognito_auth_scope"]
    req = urllib.request.Request(
        p["cognito_token_url"], data=urllib.parse.urlencode(form).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    token = json.load(_safe_urlopen(req, timeout=25))["access_token"]
    _cfg.update(url=p["mcp_url"], token=token)
    return _cfg


async def _mcp_call(tool_name: str, args: dict) -> str:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    c = _config()
    async with streamablehttp_client(url=c["url"],
                                     headers={"Authorization": f"Bearer {c['token']}"}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(tool_name, args)
            return res.content[0].text if res.content else ""


def _call_sync(tool_name: str, args: dict) -> str:
    """Run the async MCP call in an isolated event loop (safe inside a sync tool)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(lambda: asyncio.run(_mcp_call(tool_name, args))).result(timeout=90)


def _iri_to_curie(iri: str) -> str:
    seg = iri.rstrip("/").split("/")[-1]
    return seg.replace("_", ":", 1) if "_" in seg else seg


@tool
def ontology_lookup(query: str, ontology: str = "mondo") -> str:
    """Resolve a biomedical term (disease, gene, phenotype) to its authoritative ontology
    identifier via the EBI Ontology Lookup Service (OLS). Use this for ontology-id questions
    (e.g. the MONDO id for a disease) and to reconcile cross-system identifier mismatches
    between TCGA/GDC and the knowledge graph. `ontology` restricts the search (e.g. 'mondo',
    'hp', 'go'); pass None to search all. Returns top matching terms as JSON: id (CURIE), label."""
    try:
        raw = _call_sync("search_terms", {"query": query, "ontology": ontology})
    except Exception as e:
        return f"OLS lookup failed: {e}"
    try:
        items = json.loads(raw).get("items", [])[:5]
        return json.dumps([{"id": _iri_to_curie(it.get("iri", "")), "label": it.get("label")}
                           for it in items])
    except (json.JSONDecodeError, TypeError):
        return raw[:800]
