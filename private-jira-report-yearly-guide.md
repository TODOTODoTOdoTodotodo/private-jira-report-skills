# Private Jira Report Yearly 스킬 가이드 (v1)

## 목적
연간 개인 리포트를 분기 단위 병렬 처리(Q1~Q4)로 생성하고, 각 분기 내부는 주차 병렬 export를 유지하면서 최종 연간 CSV로 취합하는 표준 실행 흐름을 제공합니다.

## 대상
- 1년치 Jira 리포트를 빠르게 생성해야 하는 개인
- 분기별/연간 결과를 한 번에 확인하고 싶은 개인

## 준비물
1) `~/.codex/jira_env` 생성 (템플릿 기반)
2) 로컬 MCP 실행을 위한 Node.js 및 npx 사용 가능 환경

### jira_env 템플릿
템플릿 위치:
- `~/.codex/jira_env_template`

예시:
```
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=ATATT...
JIRA_ACCOUNT_ID=your-account-id
```

## 핵심 동작 요약
1) 연간 범위를 Q1~Q4로 분할해 병렬 실행
2) 분기 내부는 주 단위 export 병렬 처리 유지
3) master 브랜치 PR merge 기간으로 필터링
4) 분기 CSV를 연간 CSV로 병합(중복 root_key 제거)

## 실행 방법
### 기본 실행 (권장)
```bash
YEAR=2025 PROJECTS=MGTT,ITPT \
EXPORT_START=2024/06/01 EXPORT_END=2026/01/01 \
MATCH_MODE=assignee PARALLEL_RANGES=4 QUARTER_PARALLEL=4 \
ENV_FILE=~/.codex/jira_env \
~/.codex/skills/private-jira-report-yearly/scripts/private-jira-report-yearly.sh
```

### 파라미터 설명 (핵심)
- `YEAR`: 연간 기준 연도
- `PROJECTS`: 대상 프로젝트 (기본 MGTT,ITPT)
- `EXPORT_START/EXPORT_END`: Jira export 범위
- `MATCH_MODE=assignee`: assignee 기준 (currentUser)
- `PARALLEL_RANGES`: 주차 병렬 개수
- `QUARTER_PARALLEL`: 분기 병렬 개수

## 출력 위치
- 기본: `~/Downloads/itpt-YYYY`

생성 파일:
- 분기별: `Q1/itpt-links.csv`, `Q2/itpt-links.csv`, `Q3/itpt-links.csv`, `Q4/itpt-links.csv`
- 연간 취합: `itpt-links.csv`

## 누락 키 처리(필수 케이스)
분기 결과에 `missing-keys.txt`가 있으면 분기별로 마무리합니다.

```bash
OUTPUT_DIR=~/Downloads/itpt-YYYY/Q1 \
~/.codex/skills/jira-itpt-report-finalize/scripts/jira-itpt-finalize.sh
```

## 동작 흐름 (요약)
- 입력: YEAR, PROJECTS, EXPORT 범위, MATCH_MODE
- MCP 설정 및 등록
- 분기 병렬 실행 + 주차 병렬 export
- 분기별 itpt-links.csv 생성
- 연간 itpt-links.csv 취합

## 자주 발생하는 문제
1) `ENV_FILE` 없음
- 메시지: `Missing ENV_FILE`
- 해결: `~/.codex/jira_env_template`를 복사해 `~/.codex/jira_env` 생성

2) MCP 초기화 실패
- 메시지 예: `Missing required configuration: domain, email, apiToken`
- 해결: `jira_env` 값 확인 후 재실행

3) 분기별 `missing-keys.txt` 존재
- 원인: MCP 보충 미실행
- 해결: 분기별 `jira-itpt-report-finalize.sh` 실행

## 관련 스킬/스크립트
- 스킬: `private-jira-report-yearly`
- 기반 스킬: `private-jira-report`
- MCP 등록: `atlassian-mcp-connect`
- 리포트 생성: `jira-itpt-report`
- 마무리: `jira-itpt-report-finalize`

---

피드백 주시면 수정 반영하겠습니다.
