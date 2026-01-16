# private-jira-report 한글 가이드

## 목적
월 단위 개인 Jira 리포트를 생성합니다.

## 주요 입력
- `YEAR`, `MONTH`
- `PROJECTS` (기본 `MGTT,ITPT`)
- `ENV_FILE` (기본 `~/.codex/jira_env`)
- `CSV_SEED` (Jira UI CSV export 경로)
- `CSV_SEED_AUTO` (CSV 자동 export, 기본 1; 미지정 시 자동)

## MCP 자동 설정
- `private-jira-report` 실행 시 `~/.atlassian-mcp.json`을 생성하고 `atlassian-local` MCP를 등록합니다.

## 실행
```bash
YEAR=2025 MONTH=1 PROJECTS=MGTT,ITPT \
ENV_FILE=~/.codex/jira_env \
~/.codex/skills/private-jira-report/scripts/private-jira-report.sh
```

CSV seed 사용:
```bash
YEAR=2025 MONTH=1 PROJECTS=MGTT,ITPT \
ENV_FILE=~/.codex/jira_env \
CSV_SEED=/path/to/jira.csv \
~/.codex/skills/private-jira-report/scripts/private-jira-report.sh
```

## 결과
- 기본 출력: `~/Downloads/itpt-YYYY-MM`
- `itpt-links.csv` 생성 (필요 시 finalize 단계 포함)
