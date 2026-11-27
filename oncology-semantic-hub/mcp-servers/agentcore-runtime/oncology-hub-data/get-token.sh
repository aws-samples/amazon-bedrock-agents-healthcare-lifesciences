#!/usr/bin/env bash
# Mint a Cognito M2M bearer token (reusing the OLS Cognito) and export the data MCP URL + token.
#
# IMPORTANT: SOURCE this file so the exports land in your shell:
#   source ./get-token.sh
# It deliberately does NOT use `set -e`/`exit` — a sourced script with those would kill your
# interactive terminal on any error. On failure it prints a diagnostic and leaves the vars empty.
#
# Env: REGION (us-west-2), OLS_APP (ontology-lookup-service), DATA_APP (oncology-hub-data).

_ght_region="${REGION:-us-west-2}"
_ght_ols="/app/${OLS_APP:-ontology-lookup-service}/agentcore"
_ght_data="/app/${DATA_APP:-oncology-hub-data}/agentcore"

_ght_get() { aws ssm get-parameter --name "$1" --query Parameter.Value --output text --region "$_ght_region" 2>/dev/null; }

_ght_token_url="$(_ght_get "${_ght_ols}/cognito_token_url")"
_ght_client_id="$(_ght_get "${_ght_ols}/machine_client_id")"
_ght_client_secret="$(_ght_get "${_ght_ols}/cognito_secret")"
_ght_scope="$(_ght_get "${_ght_ols}/cognito_auth_scope")"
export HUB_MCP_URL="$(_ght_get "${_ght_data}/mcp_url")"

if [ -z "$_ght_token_url" ] || [ -z "$_ght_client_id" ] || [ -z "$_ght_client_secret" ]; then
  echo "[ERR] Could not read Cognito params from SSM under ${_ght_ols}." >&2
  echo "      Check: 'aws sts get-caller-identity' works, region=${_ght_region}, and you have ssm:GetParameter." >&2
elif [ -z "$HUB_MCP_URL" ]; then
  echo "[ERR] Could not read ${_ght_data}/mcp_url from SSM (is oncology-hub-data deployed in ${_ght_region}?)." >&2
else
  _ght_resp="$(curl -s -X POST "$_ght_token_url" \
      -H 'Content-Type: application/x-www-form-urlencoded' --data @- <<EOF
grant_type=client_credentials&client_id=${_ght_client_id}&client_secret=${_ght_client_secret}&scope=${_ght_scope}
EOF
  )"
  export HUB_MCP_TOKEN="$(printf '%s' "$_ght_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)"
  if [ -z "$HUB_MCP_TOKEN" ]; then
    echo "[ERR] Token mint failed. Cognito response (first 300 chars): ${_ght_resp:0:300}" >&2
  else
    echo "[OK] HUB_MCP_URL=${HUB_MCP_URL}"
    echo "[OK] HUB_MCP_TOKEN set (${#HUB_MCP_TOKEN} chars, ~60 min TTL)"
  fi
fi

# Clean up temporaries (never leave the secret in the shell environment).
unset _ght_region _ght_ols _ght_data _ght_token_url _ght_client_id _ght_client_secret _ght_scope _ght_resp
unset -f _ght_get 2>/dev/null
