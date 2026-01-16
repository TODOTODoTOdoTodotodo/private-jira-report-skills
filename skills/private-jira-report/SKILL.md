---
name: private-jira-report
description: Generate monthly private Jira MGTT/ITPT reports with minimal inputs (year, month, projects). Use when users ask for a personal report like "2026년 1월 개인 리포트" or "2026년 리포트" and want the full export + local traverse flow.
---

# Private Jira Report

## Overview
Run a monthly Jira export + traverse with the smallest possible inputs (YEAR, MONTH, PROJECTS) and standard env file.

## Inputs
- `YEAR` (required)
- `MONTH` (required)
- `PROJECTS` (optional, default `MGTT,ITPT`)
- `ENV_FILE` (optional, default `~/.codex/jira_env`)
- `CSV_SEED` (optional, Jira UI CSV export 경로)
- `CSV_SEED_AUTO` (optional, CSV 자동 export, 기본 1)

## Workflow
1) Ensure local MCP is registered:
   - Ensure `~/.codex/jira_env` exists (see `~/.codex/jira_env_template`).
   - The wrapper writes `~/.atlassian-mcp.json` from `JIRA_*` values.
   - `private-jira-report` runs `atlassian-mcp-connect` automatically.
2) Run the wrapper script:

```bash
YEAR=2026 MONTH=1 PROJECTS=MGTT,ITPT \
ENV_FILE=~/.codex/jira_env \
~/.codex/skills/private-jira-report/scripts/private-jira-report.sh
```

CSV seed 사용:

```bash
YEAR=2026 MONTH=1 PROJECTS=MGTT,ITPT \
ENV_FILE=~/.codex/jira_env \
CSV_SEED=/path/to/jira.csv \
~/.codex/skills/private-jira-report/scripts/private-jira-report.sh
```


3) If `missing-keys.txt` exists:
   - Use MCP to supplement missing keys (see `jira-itpt-report-finalize` skill),
   - Then finalize with:

```bash
OUTPUT_DIR=/path/to/output \
~/.codex/skills/jira-itpt-report-finalize/scripts/jira-itpt-finalize.sh
```

## Notes
- Output defaults to `~/Downloads/itpt-YYYY-MM`.
- `ENV_FILE` must include `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_ACCOUNT_ID`.
