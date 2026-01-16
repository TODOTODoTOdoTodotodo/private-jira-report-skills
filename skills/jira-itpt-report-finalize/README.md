# jira-itpt-report-finalize 한글 가이드

## 목적
`missing-keys.txt`에 있는 이슈를 MCP로 보충하고 최종 `itpt-links.csv`를 생성합니다.

## 전제
- `OUTPUT_DIR`에 `jira-source.json`과 `missing-keys.txt` 존재
- MCP 서버(`atlassian-local`) 등록 완료

## 실행
```bash
OUTPUT_DIR=~/Downloads/itpt-2025-01 \
~/.codex/skills/jira-itpt-report-finalize/scripts/jira-itpt-finalize.sh
```

## 결과
- `jira-source-merged.json`
- `itpt-links.csv` (최종 결과)
