#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  YEAR=YYYY MONTH=MM PROJECTS=MGTT,ITPT \
  ENV_FILE=~/.codex/jira_env OUTPUT_DIR=/path/to/output \
  ./private-jira-report.sh

Required env:
  YEAR         Year (e.g., 2026)
  MONTH        Month (1-12)

Optional env:
  PROJECTS     Project filter (default: MGTT,ITPT)
  ENV_FILE     Jira env file (default: ~/.codex/jira_env)
  OUTPUT_DIR   Output directory (default: ~/Downloads/itpt-YYYY-MM)
  CSV_SEED     Jira CSV export path (assignee=currentUser) for faster seeding
  EXPORT_START Export range start (YYYY/MM/DD)
  EXPORT_END   Export range end (YYYY/MM/DD)
  MERGE_START  PR merge range start (YYYY/MM/DD)
  MERGE_END    PR merge range end (YYYY/MM/DD)
  COMMENT_AUTHOR_DISPLAY Comment author display names (comma-separated)
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${YEAR:-}" || -z "${MONTH:-}" ]]; then
  usage
  exit 1
fi

PROJECTS="${PROJECTS:-MGTT,ITPT}"
ENV_FILE="${ENV_FILE:-$HOME/.codex/jira_env}"

MONTH_PADDED="$(printf "%02d" "$MONTH")"
OUTPUT_DIR="${OUTPUT_DIR:-$HOME/Downloads/itpt-${YEAR}-${MONTH_PADDED}}"

EXPORT_START="${EXPORT_START:-}"
EXPORT_END="${EXPORT_END:-}"
MERGE_START="${MERGE_START:-}"
MERGE_END="${MERGE_END:-}"
COMMENT_AUTHOR_DISPLAY="${COMMENT_AUTHOR_DISPLAY:-}"
CSV_SEED="${CSV_SEED:-}"
ASSIGNEE_ACCOUNT_IDS="${ASSIGNEE_ACCOUNT_IDS:-${ASSIGNEE_ACCOUNT_ID:-}}"

if [[ -z "$MERGE_START" || -z "$MERGE_END" ]]; then
  read -r MERGE_START MERGE_END < <(python3 - <<'PY'
import datetime as dt
import os
year = int(os.environ["YEAR"])
month = int(os.environ["MONTH"])
start = dt.date(year, month, 1)
if month == 12:
  end = dt.date(year + 1, 1, 1)
else:
  end = dt.date(year, month + 1, 1)
print(start.strftime("%Y/%m/%d"), end.strftime("%Y/%m/%d"))
PY
  )
fi

MCP_CONNECT="${HOME}/.codex/skills/atlassian-mcp-connect/scripts/atlassian_mcp_connect.sh"
REPORT_SCRIPT="${HOME}/.codex/skills/jira-itpt-report/scripts/jira-itpt-report.sh"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing ENV_FILE: $ENV_FILE" >&2
  echo "Create it from template: $HOME/.codex/jira_env_template" >&2
  exit 1
fi

if [[ -z "${JIRA_BASE_URL:-}" || -z "${JIRA_EMAIL:-}" || -z "${JIRA_API_TOKEN:-}" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* || "$line" != *"="* ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    key="$(echo "$key" | xargs)"
    val="$(echo "$val" | xargs)"
    case "$key" in
      JIRA_BASE_URL|JIRA_EMAIL|JIRA_API_TOKEN|JIRA_ACCOUNT_ID)
        export "$key"="${val%\"}"
        export "$key"="${!key#\"}"
        export "$key"="${!key%\'}"
        export "$key"="${!key#\'}"
        ;;
    esac
  done < "$ENV_FILE"
fi

if [[ -z "${JIRA_BASE_URL:-}" || -z "${JIRA_EMAIL:-}" || -z "${JIRA_API_TOKEN:-}" ]]; then
  echo "Missing JIRA_* in $ENV_FILE (JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN)." >&2
  exit 1
fi

if [[ -n "${ASSIGNEE_ACCOUNT_IDS:-}" && -z "${JIRA_ACCOUNT_ID:-}" ]]; then
  if [[ "$ASSIGNEE_ACCOUNT_IDS" != *,* ]]; then
    export JIRA_ACCOUNT_ID="$ASSIGNEE_ACCOUNT_IDS"
  fi
elif [[ -n "${ASSIGNEE_ACCOUNT_ID:-}" && -z "${JIRA_ACCOUNT_ID:-}" ]]; then
  export JIRA_ACCOUNT_ID="$ASSIGNEE_ACCOUNT_ID"
fi
export ASSIGNEE_ACCOUNT_ID ASSIGNEE_ACCOUNT_IDS

ATLASSIAN_DOMAIN="${ATLASSIAN_DOMAIN:-${JIRA_BASE_URL#https://}}"
ATLASSIAN_DOMAIN="${ATLASSIAN_DOMAIN#http://}"
ATLASSIAN_DOMAIN="${ATLASSIAN_DOMAIN%%/*}"
ATLASSIAN_EMAIL="${ATLASSIAN_EMAIL:-$JIRA_EMAIL}"
ATLASSIAN_API_TOKEN="${ATLASSIAN_API_TOKEN:-$JIRA_API_TOKEN}"
export ATLASSIAN_DOMAIN ATLASSIAN_EMAIL ATLASSIAN_API_TOKEN

ATLASSIAN_MCP_CONFIG="${ATLASSIAN_MCP_CONFIG:-$HOME/.atlassian-mcp.json}"
cat > "$ATLASSIAN_MCP_CONFIG" <<EOF
{
  "domain": "$ATLASSIAN_DOMAIN",
  "email": "$ATLASSIAN_EMAIL",
  "apiToken": "$ATLASSIAN_API_TOKEN"
}
EOF

ENV_FILE="$ENV_FILE" "$MCP_CONNECT" >/dev/null

ENV_FILE="$ENV_FILE" \
YEAR="$YEAR" MONTH="$MONTH" \
PROJECTS="$PROJECTS" \
MERGE_START="$MERGE_START" MERGE_END="$MERGE_END" \
EXPORT_START="$EXPORT_START" EXPORT_END="$EXPORT_END" \
COMMENT_AUTHOR_DISPLAY="$COMMENT_AUTHOR_DISPLAY" \
CSV_SEED="$CSV_SEED" \
OUTPUT_DIR="$OUTPUT_DIR" \
"$REPORT_SCRIPT"

MISSING_TXT="${OUTPUT_DIR}/missing-keys.txt"
if [[ -s "$MISSING_TXT" ]]; then
  cat <<EOF >&2
Missing keys detected: $MISSING_TXT
Run finalize after MCP supplementation:
  OUTPUT_DIR="$OUTPUT_DIR" ~/.codex/skills/jira-itpt-report-finalize/scripts/jira-itpt-finalize.sh
EOF
fi
