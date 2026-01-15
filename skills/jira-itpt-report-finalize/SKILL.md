---
name: jira-itpt-report-finalize
description: Finalize Jira ITPT report after partial run. Use when missing-keys.txt exists and you need MCP 보충, merge, and final CSV output.
---

# Jira ITPT Report Finalize

## Workflow

### 1) MCP 보충 (required)
Read `missing-keys.txt`, then fetch each key via MCP:
- `getJiraIssue` with fields: `summary, issuetype, project, parent, issuelinks`.
- Build `jira-source-supplement.json` with the same schema as the base source JSON.

### 2) Merge + final CSV
Run:

```bash
OUTPUT_DIR=/path/to/output \
~/.codex/skills/jira-itpt-report-finalize/scripts/jira-itpt-finalize.sh
```

### 3) Verify output
- `jira-source-merged.json`
- `itpt-links.csv`

## Script
- `scripts/jira-itpt-finalize.sh`: merges base + supplement and produces final ITPT CSV.
