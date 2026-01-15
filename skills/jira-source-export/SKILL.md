---
name: jira-source-export
description: Export Jira source issues for a time range by assignee and/or comment author, then output structured JSON with parent and related links. Use when a task needs Jira source data (instead of manual Jira.html exports) filtered by year/month or date range.
---

# Jira Source Export

## Workflow

### 1) Export source issues (required)
Run the script to fetch issues assigned to you and/or commented by you within a date range.

```bash
JIRA_BASE_URL="https://your-jira.atlassian.net" \
JIRA_EMAIL="you@example.com" \
JIRA_API_TOKEN="your_token" \
YEAR=2025 MONTH=1 \
./scripts/jira-source-export.sh jira-source-2025-01.json
```

For faster runs (parallel comment scan), use:

```bash
JIRA_BASE_URL="https://your-jira.atlassian.net" \
JIRA_EMAIL="you@example.com" \
JIRA_API_TOKEN="your_token" \
YEAR=2025 MONTH=1 \
CONCURRENCY=8 \
./scripts/jira-source-export-fast.py jira-source-2025-01.json
```

Use overrides when needed:
- `START_DATE=YYYY/MM/DD` and `END_DATE=YYYY/MM/DD`
- `MATCH_MODE=any|comment|assignee|both` (default `any`)
- `PROJECTS=KEY1,KEY2`
- `JQL_EXTRA=...`
 - `ASSIGNEE_JQL=...` (override assignee query)
 - `MAX_PAGES=...` / `MAX_ISSUES=...` (limit for quick runs)

### 2) Validate output
Confirm the JSON is valid and contains expected keys.

```bash
jq '.[0] | keys' jira-source-2025-01.json
```

### 3) Use as source data
Use the output JSON as the canonical source instead of Jira.html. Fields included:
- `issue_key`, `summary`, `project_key`, `issuetype`
- `parent_key`
- `issuelinks[]` with `type`, `inward`, `outward`, `issue_key`

### 4) Traverse locally (no API calls)
Use the local JSON to traverse relations (parent/relates) without additional API calls.

```bash
./scripts/jira-traverse-local.py jira-source-2025-01-01_01-30.json MGTT-17997 --max-depth 5 --only-itpt
```

Batch + CSV output:

```bash
./scripts/jira-traverse-local.py jira-source-sample.json MGTT-17744 \
  --batch-file roots.txt \
  --only-itpt \
  --csv-output itpt-links.csv
```

Emit missing keys (for MCP/REST补完):

```bash
./scripts/jira-traverse-local.py jira-source-sample.json MGTT-17744 \
  --only-itpt \
  --missing-output missing-keys.txt
```

## Script

- `scripts/jira-source-export.sh`: REST-based export for assignee/commented issues with date range filters.
- `scripts/jira-source-export-fast.py`: Parallelized exporter for faster comment scans.
- `scripts/jira-traverse-local.py`: Local graph traversal for parent/related links.
- `scripts/jira-source-export-activity.py`: REST export using changelog activity filtering (slower, but supports "my activity").
