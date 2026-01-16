# private-jira-evaluation-report 한글 가이드

## 목적
연간 리포트 결과를 평가 형식으로 요약합니다(면접 아님).

## 입력
- `YEAR` (필수)
- `BASE_DIR` (Q1~Q4 및 `itpt-links.csv`가 있는 디렉터리)
- `OUTPUT_PATH` (선택)

## 실행
```bash
YEAR=2025 \
BASE_DIR=~/Downloads/itpt-2025 \
OUTPUT_PATH=~/Downloads/itpt-2025/evaluation-2025.md \
~/.codex/skills/private-jira-evaluation-report/scripts/generate-evaluation-report.py
```

## 결과
- `evaluation-YYYY.md`
