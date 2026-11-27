#!/usr/bin/env python3
"""
Patch OLS MCP server source for Amazon Bedrock AgentCore Runtime compatibility.

AgentCore Runtime requires:
- host="0.0.0.0" and stateless_http=True for FastMCP initialization
- transport="streamable-http" for mcp.run() calls

Usage:
    python patch_ols.py <path-to-ols-server-dir>

Example:
    python patch_ols.py ./ols_mcp_deployment/ols
"""

import sys
from pathlib import Path


def patch_ols_for_agentcore(ols_root: Path) -> bool:
    """
    Patch OLS MCP server code for AgentCore Runtime compatibility.

    Args:
        ols_root: Root directory of the cloned ols-mcp-server repository.

    Returns:
        True if patches were applied successfully, False otherwise.
    """
    server_file = ols_root / "src" / "ols_mcp_server" / "server.py"

    if not server_file.exists():
        print(f"ERROR: server.py not found at {server_file}")
        return False

    with open(server_file, "r", encoding="utf-8") as f:
        content = f.read()

    patches_applied = 0

    # Patch 1: Update FastMCP initialization to use stateless HTTP
    original_init = 'mcp = FastMCP("OLS MCP Server")'
    patched_init = 'mcp = FastMCP(host="0.0.0.0", stateless_http=True)  # AgentCore Runtime'

    if original_init in content:
        content = content.replace(original_init, patched_init)
        print("  [OK] Patched FastMCP initialization for stateless HTTP")
        patches_applied += 1
    else:
        print("  [WARN] FastMCP initialization pattern not found — may already be patched")

    # Patch 2: Update all mcp.run() calls to use streamable-http transport
    original_run = "    mcp.run()"
    patched_run = '    mcp.run(transport="streamable-http")  # AgentCore Runtime'

    if original_run in content:
        content = content.replace(original_run, patched_run)
        print("  [OK] Patched mcp.run() for streamable-http transport")
        patches_applied += 1
    else:
        print("  [WARN] mcp.run() pattern not found — may already be patched")

    with open(server_file, "w", encoding="utf-8") as f:
        f.write(content)

    if patches_applied > 0:
        print(f"  Applied {patches_applied} patch(es) to {server_file}")
    else:
        print("  No patches needed (already compatible)")

    return True


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path-to-ols-server-dir>")
        print("")
        print("Example:")
        print(f"  {sys.argv[0]} ./ols_mcp_deployment/ols")
        sys.exit(1)

    ols_root = Path(sys.argv[1])

    if not ols_root.exists():
        print(f"ERROR: Directory not found: {ols_root}")
        sys.exit(1)

    print(f"Patching OLS MCP server at: {ols_root}")
    success = patch_ols_for_agentcore(ols_root)

    if not success:
        sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()
