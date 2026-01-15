#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  YEAR=YYYY \
  PROJECTS=MGTT,ITPT \
  ENV_FILE=~/.codex/jira_env \
  EXPORT_START=YYYY/MM/DD EXPORT_END=YYYY/MM/DD \
  MATCH_MODE=assignee \
  QUARTER_PARALLEL=4 PARALLEL_RANGES=4 \
  ./private-jira-report-yearly.sh

Required env:
  YEAR

Optional env:
  PROJECTS
  ENV_FILE
  OUTPUT_DIR        (default: ~/Downloads/itpt-YYYY)
  EXPORT_START/END  (default: YEAR/01/01 to YEAR+1/01/01)
  MATCH_MODE        (default: assignee)
  QUARTER_PARALLEL  (default: 4)
  PARALLEL_RANGES   (default: 4) weekly export parallelism
  CONCURRENCY, MAX_RESULTS, MAX_PAGES, HTTP_TIMEOUT (passthrough)
  COMMENT_AUTHOR_DISPLAY (passthrough)
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${YEAR:-}" ]]; then
  usage
  exit 1
fi

PROJECTS="${PROJECTS:-MGTT,ITPT}"
ENV_FILE="${ENV_FILE:-$HOME/.codex/jira_env}"
OUTPUT_DIR="${OUTPUT_DIR:-$HOME/Downloads/itpt-${YEAR}}"
MATCH_MODE="${MATCH_MODE:-assignee}"
QUARTER_PARALLEL="${QUARTER_PARALLEL:-4}"
PARALLEL_RANGES="${PARALLEL_RANGES:-4}"

EXPORT_START="${EXPORT_START:-}"
EXPORT_END="${EXPORT_END:-}"
COMMENT_AUTHOR_DISPLAY="${COMMENT_AUTHOR_DISPLAY:-}"

if [[ -z "$EXPORT_START" || -z "$EXPORT_END" ]]; then
  read -r EXPORT_START EXPORT_END < <(python3 - <<'PY'
import datetime as dt
import os
year = int(os.environ["YEAR"])
start = dt.date(year, 1, 1)
end = dt.date(year + 1, 1, 1)
print(start.strftime("%Y/%m/%d"), end.strftime("%Y/%m/%d"))
PY
  )
fi

mkdir -p "$OUTPUT_DIR"

BASE_REPORT="${HOME}/.codex/skills/private-jira-report/scripts/private-jira-report.sh"

export YEAR OUTPUT_DIR BASE_REPORT
export PROJECTS ENV_FILE EXPORT_START EXPORT_END MATCH_MODE PARALLEL_RANGES
export CONCURRENCY MAX_RESULTS MAX_PAGES HTTP_TIMEOUT COMMENT_AUTHOR_DISPLAY
export WEEKLY_SPLIT=1

quarters() {
  cat <<EOF
Q1 1 ${YEAR}/01/01 ${YEAR}/04/01
Q2 4 ${YEAR}/04/01 ${YEAR}/07/01
Q3 7 ${YEAR}/07/01 ${YEAR}/10/01
Q4 10 ${YEAR}/10/01 $((YEAR + 1))/01/01
EOF
}

quarters | xargs -n 4 -P "$QUARTER_PARALLEL" bash -c '
  set -euo pipefail
  quarter="$1"
  month="$2"
  merge_start="$3"
  merge_end="$4"
  run_quarter() {
    local q="$1"
    local m="$2"
    local ms="$3"
    local me="$4"
    local quarter_dir="${OUTPUT_DIR}/${q}"
    YEAR="$YEAR" MONTH="$m" \
    PROJECTS="$PROJECTS" ENV_FILE="$ENV_FILE" \
    OUTPUT_DIR="$quarter_dir" \
    MERGE_START="$ms" MERGE_END="$me" \
    "$BASE_REPORT"
  }
  run_quarter "$quarter" "$month" "$merge_start" "$merge_end"
' _

MERGED_CSV="${OUTPUT_DIR}/itpt-links.csv"
python3 - "$MERGED_CSV" \
  "${OUTPUT_DIR}/Q1/itpt-links.csv" \
  "${OUTPUT_DIR}/Q2/itpt-links.csv" \
  "${OUTPUT_DIR}/Q3/itpt-links.csv" \
  "${OUTPUT_DIR}/Q4/itpt-links.csv" <<'PY'
import csv
import os
import sys

out = sys.argv[1]
paths = sys.argv[2:]

rows = []
seen = set()
fieldnames = None

for path in paths:
  if not os.path.exists(path):
    raise SystemExit(f"Missing quarter report: {path}")
  with open(path, "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    if reader.fieldnames and fieldnames is None:
      fieldnames = reader.fieldnames
    for row in reader:
      key = (row.get("root_key") or "").strip()
      if not key or key in seen:
        continue
      seen.add(key)
      rows.append(row)

if not fieldnames:
  raise SystemExit("No CSV headers found in quarter reports.")

with open(out, "w", encoding="utf-8-sig", newline="") as f:
  writer = csv.DictWriter(f, fieldnames=fieldnames)
  writer.writeheader()
  writer.writerows(rows)
PY

echo "Annual report generated: $MERGED_CSV"

INTERVIEW_SCRIPT="${INTERVIEW_SCRIPT:-1}"
if [[ "$INTERVIEW_SCRIPT" == "1" ]]; then
  INTERVIEW_SCRIPT_TOOL="${HOME}/.codex/skills/private-jira-interview-script/scripts/generate-interview-script.py"
  python3 "$INTERVIEW_SCRIPT_TOOL" \
    --year "$YEAR" \
    --csv "$MERGED_CSV" \
    --out "${OUTPUT_DIR}/interview-script-${YEAR}.md"
fi
