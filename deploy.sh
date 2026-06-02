#!/usr/bin/env bash
# deploy.sh — Deploy a single agent to Amazon Bedrock AgentCore
#
# Usage:
#   ./deploy.sh <agent-name>          # Deploy an agent
#   ./deploy.sh <agent-name> --dry-run  # Preview without deploying
#   ./deploy.sh --list                # List available agents
#
# Prerequisites:
#   - AWS CLI configured with valid credentials
#   - Node.js >= 18 and npm
#   - @aws/agentcore CLI: npm install -g @aws/agentcore
#   - Docker running (for container builds)
#
# The script will run 'agentcore init' if no .bedrock_agentcore.yaml exists,
# then deploy using the agentcore CLI.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="${REPO_ROOT}/agents_catalog"

# --- Helpers ---

die() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "==> $*"; }

list_agents() {
    echo "Available agents with AgentCore support:"
    echo ""
    for dir in "${AGENTS_DIR}"/*/agentcore/; do
        [ -d "$dir" ] || continue
        agent_name="$(basename "$(dirname "$dir")")"
        echo "  ${agent_name}"
    done
    echo ""
    echo "Usage: ./deploy.sh <agent-name>"
}

check_prerequisites() {
    local missing=0

    if ! command -v aws &>/dev/null; then
        echo "  ✗ AWS CLI not found (https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)"
        missing=1
    else
        echo "  ✓ AWS CLI"
    fi

    if ! aws sts get-caller-identity &>/dev/null; then
        echo "  ✗ AWS credentials not configured or expired"
        missing=1
    else
        echo "  ✓ AWS credentials valid"
    fi

    if ! command -v node &>/dev/null; then
        echo "  ✗ Node.js not found (https://nodejs.org/)"
        missing=1
    else
        echo "  ✓ Node.js $(node --version)"
    fi

    if ! command -v npx &>/dev/null && ! command -v agentcore &>/dev/null; then
        echo "  ✗ agentcore CLI not found — install with: npm install -g @aws/agentcore"
        missing=1
    else
        echo "  ✓ agentcore CLI"
    fi

    if ! docker info &>/dev/null 2>&1; then
        echo "  ✗ Docker not running (required for container builds)"
        missing=1
    else
        echo "  ✓ Docker"
    fi

    if [ "$missing" -ne 0 ]; then
        echo ""
        die "Missing prerequisites. Install the above and retry."
    fi
}

resolve_agentcore_cli() {
    if command -v agentcore &>/dev/null; then
        echo "agentcore"
    else
        echo "npx @aws/agentcore"
    fi
}

# --- Main ---

if [ $# -lt 1 ]; then
    list_agents
    exit 0
fi

if [ "$1" = "--list" ] || [ "$1" = "-l" ]; then
    list_agents
    exit 0
fi

AGENT_NAME="$1"
DRY_RUN=""
if [ "${2:-}" = "--dry-run" ]; then
    DRY_RUN="--dry-run"
fi

AGENT_DIR="${AGENTS_DIR}/${AGENT_NAME}/agentcore"

if [ ! -d "$AGENT_DIR" ]; then
    die "Agent '${AGENT_NAME}' not found or has no agentcore/ directory.
Run './deploy.sh --list' to see available agents."
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "  Deploying: ${AGENT_NAME}"
echo "╚══════════════════════════════════════════════════╝"
echo ""

info "Checking prerequisites..."
check_prerequisites
echo ""

CLI="$(resolve_agentcore_cli)"

cd "$AGENT_DIR"

# Initialize if no config exists
if [ ! -f ".bedrock_agentcore.yaml" ]; then
    info "No .bedrock_agentcore.yaml found — running 'agentcore init'..."
    $CLI init
    echo ""
fi

# Deploy
if [ -n "$DRY_RUN" ]; then
    info "Dry run — previewing deployment..."
    $CLI deploy --dry-run
else
    info "Deploying agent..."
    $CLI deploy -y
    echo ""
    info "Checking status..."
    $CLI status
    echo ""
    echo "✅ ${AGENT_NAME} deployed successfully!"
fi
