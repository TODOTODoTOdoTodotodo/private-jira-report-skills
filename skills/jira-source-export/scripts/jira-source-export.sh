#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  JIRA_BASE_URL="https://your-jira.atlassian.net" \
  JIRA_EMAIL="user@example.com" \
  JIRA_API_TOKEN="api_token" \
  ./jira-source-export.sh [output_json]

Optional env:
  YEAR=2025                 # Year to search (default 2025)
  MONTH=1                   # 1-12 to limit search to a month
  START_DATE=YYYY/MM/DD     # Override start date (inclusive)
  END_DATE=YYYY/MM/DD       # Override end date (exclusive)
  MATCH_MODE=any            # any|comment|assignee|both (default any = union)
  PROJECTS=KEY1,KEY2        # Comma-separated project keys to limit scope
  JQL_EXTRA=...             # Extra JQL appended with AND
  MAX_RESULTS=100           # Page size for search
  PROGRESS=1                # 1 to print progress to stderr
  PROGRESS_EVERY=50         # Progress update frequency for issue loops
  SLEEP_SECONDS=0           # Sleep between comment requests
  MAX_RETRIES=5             # Rate-limit retries per request
  BACKOFF_SECONDS=2         # Initial backoff when rate-limited
  JIRA_ACCOUNT_ID=...       # If unset, the script will fetch it via /myself

Notes:
- Requires curl and jq.
- Output is JSON array with issue key, summary, project, issuetype, parent, and issue links.
- Comment matching scans issue comments and checks author + created date range.
USAGE
}

jira_request() {
  local context="$1"
  shift
  local attempt=0
  local backoff="${BACKOFF_SECONDS:-2}"
  local max_retries="${MAX_RETRIES:-5}"
  local headers
  local body
  local status
  local retry_after
  local wait_seconds

  while :; do
    headers=$(mktemp)
    body=$(mktemp)
    if ! curl -sS -D "$headers" -o "$body" -u "$AUTH" "$@"; then
      status="curl_error"
    else
      status=$(awk 'NR==1 {print $2}' "$headers")
    fi

    if [[ "$status" == "429" || "$status" == "503" || "$status" == "curl_error" ]]; then
      retry_after=$(awk 'BEGIN{IGNORECASE=1} /^Retry-After:/ {print $2}' "$headers" | tr -d '\r')
      wait_seconds="${retry_after:-$backoff}"
      attempt=$((attempt + 1))
      if [[ "$attempt" -gt "$max_retries" ]]; then
        echo "Request failed ($context) after $max_retries retries." >&2
        cat "$body" >&2
        rm -f "$headers" "$body"
        exit 1
      fi
      sleep "$wait_seconds"
      if [[ -z "$retry_after" ]]; then
        backoff=$((backoff * 2))
      fi
      rm -f "$headers" "$body"
      continue
    fi

    cat "$body"
    rm -f "$headers" "$body"
    return 0
  done
}

