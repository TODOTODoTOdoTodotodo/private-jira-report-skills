# Private Jira Report 스킬 가이드 (v1)

## 목적
개인이 최소 입력(YEAR, MONTH, PROJECTS)만으로 MGTT/ITPT 월간 리포트를 생성할 수 있도록 표준 실행 흐름을 제공합니다.

## 대상
- Jira 월간 리포트를 반복 생성해야 하는 개인
- Jira/MCP 환경을 처음 세팅하는 개인

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
1) `jira_env`에서 Jira 인증값 로드
2) `~/.atlassian-mcp.json` 자동 생성
3) `atlassian-local` MCP 등록
4) 월 단위 Jira 데이터 export + 로컬 traverse
5) 누락 키가 있으면 MCP 보충 후 최종 CSV 생성

## 실행 방법
### 기본 실행 (권장)
```bash
YEAR=2026 MONTH=1 PROJECTS=MGTT,ITPT \
ENV_FILE=~/.codex/jira_env \
~/.codex/skills/private-jira-report/scripts/private-jira-report.sh
```

### 출력 위치
- 기본: `~/Downloads/itpt-YYYY-MM`

생성 파일:
- `jira-source.json`
- `roots.txt`
- `missing-keys.txt`
- `itpt-links.csv`

## 누락 키 처리(필수 케이스)
`missing-keys.txt`가 있으면 아래 순서로 마무리합니다.

1) MCP로 누락 키 보충하여 `jira-source-supplement.json` 생성
2) finalize 실행

```bash
OUTPUT_DIR=/path/to/output \
~/.codex/skills/jira-itpt-report-finalize/scripts/jira-itpt-finalize.sh
```

## 동작 흐름 (요약)
- 입력: YEAR, MONTH, PROJECTS
- ENV_FILE 확인 및 로드
- MCP 설정 파일 생성
- MCP 등록
- Jira REST export + traverse
- missing-keys 존재 시 MCP 보충 → finalize

## 자주 발생하는 문제
1) `ENV_FILE` 없음
- 메시지: `Missing ENV_FILE`
- 해결: `~/.codex/jira_env_template`를 복사해 `~/.codex/jira_env` 생성

2) MCP 초기화 실패
- 메시지 예: `Missing required configuration: domain, email, apiToken`
- 해결: `jira_env` 값 확인 후 재실행

3) 누락 키 지속 발생
- 원인: MCP 보충 미실행
- 해결: `jira-itpt-report-finalize.sh` 실행

## 관련 스킬/스크립트
- 스킬: `private-jira-report`
- MCP 등록: `atlassian-mcp-connect`
- 리포트 생성: `jira-itpt-report`
- 마무리: `jira-itpt-report-finalize`

---

피드백 주시면 수정 반영하겠습니다.
