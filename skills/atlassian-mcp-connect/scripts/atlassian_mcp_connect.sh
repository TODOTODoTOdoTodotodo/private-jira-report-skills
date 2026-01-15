#!/usr/bin/env bash
set -euo pipefail

load_env_file() {
  local path="${ENV_FILE:-}"
  if [[ -z "$path" ]]; then
    return 0
  fi
  if [[ ! -f "$path" ]]; then
    echo "ENV_FILE not found: $path" >&2
    exit 1
  fi
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* || "$line" != *"="* ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    key="$(echo "$key" | xargs)"
    val="$(echo "$val" | xargs)"
    if [[ -z "${!key:-}" ]]; then
      export "$key"="${val%\"}"
      export "$key"="${!key#\"}"
      export "$key"="${!key%\'}"
      export "$key"="${!key#\'}"
    fi
  done < "$path"
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env: $name" >&2
    exit 1
  fi
}

load_env_file

NAME="${MCP_SERVER_NAME:-atlassian-local}"

if [[ -z "${JIRA_INSTANCE_URL:-}" && -n "${JIRA_BASE_URL:-}" ]]; then
  export JIRA_INSTANCE_URL="$JIRA_BASE_URL"
fi
if [[ -z "${JIRA_USERNAME:-}" && -n "${JIRA_EMAIL:-}" ]]; then
  export JIRA_USERNAME="$JIRA_EMAIL"
fi

if [[ -z "${ATLASSIAN_DOMAIN:-}" ]]; then
  base="${JIRA_INSTANCE_URL:-$JIRA_BASE_URL}"
  if [[ -n "$base" ]]; then
    ATLASSIAN_DOMAIN="${base#https://}"
    ATLASSIAN_DOMAIN="${ATLASSIAN_DOMAIN#http://}"
    ATLASSIAN_DOMAIN="${ATLASSIAN_DOMAIN%%/*}"
    export ATLASSIAN_DOMAIN
  fi
fi
if [[ -z "${ATLASSIAN_EMAIL:-}" && -n "${JIRA_EMAIL:-}" ]]; then
  export ATLASSIAN_EMAIL="$JIRA_EMAIL"
fi
if [[ -z "${ATLASSIAN_API_TOKEN:-}" && -n "${JIRA_API_TOKEN:-}" ]]; then
  export ATLASSIAN_API_TOKEN="$JIRA_API_TOKEN"
fi

require_env ATLASSIAN_DOMAIN
require_env ATLASSIAN_EMAIL
require_env ATLASSIAN_API_TOKEN

ATLASSIAN_MCP_CONFIG="${ATLASSIAN_MCP_CONFIG:-$HOME/.atlassian-mcp.json}"
cat > "$ATLASSIAN_MCP_CONFIG" <<EOF
{
  "domain": "$ATLASSIAN_DOMAIN",
  "email": "$ATLASSIAN_EMAIL",
  "apiToken": "$ATLASSIAN_API_TOKEN"
}
EOF

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found in PATH." >&2
  exit 1
fi

codex mcp remove "$NAME" >/dev/null 2>&1 || true
codex mcp add "$NAME" -- npx -y @xuandev/atlassian-mcp
codex mcp list
