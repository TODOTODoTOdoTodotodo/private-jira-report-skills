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
  --include-master-merge
  --env-file "${ENV_FILE:-$HOME/.codex/jira_env}"
)

if [[ -n "$MERGE_START" ]]; then
  args+=(--merge-start "$MERGE_START")
fi
if [[ -n "$MERGE_END" ]]; then
  args+=(--merge-end "$MERGE_END")
fi

python3 "$TRAVERSE_SCRIPT" "${args[@]}"

echo "Final report: $CSV_OUT"
