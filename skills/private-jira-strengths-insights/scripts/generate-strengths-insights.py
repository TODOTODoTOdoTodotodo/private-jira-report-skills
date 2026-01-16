#!/usr/bin/env python3
import argparse
import json
import os
import re
import urllib.request
from pathlib import Path


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_source_files(base_dir):
    base = Path(base_dir)
    files = []
    direct = base / "jira-source.json"
    if direct.exists():
        files.append(direct)
    for q in ("Q1", "Q2", "Q3", "Q4"):
        path = base / q / "jira-source.json"
        if path.exists():
            files.append(path)
    return files


def extract_issue_text(issue):
    summary = issue.get("summary") or ""
    desc = issue.get("description") or ""
    desc_summary = issue.get("description_summary") or ""
    if not desc and desc_summary:
        desc = desc_summary
    key = issue.get("issue_key") or ""
    project = issue.get("project_key") or ""
    return {
        "key": key,
        "project": project,
        "summary": summary.strip(),
        "description": desc.strip(),
    }


def normalize_text(text):
    return " ".join(text.split())


def theme_counts(items):
    themes = {
        "안정성/장애 대응": ["장애", "오류", "버그", "안정", "예외", "실패", "복구"],
        "성능/최적화": ["성능", "속도", "지연", "최적화", "튜닝"],
        "자동화/파이프라인": ["자동화", "배치", "파이프라인", "스크립트", "워크플로"],
        "배포/런칭": ["배포", "릴리스", "런칭", "출시"],
        "품질/검증": ["QA", "품질", "테스트", "검증"],
        "데이터/지표": ["데이터", "지표", "로그", "분석", "리포트"],
        "보안/권한": ["보안", "권한", "취약", "암호", "인증"],
        "기능/기획": ["기능", "요구사항", "기획", "화면", "정책"],
        "운영/모니터링": ["운영", "모니터링", "알림", "대응"],
    }
    counters = {k: 0 for k in themes}
    for item in items:
        text = normalize_text(
            " ".join([item.get("summary", ""), item.get("description", "")])
        )
        for label, terms in themes.items():
            if any(term in text for term in terms):
                counters[label] += 1
    ranked = sorted(counters.items(), key=lambda x: x[1], reverse=True)
    return [label for label, count in ranked if count][:3]


def build_prompt(items, themes):
    samples = []
    for item in items[:50]:
        summary = item.get("summary") or ""
        desc = item.get("description") or ""
        key = item.get("key") or ""
        block = f"- {key}: {summary}\n  {desc[:400]}"
        samples.append(block)
    return (
        "너는 평가 리포트 작성자다. 아래 작업 내용을 읽고 "
        "왜 했는지, 어떤 결과와 기술적 이익이 있었는지 분석해라.\n"
        "반드시 JSON으로 출력해라.\n"
        "키: summary, themes, strengths, weaknesses, impact\n"
        f"테마 힌트: {', '.join(themes)}\n"
        "작업 목록:\n" + "\n".join(samples)
    )


def llm_call(prompt, model, api_url, api_key):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful analyst."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(api_url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = json.loads(resp.read().decode("utf-8"))
    content = raw["choices"][0]["message"]["content"]
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(content)


def heuristic_fallback(themes):
    strengths = [
        "복잡한 과제를 구조화하고 끝까지 완주하는 실행력",
        "ITPT 연계 관점에서 이슈를 연결하고 영향도를 확대",
    ]
    weaknesses = [
        "정량 지표(시간 절감/장애 감소 등)로 영향도를 설명하는 부분 보강 필요",
        "결정 배경과 대안 비교를 문서화하는 습관 강화 필요",
    ]
    impact = [
        "운영 안정성 및 품질 개선에 기여",
        "업무 자동화/표준화로 반복 작업의 비용 절감",
    ]
    if themes:
        strengths.insert(1, f"{', '.join(themes)} 영역에서 방향성 있는 개선 수행")
    return {
        "summary": "ITPT 중심의 과제 연계를 통해 안정적이고 지속적인 개선을 수행",
        "themes": themes,
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "impact": impact[:3],
    }


def main():
    parser = argparse.ArgumentParser(description="Generate strengths insights from Jira source JSON.")
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--out", dest="out_path", required=False)
    parser.add_argument("--max-issues", type=int, default=200)
    parser.add_argument("--llm-prompt-only", default="0")
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    out_path = Path(args.out_path) if args.out_path else base_dir / "strengths-insights.json"
    files = find_source_files(base_dir)
    if not files:
        raise SystemExit("No jira-source.json files found.")

    issues = []
    seen = set()
    for path in files:
        data = load_json(path)
        for issue in data:
            key = issue.get("issue_key")
            if not key or key in seen:
                continue
            seen.add(key)
            issues.append(extract_issue_text(issue))
            if len(issues) >= args.max_issues:
                break
        if len(issues) >= args.max_issues:
            break

    themes = theme_counts(issues)
    prompt = build_prompt(issues, themes)
    llm_api_url = os.environ.get("LLM_API_URL")
    llm_api_key = os.environ.get("LLM_API_KEY")
    llm_model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    prompt_only = os.environ.get("LLM_PROMPT_ONLY", args.llm_prompt_only) == "1"

    result = None
    if llm_api_url and llm_api_key and not prompt_only:
        try:
            result = llm_call(prompt, llm_model, llm_api_url, llm_api_key)
        except Exception:
            result = None

    if result is None:
        result = heuristic_fallback(themes)
        result["prompt"] = prompt

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote insights: {out_path}")


if __name__ == "__main__":
    main()
