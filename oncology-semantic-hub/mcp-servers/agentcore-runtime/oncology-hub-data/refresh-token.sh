#!/usr/bin/env bash
# Auto-refresh the Cognito M2M bearer token for the oncology-hub-data MCP server so Quick Desktop
# users don't hit the ~60-min TTL. Mints a fresh token from the (reused) OLS Cognito and writes it to
# a token file that a Quick/MCP client config can reference.
#
# Modes:
#   ./refresh-token.sh --once      mint once, write token file, print path, exit
#   ./refresh-token.sh             daemon: re-mint every REFRESH_INTERVAL (default 3000s = 50 min)
#
# Env: REGION (us-west-2), OLS_APP (ontology-lookup-service), DATA_APP (oncology-hub-data),
#      TOKEN_FILE (~/.oncology-hub-mcp/token), URL_FILE (~/.oncology-hub-mcp/mcp_url),
#      REFRESH_INTERVAL (3000).
#
# Wiring into Quick: point the MCP server's Authorization header at the token file if your client
# supports file/command-sourced headers; otherwise run `--once` and paste $(cat TOKEN_FILE), and keep
# the daemon running so the file always holds a valid token.
set -euo pipefail
REGION="${REGION:-us-west-2}"
OLS_APP="${OLS_APP:-ontology-lookup-service}"
DATA_APP="${DATA_APP:-oncology-hub-data}"
DIR="${HOME}/.oncology-hub-mcp"
TOKEN_FILE="${TOKEN_FILE:-${DIR}/token}"
URL_FILE="${URL_FILE:-${DIR}/mcp_url}"
REFRESH_INTERVAL="${REFRESH_INTERVAL:-3000}"
OLS="/app/${OLS_APP}/agentcore"
mkdir -p "$DIR"; chmod 700 "$DIR"

_get() { aws ssm get-parameter --name "$1" --query Parameter.Value --output text --region "$REGION"; }

# Read static Cognito config + MCP URL once.
TOKEN_URL=$(_get "${OLS}/cognito_token_url")
CLIENT_ID=$(_get "${OLS}/machine_client_id")
CLIENT_SECRET=$(_get "${OLS}/cognito_secret")
SCOPE=$(_get "${OLS}/cognito_auth_scope")
_get "/app/${DATA_APP}/agentcore/mcp_url" > "$URL_FILE"

mint() {
  local tok
  tok=$(curl -s -X POST "$TOKEN_URL" \
      -H "Content-Type: application/x-www-form-urlencoded" --data @- <<EOF | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])"
grant_type=client_credentials&client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&scope=${SCOPE}
EOF
)
  if [ -z "$tok" ]; then echo "[ERR] token mint failed" >&2; return 1; fi
  umask 077; printf '%s' "$tok" > "$TOKEN_FILE"
  echo "[OK] $(date '+%H:%M:%S') token refreshed -> $TOKEN_FILE (${#tok} chars)"
}

if [ "${1:-}" = "--once" ]; then
  mint
  echo "MCP URL: $(cat "$URL_FILE")"
  echo "Token file: $TOKEN_FILE"
  exit 0
fi

echo "[daemon] refreshing every ${REFRESH_INTERVAL}s. Token: $TOKEN_FILE  URL: $URL_FILE  (Ctrl-C to stop)"
while true; do
  mint || true
  sleep "$REFRESH_INTERVAL"
done
