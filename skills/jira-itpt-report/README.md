# jira-itpt-report 한글 가이드

## 목적
Jira 소스를 export하고 ITPT 관계를 로컬에서 탐색해 `itpt-links.csv`를 생성합니다.

## 주요 입력
- `START_DATE`, `END_DATE` 또는 `YEAR`, `MONTH`
- `PROJECTS` (기본 `MGTT,ITPT`)
- `ENV_FILE` (기본 `~/.codex/jira_env`)
- `ROLE_MODE` (`dev`=PR merge 기준, `plan_qa`=assignee 기준)
- `CSV_SEED` (Jira UI CSV export 경로, 기본 assignee=currentUser)
- `CSV_SEED_AUTO` (CSV_SEED 비어있으면 자동 export, 기본 1; 미지정 시 자동)
- `CSV_SEED_JQL` (CSV export용 JQL override)

## 실행
```bash
ENV_FILE=~/.codex/jira_env \
START_DATE=2025/01/01 END_DATE=2025/01/31 \
OUTPUT_DIR=~/Downloads/itpt-2025-01 \
~/.codex/skills/jira-itpt-report/scripts/jira-itpt-report.sh
```

CSV seed 사용 (PR merge 기준 빠른 필터):
```bash
ENV_FILE=~/.codex/jira_env \
CSV_SEED=/path/to/jira.csv \
START_DATE=2025/01/01 END_DATE=2025/01/31 \
OUTPUT_DIR=~/Downloads/itpt-2025-01 \
~/.codex/skills/jira-itpt-report/scripts/jira-itpt-report.sh
```

CSV seed 자동 생성(assignee 이력 포함 예시):
```bash
ENV_FILE=~/.codex/jira_env \
CSV_SEED_AUTO=1 \
CSV_SEED_JQL='project in (MGTT, ITPT) AND assignee WAS currentUser()' \
START_DATE=2025/01/01 END_DATE=2025/01/31 \
OUTPUT_DIR=~/Downloads/itpt-2025-01 \
~/.codex/skills/jira-itpt-report/scripts/jira-itpt-report.sh
```

## 후속 처리
`missing-keys.txt`가 있으면 `jira-itpt-report-finalize`로 보충 후 최종 CSV를 생성합니다.

## 결과
- `jira-source.json`, `roots.txt`, `missing-keys.txt`
- `itpt-links.csv` (부분 결과)
