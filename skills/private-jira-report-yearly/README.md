# private-jira-report-yearly 한글 가이드

## 목적
연간 개인 리포트를 분기 병렬(Q1~Q4)로 생성하고, 연간 CSV로 취합합니다.

## 주요 입력
- `YEAR` (필수)
- `PROJECTS` (기본 `MGTT,ITPT`)
- `EXPORT_START`, `EXPORT_END`
- `PARALLEL_RANGES` (주차 병렬), `QUARTER_PARALLEL` (분기 병렬)
- `ROLE_MODE` (`dev`=PR merge 기준, `plan_qa`=assignee 기준)
- `CSV_SEED` (Jira UI CSV export 경로)
- `CSV_SEED_AUTO` (CSV 자동 export, 기본 1; 연간 실행 시 1회 생성/재사용)

## 실행
```bash
YEAR=2025 PROJECTS=MGTT,ITPT \
EXPORT_START=2024/06/01 EXPORT_END=2026/01/01 \
MATCH_MODE=assignee PARALLEL_RANGES=4 QUARTER_PARALLEL=4 \
ENV_FILE=~/.codex/jira_env \
~/.codex/skills/private-jira-report-yearly/scripts/private-jira-report-yearly.sh
```

assignee 이력까지 포함한 CSV 시드:
```bash
YEAR=2025 PROJECTS=MGTT,ITPT \
EXPORT_START=2024/06/01 EXPORT_END=2026/01/01 \
ENV_FILE=~/.codex/jira_env \
CSV_SEED_JQL='project in (MGTT, ITPT) AND assignee WAS currentUser()' \
~/.codex/skills/private-jira-report-yearly/scripts/private-jira-report-yearly.sh
```

CSV seed 사용:
```bash
YEAR=2025 PROJECTS=MGTT,ITPT \
EXPORT_START=2024/06/01 EXPORT_END=2026/01/01 \
MATCH_MODE=assignee PARALLEL_RANGES=4 QUARTER_PARALLEL=4 \
ENV_FILE=~/.codex/jira_env \
CSV_SEED=/path/to/jira.csv \
~/.codex/skills/private-jira-report-yearly/scripts/private-jira-report-yearly.sh
```

## 결과
- 분기 CSV: `Q1..Q4/itpt-links.csv`
- 연간 CSV: `itpt-links.csv`
- 평가 리포트: `evaluation-YYYY.md`