log_progress() {
  if [[ "${PROGRESS:-1}" == "1" ]]; then
    echo "$1" >&2
  fi
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

for bin in curl jq; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "Missing dependency: $bin" >&2
    exit 1
  fi
done

BASE_URL="${JIRA_BASE_URL:-}"
EMAIL="${JIRA_EMAIL:-}"
TOKEN="${JIRA_API_TOKEN:-}"
YEAR="${YEAR:-2025}"
MONTH="${MONTH:-}"
PROJECTS="${PROJECTS:-}"
JQL_EXTRA="${JQL_EXTRA:-}"
START_DATE_OVERRIDE="${START_DATE:-}"
END_DATE_OVERRIDE="${END_DATE:-}"
MATCH_MODE="${MATCH_MODE:-any}"
MAX_RESULTS="${MAX_RESULTS:-100}"
PROGRESS_EVERY="${PROGRESS_EVERY:-50}"
SLEEP_SECONDS="${SLEEP_SECONDS:-0}"

if [[ -z "$BASE_URL" || -z "$EMAIL" || -z "$TOKEN" ]]; then
  echo "JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN must be set." >&2
  usage
  exit 1
fi

NEXT_YEAR=$((YEAR + 1))
START_DATE="${YEAR}/01/01"
END_DATE="${NEXT_YEAR}/01/01"
START_TS="${YEAR}-01-01T00:00:00.000+0000"
END_TS="${NEXT_YEAR}-01-01T00:00:00.000+0000"

if [[ -n "$MONTH" ]]; then
  if ! [[ "$MONTH" =~ ^[0-9]+$ ]]; then
    echo "MONTH must be a number between 1 and 12." >&2
    exit 1
  fi
  if (( MONTH < 1 || MONTH > 12 )); then
    echo "MONTH must be between 1 and 12." >&2
    exit 1
  fi
  month_padded=$(printf "%02d" "$MONTH")
  START_DATE="${YEAR}/${month_padded}/01"
  if (( MONTH == 12 )); then
    END_DATE="${NEXT_YEAR}/01/01"
  else
    next_month=$((MONTH + 1))
    next_month_padded=$(printf "%02d" "$next_month")
    END_DATE="${YEAR}/${next_month_padded}/01"
  fi
  START_TS="${START_DATE//\//-}T00:00:00.000+0000"
  END_TS="${END_DATE//\//-}T00:00:00.000+0000"
fi

if [[ -n "$START_DATE_OVERRIDE" && -n "$END_DATE_OVERRIDE" ]]; then
  START_DATE="$START_DATE_OVERRIDE"
  END_DATE="$END_DATE_OVERRIDE"
  START_TS="${START_DATE_OVERRIDE//\//-}T00:00:00.000+0000"
  END_TS="${END_DATE_OVERRIDE//\//-}T00:00:00.000+0000"
elif [[ -n "$START_DATE_OVERRIDE" || -n "$END_DATE_OVERRIDE" ]]; then
  echo "Both START_DATE and END_DATE must be set together." >&2
  exit 1
fi

AUTH="${EMAIL}:${TOKEN}"
OUTPUT="${1:-jira-source-${YEAR}.json}"

if [[ -z "${JIRA_ACCOUNT_ID:-}" ]]; then
  account_resp=$(jira_request "myself" "$BASE_URL/rest/api/3/myself")
  JIRA_ACCOUNT_ID=$(echo "$account_resp" | jq -r '.accountId')
  if [[ -z "$JIRA_ACCOUNT_ID" || "$JIRA_ACCOUNT_ID" == "null" ]]; then
    echo "Failed to resolve accountId from /myself." >&2
    exit 1
  fi
fi

comment_jql="updated >= \"$START_DATE\" AND updated < \"$END_DATE\""
assignee_jql="assignee WAS currentUser() DURING (\"$START_DATE\",\"$END_DATE\")"

if [[ -n "$PROJECTS" ]]; then
  project_filter="project in ($(echo "$PROJECTS" | tr ',' ' '))"
  comment_jql="$comment_jql AND $project_filter"
  assignee_jql="$assignee_jql AND $project_filter"
fi

if [[ -n "$JQL_EXTRA" ]]; then
  comment_jql="$comment_jql AND $JQL_EXTRA"
  assignee_jql="$assignee_jql AND $JQL_EXTRA"
fi

case "$MATCH_MODE" in
  any|comment|assignee|both)
    ;;
  *)
    echo "MATCH_MODE must be one of: any, comment, assignee, both." >&2
    exit 1
    ;;
esac

log_progress "date range: $START_DATE to $END_DATE"
log_progress "match mode: $MATCH_MODE"

comment_keys_file=$(mktemp)
comment_matches_file=$(mktemp)
assignee_keys_file=$(mktemp)
combined_keys_file=$(mktemp)
comment_sorted_file=$(mktemp)
assignee_sorted_file=$(mktemp)
final_keys_file=$(mktemp)
json_lines_file=$(mktemp)
trap 'rm -f "$comment_keys_file" "$comment_matches_file" "$assignee_keys_file" "$combined_keys_file" "$comment_sorted_file" "$assignee_sorted_file" "$final_keys_file" "$json_lines_file"' EXIT

