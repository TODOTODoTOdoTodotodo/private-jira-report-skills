#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ENV_FILE=~/.codex/jira_env \
  START_DATE=YYYY/MM/DD END_DATE=YYYY/MM/DD \
  OUTPUT_DIR=/path/to/output \
  ./jira-itpt-report.sh

Required env:
  ENV_FILE       Path to env file with JIRA_* credentials.
  START_DATE     Start date (inclusive), YYYY/MM/DD (or use YEAR+MONTH)
  END_DATE       End date (exclusive), YYYY/MM/DD (or use YEAR+MONTH)

Optional env:
  OUTPUT_DIR      Output directory (default: current dir)
  CONCURRENCY     Parallelism for export (default: 8)
  PROJECTS        Project filter (default: MGTT,ITPT)
  MAX_DEPTH       Traverse depth (default: 5)
  YEAR            Year for month-based export (e.g. 2026)
  MONTH           Month for month-based export (1-12)
  WEEKLY_SPLIT    Split range into 7-day chunks (default: 1 for YEAR+MONTH, else 0)
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${ENV_FILE:-}" ]]; then
  usage
  exit 1
fi

OUTPUT_DIR="${OUTPUT_DIR:-$PWD}"
mkdir -p "$OUTPUT_DIR"
CONCURRENCY="${CONCURRENCY:-8}"
PROJECTS="${PROJECTS:-MGTT,ITPT}"
MAX_DEPTH="${MAX_DEPTH:-5}"
MATCH_MODE="${MATCH_MODE:-any}"
MAX_PAGES="${MAX_PAGES:-0}"
MAX_RESULTS="${MAX_RESULTS:-100}"
WEEKLY_SPLIT="${WEEKLY_SPLIT:-}"

RANGE_START="${START_DATE:-}"
RANGE_END="${END_DATE:-}"
NO_DATE_FILTER="${NO_DATE_FILTER:-}"
COMMENT_AUTHOR_DISPLAY="${COMMENT_AUTHOR_DISPLAY:-}"

