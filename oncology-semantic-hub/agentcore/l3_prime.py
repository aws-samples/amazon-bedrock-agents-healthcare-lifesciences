"""L3' — the L3 agent reconstructed purely from PORTABLE COMPONENTS (no bespoke tool code):

  • domain workflow skill  -> agent system prompt  (skills/oncology-semantic-hub-analysis/SKILL.md)
  • deployed MCP servers   -> agent tools          (oncology-hub-data + ontology-lookup-service, JWT)
  • process/eval skill     -> scores the answer    (skills/grounding-faithfulness-eval/scripts/score_provenance.py)

WHAT THIS PROVES: the deployed L3 agent (agentcore/semantic_hub_agent.py) answers using in-process
boto3 tools (kept in-process deliberately, for ablation control across L0-L3 — see ADR 0004 in
docs/adr/). This script builds a SEPARATE agent ("L3'", "L3 prime") that reaches the SAME data —
Neptune graph + Athena lake + OLS ontology — only through the portable, externally-consumable
components: the two remote MCP servers (mcp-servers/agentcore-runtime/) and the domain-workflow
skill, the same components a non-AWS-SDK client (Amazon Quick, Claude Code, Kiro) would use. A
run of this script against the EGFR-GBM demo question reproduced L3's results (144 MONDO-anchored
genes, 82 EGFR patients, provenance-faithfulness 1.0) — recorded in docs/backlog.md — confirming the
MCP-server architecture is a faithful, drift-free stand-in for the in-process agent.

WHY STANDALONE: this is a one-off architecture-validation tool, not part of the deployed demo or
the data pipeline. It has no deploy.py of its own; it runs ad hoc against already-deployed MCP
servers (deploy those first — see mcp-servers/agentcore-runtime/*/README.md) to let a developer
re-verify the "two consumers, one hub_core" claim after a change to the shared query core, the MCP
servers, or the skill. Nothing else in this repo imports or shells out to it.

Both skills/ this script reads are vendored under oncology_semantic_hub/skills/ (copied from the
monorepo's shared skills/ dir, since this hub subproject is also distributed/committed on its own).

Proves the L3 capability is reproducible via skills + MCP servers — the same components a Quick harness
uses. KB (`knowledge_search`) is a LOCAL MCP server in Quick; add it here with --kb-url if running one.

Usage:
  python l3_prime.py --question "..."               # graph/lake/ontology via the 2 remote MCP servers
  python l3_prime.py --question "..." --kb-url URL   # also connect a local/remote KB MCP
"""
import argparse
import importlib.util
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

import boto3
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

REGION = os.environ.get("SEMHUB_REGION", "us-west-2")
HUB = Path(__file__).resolve().parents[1]  # oncology_semantic_hub/


def _safe_urlopen(req_or_url, **kwargs):
    """urllib.request.urlopen, restricted to https:// (Bandit B310). URL comes from SSM (OLS Cognito
    token endpoint), never end-user input, but validating the scheme is the correct hardening."""
    url = req_or_url.full_url if isinstance(req_or_url, urllib.request.Request) else req_or_url
    scheme = urllib.parse.urlsplit(url).scheme
    if scheme != "https":
        raise ValueError(f"refusing to open non-https URL (scheme={scheme!r}): {url}")
    return urllib.request.urlopen(req_or_url, **kwargs)  # nosec B310 — scheme validated above


SKILLS = HUB / "skills"
OLS_PREFIX = "/app/ontology-lookup-service/agentcore"


def _load_score_provenance():
    """Import skills/grounding-faithfulness-eval/scripts/score_provenance.py's score_provenance()
    DIRECTLY (importlib, no subprocess) instead of shelling out to it as a script. Closes the
    semgrep dangerous-subprocess-use finding at the root — there is no subprocess call to flag —
    rather than suppressing it; the module is stdlib-only with no import-time side effects
    (its CLI body is behind `if __name__ == "__main__":`), so importing it is safe."""
    path = SKILLS / "grounding-faithfulness-eval" / "scripts" / "score_provenance.py"
    spec = importlib.util.spec_from_file_location("score_provenance", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.score_provenance


def _ssm(name):
    return boto3.client("ssm", region_name=REGION).get_parameter(Name=name)["Parameter"]["Value"]


def _token():
    """Mint a Cognito M2M token from the (reused) OLS Cognito — valid for BOTH remote MCP servers."""
    tok_url = _ssm(f"{OLS_PREFIX}/cognito_token_url")
    form = {"grant_type": "client_credentials", "client_id": _ssm(f"{OLS_PREFIX}/machine_client_id"),
            "client_secret": _ssm(f"{OLS_PREFIX}/cognito_secret"), "scope": _ssm(f"{OLS_PREFIX}/cognito_auth_scope")}
    req = urllib.request.Request(tok_url, data=urllib.parse.urlencode(form).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    return json.load(_safe_urlopen(req, timeout=25))["access_token"]


def _skill_body(name):
    txt = (SKILLS / name / "SKILL.md").read_text()
    m = re.match(r"^---\n.*?\n---\n(.*)$", txt, re.DOTALL)
    return m.group(1).strip() if m else txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    ap.add_argument("--inventory", default="quick", choices=["quick", "L0", "L0-web", "L1", "L2", "L3"],
                    help="provenance-tag inventory passed to the scorer (constrained to the scorer's "
                         "own known-good set)")
    ap.add_argument("--kb-url", default=os.environ.get("KB_MCP_URL", ""), help="optional KB MCP URL (JWT)")
    a = ap.parse_args()

    token = _token()
    headers = {"authorization": f"Bearer {token}", "Content-Type": "application/json"}
    clients = [
        MCPClient(lambda u=_ssm("/app/oncology-hub-data/agentcore/mcp_url"):
                  streamablehttp_client(u, headers, timeout=180, terminate_on_close=False)),
        MCPClient(lambda u=_ssm(f"{OLS_PREFIX}/mcp_url"):
                  streamablehttp_client(u, headers, timeout=180, terminate_on_close=False)),
    ]
    if a.kb_url:
        clients.append(MCPClient(lambda u=a.kb_url:
                       streamablehttp_client(u, headers, timeout=180, terminate_on_close=False)))

    system = _skill_body("oncology-semantic-hub-analysis")
    model = BedrockModel(model_id=os.environ.get("SEMHUB_SUBJECT_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
                         region_name=REGION, temperature=0.0)

    import contextlib
    with contextlib.ExitStack() as stack:
        for c in clients:
            stack.enter_context(c)
        tools = []
        for c in clients:
            tools += c.list_tools_sync()
        print("L3' composed tools:", [getattr(t, "tool_name", getattr(t, "name", "?")) for t in tools])
        agent = Agent(model=model, tools=tools, system_prompt=system)
        answer = str(agent(a.question))

    print("\n=== L3' ANSWER ===")
    print(answer[:1600])
    # Direct import, no subprocess — see _load_score_provenance() above.
    score_provenance = _load_score_provenance()
    result = score_provenance(answer, a.inventory)
    print("\n=== grounding-faithfulness-eval ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
