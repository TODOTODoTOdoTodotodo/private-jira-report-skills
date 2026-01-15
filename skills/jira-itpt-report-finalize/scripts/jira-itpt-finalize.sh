#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  OUTPUT_DIR=/path/to/output ./jira-itpt-finalize.sh

Required files in OUTPUT_DIR:
  jira-source.json
  jira-source-supplement.json
  roots.txt

Outputs:
  jira-source-merged.json
  itpt-links.csv
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

OUTPUT_DIR="${OUTPUT_DIR:-$PWD}"
EVALUATION_REPORT="${EVALUATION_REPORT:-0}"
YEAR="${YEAR:-}"
ROLE_MODE="${ROLE_MODE:-dev}"
DEVSTATUS_CACHE="${DEVSTATUS_CACHE:-$OUTPUT_DIR/devstatus-cache.json}"
BASE_JSON="${OUTPUT_DIR}/jira-source.json"
SUPP_JSON="${OUTPUT_DIR}/jira-source-supplement.json"
MERGED_JSON="${OUTPUT_DIR}/jira-source-merged.json"
ROOTS_TXT="${OUTPUT_DIR}/roots.txt"
CSV_OUT="${OUTPUT_DIR}/itpt-links.csv"

MERGE_SCRIPT="${HOME}/.codex/skills/jira-source-export/scripts/jira-merge-source.py"
TRAVERSE_SCRIPT="${HOME}/.codex/skills/jira-itpt-report/scripts/jira-traverse-root-itpt.py"

for f in "$BASE_JSON" "$SUPP_JSON" "$ROOTS_TXT"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing required file: $f" >&2
    exit 1
  fi
done

python3 "$MERGE_SCRIPT" "$BASE_JSON" "$SUPP_JSON" "$MERGED_JSON"
MERGE_START="${MERGE_START:-}"
MERGE_END="${MERGE_END:-}"

args=(
  "$MERGED_JSON"
  --batch-file "$ROOTS_TXT"
  --csv-output "$CSV_OUT"
  --env-file "${ENV_FILE:-$HOME/.codex/jira_env}"
  --role-mode "$ROLE_MODE"
)

if [[ "$ROLE_MODE" == "dev" ]]; then
  args+=(--include-master-merge --devstatus-cache "$DEVSTATUS_CACHE")
fi

if [[ "$ROLE_MODE" == "dev" && -n "$MERGE_START" ]]; then
  args+=(--merge-start "$MERGE_START")
fi
if [[ "$ROLE_MODE" == "dev" && -n "$MERGE_END" ]]; then
  args+=(--merge-end "$MERGE_END")
fi

python3 "$TRAVERSE_SCRIPT" "${args[@]}"

if [[ "$EVALUATION_REPORT" == "1" ]]; then
  EVAL_TOOL="${HOME}/.codex/skills/private-jira-evaluation-report/scripts/generate-evaluation-report.py"
  if [[ -f "$EVAL_TOOL" ]]; then
    if [[ -z "$YEAR" ]]; then
      base_name="$(basename "$OUTPUT_DIR")"
      if [[ "$base_name" =~ itpt-([0-9]{4}) ]]; then
        YEAR="${BASH_REMATCH[1]}"
      fi
    fi
    if [[ -n "$YEAR" ]]; then
      python3 "$EVAL_TOOL" \
        --year "$YEAR" \
        --base-dir "$OUTPUT_DIR" \
        --out "${OUTPUT_DIR}/evaluation-${YEAR}.md"
    else
      echo "Skip evaluation report: YEAR not set." >&2
    fi
  fi
fi

echo "Final report: $CSV_OUT"
