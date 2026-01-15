---
name: private-jira-interview-script
description: Generate a yearly interview-style self-review script from the merged private Jira report CSV. Use after an annual report is completed.
---

# Private Jira Interview Script

## Overview
Create an interview-style self-review (Q&A format) based on the annual merged CSV.

## Inputs
- `YEAR` (required)
- `CSV_PATH` (required) merged `itpt-links.csv`
- `OUTPUT_PATH` (optional, default: same dir as CSV)

## Run
```bash
YEAR=2025 \
CSV_PATH=~/Downloads/itpt-2025/itpt-links.csv \
OUTPUT_PATH=~/Downloads/itpt-2025/interview-script-2025.md \
~/.codex/skills/private-jira-interview-script/scripts/generate-interview-script.py
```
