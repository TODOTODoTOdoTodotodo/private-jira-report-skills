# private-jira-report 한글 가이드

## 목적
월 단위 개인 Jira 리포트를 생성합니다.

## 주요 입력
- `YEAR`, `MONTH`
- `PROJECTS` (기본 `MGTT,ITPT`)
- `ENV_FILE` (기본 `~/.codex/jira_env`)

## 실행
```bash
YEAR=2025 MONTH=1 PROJECTS=MGTT,ITPT \
ENV_FILE=~/.codex/jira_env \
~/.codex/skills/private-jira-report/scripts/private-jira-report.sh
```

## 결과
- 기본 출력: `~/Downloads/itpt-YYYY-MM`
- `itpt-links.csv` 생성 (필요 시 finalize 단계 포함)
