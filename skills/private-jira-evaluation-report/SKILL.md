---
name: private-jira-evaluation-report
description: Generate a yearly evaluation report (not interview) from merged Jira CSVs with ITPT focus and MGTT summaries. Use after annual report merge.
---

# Private Jira Evaluation Report

## Overview
Create an evaluation-style report from merged quarter CSVs, focusing on ITPT outcomes and summarizing MGTT contributions.

## Inputs
- `YEAR` (required)
- `BASE_DIR` (required) directory containing `Q1..Q4` and merged `itpt-links.csv`
- `OUTPUT_PATH` (optional, default: `BASE_DIR/evaluation-YYYY.md`)

## Run
```bash
YEAR=2025 \
BASE_DIR=~/Downloads/itpt-2025 \
OUTPUT_PATH=~/Downloads/itpt-2025/evaluation-2025.md \
~/.codex/skills/private-jira-evaluation-report/scripts/generate-evaluation-report.py
```
