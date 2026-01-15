---
name: atlassian-mcp-connect
description: Register the local Atlassian MCP server (server-atlassian) via Codex CLI. Use when the user says “jira 연결해줘”, “jira mcp 연결해줘”, “jira 붙여줘”, “jira 로그인해줘”, or “atlassian 연결해줘”, or when MCP access is missing and needs re-registration.
---

# Atlassian MCP Connect (Local)

## Getting Started

### Local MCP server (recommended)
Ensure these env vars are present (from env or `~/.codex/jira_env`):

- `ATLASSIAN_DOMAIN` (e.g., `your-domain.atlassian.net`)
- `ATLASSIAN_EMAIL` (email)
- `ATLASSIAN_API_TOKEN` (ATATT...)

Register the local MCP server (writes `~/.atlassian-mcp.json` automatically):

```bash
codex mcp remove atlassian-local >/dev/null 2>&1 || true
codex mcp add atlassian-local -- npx -y @xuandev/atlassian-mcp
```

### Verify

```bash
codex mcp list
```

## Workflow

### 1) Gather inputs
Ask for missing inputs:
- `MCP_SERVER_NAME` (default `atlassian-local`)
- Atlassian env vars: `ATLASSIAN_DOMAIN`, `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`

### 2) Connect (re-register on failure)
Register the local server using `npx` (writes `~/.atlassian-mcp.json` automatically):

```bash
codex mcp remove atlassian-local >/dev/null 2>&1 || true
codex mcp add atlassian-local -- npx -y @xuandev/atlassian-mcp
```

### 3) Verify
Check the server shows in `codex mcp list`.

## Defaults
- Jira base URL: `https://jira-hanatour.atlassian.net`
- Name: `atlassian-local`

## Script
- `scripts/atlassian_mcp_connect.sh`: Local MCP connector (loads `ENV_FILE` if provided).