if [[ "$MATCH_MODE" == "any" || "$MATCH_MODE" == "comment" || "$MATCH_MODE" == "both" ]]; then
  start_at=0
  while :; do
    resp=$(jira_request "comment search page" \
      -G "$BASE_URL/rest/api/3/search/jql" \
      --data-urlencode "jql=$comment_jql" \
      --data-urlencode 'fields=key' \
      --data-urlencode "startAt=$start_at" \
      --data-urlencode "maxResults=$MAX_RESULTS")
    total=$(echo "$resp" | jq -r '.total')
    page_count=$(echo "$resp" | jq -r '.issues | length')
    echo "$resp" | jq -r '.issues[].key' >> "$comment_keys_file"
    start_at=$((start_at + MAX_RESULTS))
    if [[ -n "$total" && "$total" != "null" ]]; then
      if [[ "$start_at" -ge "$total" ]]; then
        break
      fi
    else
      if [[ "$page_count" -lt "$MAX_RESULTS" ]]; then
        break
      fi
    fi
  done

  issue_count=0
  while IFS= read -r key; do
    issue_count=$((issue_count + 1))
    if (( issue_count % PROGRESS_EVERY == 0 )); then
      log_progress "comment scan ${issue_count} issues..."
    fi
    comment_start=0
    comment_max=100
    found=0

    while :; do
      comments=$(jira_request "comment list $key" \
        "$BASE_URL/rest/api/3/issue/$key/comment?startAt=$comment_start&maxResults=$comment_max")

  total_comments=$(echo "$comments" | jq -r '.total')
      match=$(echo "$comments" | jq -r --arg aid "$JIRA_ACCOUNT_ID" --arg start "$START_TS" --arg end "$END_TS" '
        .comments[]
        | select(.author.accountId == $aid)
        | select(.created >= $start and .created < $end)
        | .id' | head -n 1)

      if [[ -n "$match" ]]; then
        found=1
        break
      fi

  comment_start=$((comment_start + comment_max))
  if [[ -n "$total_comments" && "$total_comments" != "null" ]]; then
    if [[ "$comment_start" -ge "$total_comments" ]]; then
      break
    fi
  else
    break
  fi
    done

    if [[ "$found" -eq 1 ]]; then
      printf "%s\n" "$key" >> "$comment_matches_file"
    fi

    if [[ "$SLEEP_SECONDS" != "0" ]]; then
      sleep "$SLEEP_SECONDS"
    fi
  done < "$comment_keys_file"
fi

if [[ "$MATCH_MODE" == "any" || "$MATCH_MODE" == "assignee" || "$MATCH_MODE" == "both" ]]; then
  start_at=0
  while :; do
    resp=$(jira_request "assignee search page" \
      -G "$BASE_URL/rest/api/3/search/jql" \
      --data-urlencode "jql=$assignee_jql" \
      --data-urlencode 'fields=key' \
      --data-urlencode "startAt=$start_at" \
      --data-urlencode "maxResults=$MAX_RESULTS")
    total=$(echo "$resp" | jq -r '.total')
    page_count=$(echo "$resp" | jq -r '.issues | length')
    echo "$resp" | jq -r '.issues[].key' >> "$assignee_keys_file"
    start_at=$((start_at + MAX_RESULTS))
    if [[ -n "$total" && "$total" != "null" ]]; then
      if [[ "$start_at" -ge "$total" ]]; then
        break
      fi
    else
      if [[ "$page_count" -lt "$MAX_RESULTS" ]]; then
        break
      fi
    fi
  done
fi

if [[ "$MATCH_MODE" == "comment" ]]; then
  LC_ALL=C sort -u "$comment_matches_file" > "$final_keys_file"
elif [[ "$MATCH_MODE" == "assignee" ]]; then
  LC_ALL=C sort -u "$assignee_keys_file" > "$final_keys_file"
elif [[ "$MATCH_MODE" == "both" ]]; then
  LC_ALL=C sort -u "$comment_matches_file" > "$comment_sorted_file"
  LC_ALL=C sort -u "$assignee_keys_file" > "$assignee_sorted_file"
  comm -12 "$comment_sorted_file" "$assignee_sorted_file" > "$final_keys_file"
else
  cat "$comment_matches_file" "$assignee_keys_file" >> "$combined_keys_file"
  LC_ALL=C sort -u "$combined_keys_file" > "$final_keys_file"
fi

issue_count=0
while IFS= read -r key; do
  issue_count=$((issue_count + 1))
  if (( issue_count % PROGRESS_EVERY == 0 )); then
    log_progress "issue fetch ${issue_count} issues..."
  fi
  issue=$(jira_request "issue $key" \
    -G "$BASE_URL/rest/api/3/issue/$key" \
    --data-urlencode 'fields=summary,issuetype,project,parent,issuelinks')
  echo "$issue" | jq -c '
    {
      issue_key: .key,
      summary: .fields.summary,
      project_key: .fields.project.key,
      issuetype: .fields.issuetype.name,
      parent_key: (.fields.parent.key // null),
      issuelinks: [
        .fields.issuelinks[]? | {
          type: .type.name,
          inward: .type.inward,
          outward: .type.outward,
          issue_key: (.inwardIssue.key // .outwardIssue.key)
        }
      ]
    }' >> "$json_lines_file"
done < "$final_keys_file"

jq -s '.' "$json_lines_file" > "$OUTPUT"
echo "Wrote: $OUTPUT"
