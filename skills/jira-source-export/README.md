# jira-source-export 한글 가이드

## 목적
Jira 이슈를 기간/프로젝트 기준으로 export하여 로컬 JSON 소스를 생성합니다.

## 주요 입력
- `YEAR`, `MONTH` 또는 `START_DATE`, `END_DATE`
- `PROJECTS` (예: `MGTT,ITPT`)
- `MATCH_MODE` (`assignee`, `comment`, `both`, `any`)
- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`

## 실행 예시
```bash
YEAR=2025 MONTH=1 PROJECTS=MGTT,ITPT \
JIRA_BASE_URL=... JIRA_EMAIL=... JIRA_API_TOKEN=... \
./scripts/jira-source-export.sh jira-source.json
```

빠른 병렬 버전:
```bash
YEAR=2025 MONTH=1 PROJECTS=MGTT,ITPT CONCURRENCY=8 \
JIRA_BASE_URL=... JIRA_EMAIL=... JIRA_API_TOKEN=... \
./scripts/jira-source-export-fast.py jira-source.json
```

## 결과
- 로컬 JSON(`jira-source.json`) 생성
- 이후 `jira-traverse-local.py`로 관계 탐색 가능
