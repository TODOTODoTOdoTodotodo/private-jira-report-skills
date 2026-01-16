# private-jira-interview-script 한글 가이드

## 목적
연간 CSV를 기반으로 인터뷰 형식(Q&A)의 자기소개 스크립트를 생성합니다.

## 입력
- `YEAR` (필수)
- `CSV_PATH` (필수, merged `itpt-links.csv`)
- `OUTPUT_PATH` (선택)

## 실행
```bash
YEAR=2025 \
CSV_PATH=~/Downloads/itpt-2025/itpt-links.csv \
OUTPUT_PATH=~/Downloads/itpt-2025/interview-script-2025.md \
~/.codex/skills/private-jira-interview-script/scripts/generate-interview-script.py
```

## 결과
- `interview-script-YYYY.md`
