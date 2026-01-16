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
  CSV_SEED          Jira CSV export path (assignee=currentUser) for faster seeding
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
QUARTERS="${QUARTERS:-}"
ROLE_MODE="${ROLE_MODE:-dev}"
OUTPUT_TIMESTAMP="${OUTPUT_TIMESTAMP:-1}"

EXPORT_START="${EXPORT_START:-}"
EXPORT_END="${EXPORT_END:-}"
COMMENT_AUTHOR_DISPLAY="${COMMENT_AUTHOR_DISPLAY:-}"
CSV_SEED="${CSV_SEED:-}"
CSV_SEED_AUTO="${CSV_SEED_AUTO:-1}"

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
export PROJECTS ENV_FILE EXPORT_START EXPORT_END MATCH_MODE PARALLEL_RANGES ROLE_MODE
export CONCURRENCY MAX_RESULTS MAX_PAGES HTTP_TIMEOUT COMMENT_AUTHOR_DISPLAY
export CSV_SEED CSV_SEED_AUTO
export WEEKLY_SPLIT=1

if [[ -z "$CSV_SEED" && "$CSV_SEED_AUTO" == "1" ]]; then
  CSV_SEED="${OUTPUT_DIR}/jira-seed.csv"
  if [[ ! -s "$CSV_SEED" ]]; then
    python3 "${HOME}/.codex/skills/jira-itpt-report/scripts/jira-export-csv-seed.py" \
      --out "$CSV_SEED" \
      --env-file "$ENV_FILE" \
      --projects "$PROJECTS"
  fi
  CSV_SEED_AUTO="0"
  export CSV_SEED CSV_SEED_AUTO
fi

quarters() {
  cat <<EOF
Q1 1 ${YEAR}/01/01 ${YEAR}/04/01
Q2 4 ${YEAR}/04/01 ${YEAR}/07/01
Q3 7 ${YEAR}/07/01 ${YEAR}/10/01
Q4 10 ${YEAR}/10/01 $((YEAR + 1))/01/01
EOF
}

quarters_filtered() {
  quarters | awk -v sel="$QUARTERS" '
    BEGIN {
      if (sel == "") { all = 1 }
      n = split(sel, arr, ",")
      for (i = 1; i <= n; i++) keep[arr[i]] = 1
    }
    {
      if (all || keep[$1]) print
    }
  '
}

QUARTER_LINES=()
while IFS= read -r line; do
  QUARTER_LINES+=("$line")
done < <(quarters_filtered)
if [[ "${#QUARTER_LINES[@]}" -eq 0 ]]; then
  echo "No quarters selected. QUARTERS=$QUARTERS" >&2
  exit 1
fi

printf "%s\n" "${QUARTER_LINES[@]}" | xargs -n 4 -P "$QUARTER_PARALLEL" bash -c '
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
    local export_start="${EXPORT_START:-}"
    local export_end="${EXPORT_END:-}"
    if [[ -z "$export_start" || -z "$export_end" ]]; then
      export_start="$ms"
      export_end="$me"
    fi
    YEAR="$YEAR" MONTH="$m" \
    PROJECTS="$PROJECTS" ENV_FILE="$ENV_FILE" \
    OUTPUT_DIR="$quarter_dir" \
    MERGE_START="$ms" MERGE_END="$me" \
    EXPORT_START="$export_start" EXPORT_END="$export_end" \
    CSV_SEED="$CSV_SEED" CSV_SEED_AUTO="$CSV_SEED_AUTO" \
    "$BASE_REPORT"
  }
  run_quarter "$quarter" "$month" "$merge_start" "$merge_end"
' _

MERGED_CSV="${OUTPUT_DIR}/itpt-links.csv"
CSV_ARGS=()
for line in "${QUARTER_LINES[@]}"; do
  q="$(echo "$line" | awk "{print \$1}")"
  CSV_ARGS+=("${OUTPUT_DIR}/${q}/itpt-links.csv")
done

python3 - "$MERGED_CSV" "${CSV_ARGS[@]}" <<'PY'
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
if [[ "$OUTPUT_TIMESTAMP" == "1" && -s "$MERGED_CSV" ]]; then
  TS="$(date +"%Y%m%d-%H%M%S")"
  cp "$MERGED_CSV" "${OUTPUT_DIR}/itpt-links-${TS}.csv"
fi

EVALUATION_REPORT="${EVALUATION_REPORT:-1}"
if [[ "$EVALUATION_REPORT" == "1" ]]; then
  EVAL_TOOL="${HOME}/.codex/skills/private-jira-evaluation-report/scripts/generate-evaluation-report.py"
  EVAL_OUT="${OUTPUT_DIR}/evaluation-${YEAR}.md"
  python3 "$EVAL_TOOL" \
    --year "$YEAR" \
    --base-dir "$OUTPUT_DIR" \
    --out "$EVAL_OUT"
  if [[ "$OUTPUT_TIMESTAMP" == "1" && -s "$EVAL_OUT" ]]; then
    TS="$(date +"%Y%m%d-%H%M%S")"
    cp "$EVAL_OUT" "${OUTPUT_DIR}/evaluation-${YEAR}-${TS}.md"
  fi
fi
