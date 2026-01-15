---
name: private-jira-report-yearly
description: Run a yearly private Jira report by quarter in parallel (weekly split inside each quarter) and merge all quarters into one annual report. Trigger on natural-language requests like "2025년 리포트 만들어줘", "2025년 개인 리포트 만들어줘", "2025년 MGTT/ITPT 리포트", "작년 전체 리포트".
---

# Private Jira Report (Yearly Parallel)

## Overview
Runs 4 quarter jobs in parallel using the existing `private-jira-report` workflow, keeps weekly split inside each quarter, and merges quarter CSVs into one annual CSV.

## Inputs
- `YEAR` (required)
- `PROJECTS` (optional, default `MGTT,ITPT`)
- `ENV_FILE` (optional, default `~/.codex/jira_env`)
- `EXPORT_START` / `EXPORT_END` (optional, default `YEAR/01/01` to `YEAR+1/01/01`)
- `MATCH_MODE` (optional, default `assignee`)
- `QUARTER_PARALLEL` (optional, default `4`)
- `PARALLEL_RANGES` (optional, default `4`) for weekly export parallelism
- `QUARTERS` (optional, default all) e.g. `Q1` or `Q1,Q2`
- `ROLE_MODE` (optional, default `dev`) `dev`=PR merge 기준, `plan_qa`=assignee 기준
- `DEVSTATUS_CACHE` (optional, default `OUTPUT_DIR/devstatus-cache.json`)
- `CONCURRENCY`, `MAX_RESULTS`, `MAX_PAGES`, `HTTP_TIMEOUT` (optional, passthrough)
- `COMMENT_AUTHOR_DISPLAY` (optional, passthrough)

## Run
```bash
YEAR=2025 PROJECTS=MGTT,ITPT \
EXPORT_START=2024/06/01 EXPORT_END=2026/01/01 \
MATCH_MODE=assignee PARALLEL_RANGES=4 QUARTER_PARALLEL=4 \
ENV_FILE=~/.codex/jira_env \
~/.codex/skills/private-jira-report-yearly/scripts/private-jira-report-yearly.sh
```

## Natural-language trigger examples
- "2025년 리포트 만들어줘"
- "2025년 개인 리포트 만들어줘. 프로젝트 MGTT,ITPT"
- "2025년 전체 리포트"
- "작년 리포트 만들어줘"

## Output
- Quarter outputs: `~/Downloads/itpt-YYYY/Q1..Q4/itpt-links.csv`
- Annual merged output: `~/Downloads/itpt-YYYY/itpt-links.csv`
