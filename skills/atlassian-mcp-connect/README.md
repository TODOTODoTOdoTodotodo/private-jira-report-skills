# atlassian-mcp-connect 한글 가이드

## 목적
로컬 Atlassian MCP 서버(`atlassian-local`)를 등록해 Jira API를 사용할 수 있게 합니다.

## 준비물
- `~/.codex/jira_env` 또는 환경변수에 아래 값 필요
  - `ATLASSIAN_DOMAIN`
  - `ATLASSIAN_EMAIL`
  - `ATLASSIAN_API_TOKEN`

## 실행
```bash
~/.codex/skills/atlassian-mcp-connect/scripts/atlassian_mcp_connect.sh
```

## 확인
```bash
codex mcp list
```

## 결과
- `~/.atlassian-mcp.json` 생성
- `atlassian-local` 등록 완료
