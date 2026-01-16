---
name: private-jira-strengths-insights
description: Analyze Jira source JSON (descriptions) to draft strengths/weaknesses and impact insights for evaluation reports. Use before generating evaluation report so strengths/weaknesses can reflect real work context.
---

# Private Jira Strengths Insights

## Overview
Generate strengths/weaknesses/impact insights by reading `jira-source.json` (description 포함) and optionally calling an LLM. Output is a JSON file consumed by the evaluation report generator.

## Inputs
- `BASE_DIR` (required): directory containing `jira-source.json` or `Q1..Q4/jira-source.json`
- `OUTPUT_PATH` (optional, default: `BASE_DIR/strengths-insights.json`)
- `MAX_ISSUES` (optional, default: 200) limit issues analyzed
- `LLM_API_URL` (optional): OpenAI-compatible endpoint
- `LLM_API_KEY` (optional): API token for LLM
- `LLM_MODEL` (optional, default: `gpt-4o-mini`)
- `LLM_PROMPT_ONLY` (optional, default: 0) if 1, only emits prompt and uses heuristic fallback

## Run
```bash
BASE_DIR=~/Downloads/itpt-2025 \
OUTPUT_PATH=~/Downloads/itpt-2025/strengths-insights.json \
~/.codex/skills/private-jira-strengths-insights/scripts/generate-strengths-insights.py
```

## Output
JSON with:
- `summary` (string)
- `themes` (list)
- `strengths` (list)
- `weaknesses` (list)
- `impact` (list)
