---
name: jira-itpt-report
description: End-to-end Jira ITPT report flow from natural-language “jira 연결해줘” to exporting MGTT/ITPT issues, traversing relationships, and producing the final ITPT CSV report. Use when a user wants a single workflow for date-range Jira extraction and reporting.
---

# Jira ITPT Report

## Getting Started

### Quick start (recommended)
1) Ensure Jira env file exists (token mode default):
   - `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_ACCOUNT_ID`
   - Example: `~/.codex/jira_env`
2) Decide date range: `START_DATE`, `END_DATE` (YYYY/MM/DD)
3) Run the partial flow, then chain finalize if missing keys remain.

### Example prompt (natural language)
```
jira 연결해줘. 인증 token, 2026년 1월, ENV_FILE=~/.codex/jira_env, 프로젝트 MGTT,ITPT로 리포트까지 진행해줘.
```

### Inputs to request
- Date range: `START_DATE`, `END_DATE`
- Or month-based: `YEAR`, `MONTH` (auto weekly split)
- Credentials env file: `ENV_FILE` (e.g. `~/.codex/jira_env`)
- MCP server: `atlassian-local` (local MCP server, required for supplements)
- Atlassian env vars: `ATLASSIAN_DOMAIN`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN` (can be mapped from `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`)
- Role mode: `ROLE_MODE=dev|plan_qa` (dev=PR merge 기준, plan_qa=assignee 기준)
- Dev-status cache: `DEVSTATUS_CACHE` (기본 `OUTPUT_DIR/devstatus-cache.json`)
- Output timestamp: `OUTPUT_TIMESTAMP` (기본 1, 결과 CSV에 타임스탬프 사본 생성)
- CSV seed: `CSV_SEED` (JQL export CSV, 기본 assignee=currentUser)
- CSV seed auto: `CSV_SEED_AUTO` (CSV_SEED 비어있으면 Jira CSV 자동 생성, 기본 1)
- CSV seed JQL: `CSV_SEED_JQL` (Jira CSV export용 JQL override)
- Development field: `DEVELOPMENT_FIELD_ID` (Jira 개발 필드 ID, 미지정 시 name 검색)

### Run end-to-end export (partial)
This generates the source JSON, roots list, missing keys, and a partial CSV.

```bash
ENV_FILE=~/.codex/jira_env \
START_DATE=2025/01/01 END_DATE=2025/01/31 \
OUTPUT_DIR=/path/to/output \
~/.codex/skills/jira-itpt-report/scripts/jira-itpt-report.sh
```

Month-based (auto weekly chunks saved to `week-YYYYMMDD-YYYYMMDD/`):

```bash
ENV_FILE=~/.codex/jira_env \
YEAR=2026 MONTH=1 \
OUTPUT_DIR=/path/to/output \
~/.codex/skills/jira-itpt-report/scripts/jira-itpt-report.sh
```

CSV seed mode (Jira UI CSV export 사용, PR merge 기준 빠른 분기 필터):

```bash
ENV_FILE=~/.codex/jira_env \
CSV_SEED=/path/to/jira.csv \
START_DATE=2025/01/01 END_DATE=2025/01/31 \
OUTPUT_DIR=/path/to/output \
~/.codex/skills/jira-itpt-report/scripts/jira-itpt-report.sh
```

CSV seed 자동 생성(assignee 이력 포함 예시):

```bash
ENV_FILE=~/.codex/jira_env \
CSV_SEED_AUTO=1 \
CSV_SEED_JQL='project in (MGTT, ITPT) AND assignee WAS currentUser()' \
START_DATE=2025/01/01 END_DATE=2025/01/31 \
OUTPUT_DIR=/path/to/output \
~/.codex/skills/jira-itpt-report/scripts/jira-itpt-report.sh
```


If `missing-keys.txt` is non-empty, use MCP to fetch those issues and merge:

```bash
~/.codex/skills/jira-source-export/scripts/jira-merge-source.py \
  /path/to/output/jira-source.json \
  /path/to/output/jira-source-supplement.json \
  /path/to/output/jira-source-merged.json
```

Then re-run traversal on the merged JSON:

```bash
~/.codex/skills/jira-source-export/scripts/jira-traverse-local.py \
  /path/to/output/jira-source-merged.json MGTT-ROOT \
  --batch-file /path/to/output/roots.txt \
  --only-itpt \
  --csv-output /path/to/output/itpt-links.csv
```

## Workflow

### 1) Connect Jira MCP
Use `atlassian-mcp-connect` (local MCP server) and ensure `ATLASSIAN_DOMAIN`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN` are present (can be mapped from `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`).

### 2) Export source issues
Use the `jira-source-export-fast.py` script with `PROJECTS=MGTT,ITPT` and `MATCH_MODE=any`.
CSV seed를 사용할 경우 `CSV_SEED`가 `Jira CSV (assignee=currentUser)`를 기반으로 `key in (...)` JQL을 생성해 호출 수를 줄입니다. dev 모드에서는 `사용자정의 필드 (development)`의 `lastUpdated`를 PR merge 기준으로 사용합니다.

### 3) Traverse locally
Use `jira-traverse-local.py` to produce a partial CSV and a missing key list.

### 4) MCP补完
Chain to the `jira-itpt-report-finalize` skill to fetch missing keys, merge, and produce the final CSV.

### 5) Merge + final CSV
Merge base + supplement JSON, then re-run local traverse to produce final CSV.

## Scripts
- `scripts/jira-itpt-report.sh`: Partial end-to-end flow (export + traverse + missing keys).
- `scripts/jira-build-roots.py`: Build MGTT root key list from source JSON.
- `scripts/jira-seed-from-csv.py`: Jira CSV에서 분기 키/PR merge 기준을 추출.
- `scripts/jira-export-csv-seed.py`: Jira REST로 CSV seed 자동 export.