if [[ -n "${YEAR:-}" && -n "${MONTH:-}" ]]; then
  if [[ -z "$WEEKLY_SPLIT" ]]; then
    WEEKLY_SPLIT="1"
  fi
  read -r RANGE_START RANGE_END < <(python3 - <<'PY'
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

if [[ -z "$RANGE_START" || -z "$RANGE_END" ]]; then
  usage
  exit 1
fi

if [[ -n "${EXPORT_START:-}" && -n "${EXPORT_END:-}" ]]; then
  RANGE_START="$EXPORT_START"
  RANGE_END="$EXPORT_END"
fi

if [[ -z "$WEEKLY_SPLIT" ]]; then
  WEEKLY_SPLIT="0"
fi


SOURCE_JSON="${OUTPUT_DIR}/jira-source.json"
ROOTS_TXT="${OUTPUT_DIR}/roots.txt"
MISSING_TXT="${OUTPUT_DIR}/missing-keys.txt"
CSV_OUT="${OUTPUT_DIR}/itpt-links.csv"

EXPORT_SCRIPT="${HOME}/.codex/skills/jira-source-export/scripts/jira-source-export-fast.py"
TRAVERSE_SCRIPT="${HOME}/.codex/skills/jira-itpt-report/scripts/jira-traverse-root-itpt.py"
ROOTS_SCRIPT="${HOME}/.codex/skills/jira-itpt-report/scripts/jira-build-roots.py"

if [[ "$WEEKLY_SPLIT" == "1" ]]; then
  SPLIT_DAYS="${SPLIT_DAYS:-7}"
  RANGES_FILE="${OUTPUT_DIR}/weekly-ranges.txt"
  RANGE_START="$RANGE_START" RANGE_END="$RANGE_END" SPLIT_DAYS="$SPLIT_DAYS" python3 - <<'PY' > "$RANGES_FILE"
import datetime as dt
import os

start = dt.datetime.strptime(os.environ["RANGE_START"], "%Y/%m/%d").date()
end = dt.datetime.strptime(os.environ["RANGE_END"], "%Y/%m/%d").date()
split_days = int(os.environ.get("SPLIT_DAYS", "7"))
cur = start
while cur < end:
  nxt = min(cur + dt.timedelta(days=split_days), end)
  print(cur.strftime("%Y/%m/%d"), nxt.strftime("%Y/%m/%d"))
  cur = nxt
PY

  WEEK_SOURCES=()
  PARALLEL_RANGES="${PARALLEL_RANGES:-1}"
  if [[ "$PARALLEL_RANGES" -le 1 ]]; then
    while read -r WEEK_START WEEK_END; do
      WEEK_DIR="${OUTPUT_DIR}/week-${WEEK_START//\//}-${WEEK_END//\//}"
      mkdir -p "$WEEK_DIR"
      WEEK_SOURCE="${WEEK_DIR}/jira-source.json"
      ENV_FILE="$ENV_FILE" \
      START_DATE="$WEEK_START" END_DATE="$WEEK_END" \
      PROJECTS="$PROJECTS" MATCH_MODE="$MATCH_MODE" CONCURRENCY="$CONCURRENCY" \
      MAX_PAGES="$MAX_PAGES" MAX_RESULTS="$MAX_RESULTS" \
      NO_DATE_FILTER="$NO_DATE_FILTER" \
      COMMENT_AUTHOR_DISPLAY="$COMMENT_AUTHOR_DISPLAY" \
      COMMENT_JQL_TEMPLATE="${COMMENT_JQL_TEMPLATE:-}" \
      COMMENT_JQL="${COMMENT_JQL:-}" \
      COMMENT_MATCH="${COMMENT_MATCH:-}" \
      ASSIGNEE_JQL="${ASSIGNEE_JQL:-}" \
      python3 "$EXPORT_SCRIPT" "$WEEK_SOURCE"
      WEEK_SOURCES+=("$WEEK_SOURCE")
    done < "$RANGES_FILE"
  else
    export OUTPUT_DIR ENV_FILE PROJECTS MATCH_MODE CONCURRENCY MAX_PAGES MAX_RESULTS
    export NO_DATE_FILTER COMMENT_AUTHOR_DISPLAY COMMENT_JQL_TEMPLATE COMMENT_JQL
    export COMMENT_MATCH ASSIGNEE_JQL EXPORT_SCRIPT
    while read -r WEEK_START WEEK_END; do
      WEEK_SOURCES+=("${OUTPUT_DIR}/week-${WEEK_START//\//}-${WEEK_END//\//}/jira-source.json")
    done < "$RANGES_FILE"

    cat "$RANGES_FILE" | xargs -n 2 -P "$PARALLEL_RANGES" bash -c '
      WEEK_START="$1"
      WEEK_END="$2"
      WEEK_DIR="${OUTPUT_DIR}/week-${WEEK_START//\//}-${WEEK_END//\//}"
      mkdir -p "$WEEK_DIR"
      WEEK_SOURCE="${WEEK_DIR}/jira-source.json"
      if [[ -s "$WEEK_SOURCE" ]]; then
        exit 0
      fi
      ENV_FILE="$ENV_FILE" \
      START_DATE="$WEEK_START" END_DATE="$WEEK_END" \
      PROJECTS="$PROJECTS" MATCH_MODE="$MATCH_MODE" CONCURRENCY="$CONCURRENCY" \
      MAX_PAGES="$MAX_PAGES" MAX_RESULTS="$MAX_RESULTS" \
      NO_DATE_FILTER="$NO_DATE_FILTER" \
      COMMENT_AUTHOR_DISPLAY="$COMMENT_AUTHOR_DISPLAY" \
      COMMENT_JQL_TEMPLATE="$COMMENT_JQL_TEMPLATE" \
      COMMENT_JQL="$COMMENT_JQL" \
      COMMENT_MATCH="$COMMENT_MATCH" \
      ASSIGNEE_JQL="$ASSIGNEE_JQL" \
      python3 "$EXPORT_SCRIPT" "$WEEK_SOURCE"
    ' _
  fi

  python3 - "$SOURCE_JSON" "${WEEK_SOURCES[@]}" <<'PY'
import json
import sys

out = sys.argv[1]
paths = sys.argv[2:]
by_key = {}

def merge_issue(dst, src):
  for k, v in src.items():
    if k not in dst or dst[k] in (None, "", [], {}):
      dst[k] = v
  if "issuelinks" in src:
    dst_links = dst.get("issuelinks") or []
    seen = {(l.get("issue_key"), l.get("type"), l.get("inward"), l.get("outward")) for l in dst_links}
    for l in src.get("issuelinks") or []:
      sig = (l.get("issue_key"), l.get("type"), l.get("inward"), l.get("outward"))
      if sig not in seen:
        dst_links.append(l)
        seen.add(sig)
    dst["issuelinks"] = dst_links

for path in paths:
  with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
  for issue in data:
    key = issue.get("issue_key")
    if not key:
      continue
    if key not in by_key:
      by_key[key] = issue
    else:
      merge_issue(by_key[key], issue)

with open(out, "w", encoding="utf-8") as f:
  json.dump(list(by_key.values()), f, ensure_ascii=False, indent=2)
PY
else
  ENV_FILE="$ENV_FILE" \
  START_DATE="$RANGE_START" END_DATE="$RANGE_END" \
  PROJECTS="$PROJECTS" MATCH_MODE="$MATCH_MODE" CONCURRENCY="$CONCURRENCY" \
  MAX_PAGES="$MAX_PAGES" MAX_RESULTS="$MAX_RESULTS" \
  NO_DATE_FILTER="$NO_DATE_FILTER" \
  COMMENT_AUTHOR_DISPLAY="$COMMENT_AUTHOR_DISPLAY" \
  python3 "$EXPORT_SCRIPT" "$SOURCE_JSON"
fi

python3 "$ROOTS_SCRIPT" "$SOURCE_JSON" "$ROOTS_TXT" --prefix MGTT-

MERGE_START="${MERGE_START:-$RANGE_START}"
MERGE_END="${MERGE_END:-$RANGE_END}"
ROLE_MODE="${ROLE_MODE:-}"
if [[ -z "$ROLE_MODE" ]]; then
  ROLE_MODE="dev"
fi
DEVSTATUS_CACHE="${DEVSTATUS_CACHE:-$OUTPUT_DIR/devstatus-cache.json}"

TRAVERSE_ARGS=(
  "$SOURCE_JSON"
  --batch-file "$ROOTS_TXT"
  --max-depth "$MAX_DEPTH"
  --csv-output "$CSV_OUT"
  --env-file "$ENV_FILE"
  --role-mode "$ROLE_MODE"
)

if [[ "$ROLE_MODE" == "dev" ]]; then
  TRAVERSE_ARGS+=(--include-master-merge --merge-start "$MERGE_START" --merge-end "$MERGE_END" --devstatus-cache "$DEVSTATUS_CACHE")
fi

python3 "$TRAVERSE_SCRIPT" "${TRAVERSE_ARGS[@]}"

if [[ -s "$MISSING_TXT" ]]; then
  echo "Missing keys detected. Use MCP to fetch and merge before final report:" >&2
  echo "  missing-keys: $MISSING_TXT" >&2
  echo "  source-json:  $SOURCE_JSON" >&2
  echo "  csv:          $CSV_OUT (partial)" >&2
  echo "Next: fetch missing via MCP, create jira-source-supplement.json, then merge with jira-merge-source.py and re-run traverse on merged JSON." >&2
else
  echo "Report generated: $CSV_OUT"
fi
