#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Generate evaluation report from Jira CSVs.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--out", dest="out_path", required=False)
    parser.add_argument("--top-n", type=int, default=10)
    return parser.parse_args()


def load_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def split_issues(rows):
    itpt = []
    mgtt = []
    for row in rows:
        upper_key = (row.get("upper_key") or "").strip()
        root_key_raw = (row.get("root_key") or "").strip()
        root_key = root_key_raw.rsplit("/browse/", 1)[-1] if "/browse/" in root_key_raw else root_key_raw
        if upper_key.startswith("ITPT-"):
            itpt.append(row)
        if root_key.startswith("MGTT-"):
            mgtt.append(row)
    return itpt, mgtt


def build_benefit_signals(rows):
    keywords = {
        "stability": ["장애", "오류", "버그", "안정", "예외", "실패"],
        "performance": ["성능", "속도", "지연", "최적화", "개선"],
        "cost": ["비용", "절감", "운영", "효율", "자동화"],
        "revenue": ["매출", "전환", "판매", "예약", "결제", "상품"],
        "quality": ["QA", "품질", "리뷰", "테스트"],
        "ai": ["AI", "LLM", "Gemini", "요약", "추천"],
    }
    counters = {k: 0 for k in keywords}
    for row in rows:
        text = " ".join(
            [
                row.get("root_summary") or "",
                row.get("root_description") or "",
                row.get("upper_summary") or "",
                row.get("upper_description") or "",
            ]
        )
        for key, terms in keywords.items():
            if any(term in text for term in terms):
                counters[key] += 1
    return counters


def extract_text(row, focus="all"):
    parts = []
    if focus in ("all", "root"):
        parts.append(row.get("root_summary") or "")
        parts.append(row.get("root_description") or "")
    if focus in ("all", "itpt"):
        parts.append(row.get("upper_summary") or "")
        parts.append(row.get("upper_description") or "")
    return " ".join(parts)


def build_theme_signals(rows, focus="itpt"):
    themes = {
        "stability": ["장애", "오류", "버그", "안정", "예외", "실패", "복구"],
        "performance": ["성능", "속도", "지연", "최적화", "튜닝"],
        "automation": ["자동화", "배치", "파이프라인", "스크립트", "워크플로"],
        "release": ["배포", "릴리스", "런칭", "출시"],
        "quality": ["QA", "품질", "테스트", "검증"],
        "data": ["데이터", "지표", "로그", "분석", "리포트"],
        "security": ["보안", "권한", "취약", "암호", "인증"],
        "product": ["기능", "요구사항", "기획", "화면", "정책"],
        "ops": ["운영", "모니터링", "알림", "대응"],
    }
    counters = {k: 0 for k in themes}
    for row in rows:
        text = extract_text(row, focus=focus)
        if not text:
            continue
        for key, terms in themes.items():
            if any(term in text for term in terms):
                counters[key] += 1
    return counters


def top_themes(counters, top_n=3):
    labels = {
        "stability": "안정성/장애 대응",
        "performance": "성능/최적화",
        "automation": "자동화/파이프라인",
        "release": "배포/런칭",
        "quality": "품질/검증",
        "data": "데이터/지표",
        "security": "보안/권한",
        "product": "기능/기획",
        "ops": "운영/모니터링",
    }
    ranked = sorted(
        ((key, count) for key, count in counters.items() if count),
        key=lambda item: item[1],
        reverse=True,
    )
    return [labels[key] for key, _ in ranked[:top_n]]


def metric_suggestions(theme_labels):
    mapping = {
        "안정성/장애 대응": [
            "장애 건수/재발률",
            "MTTR(평균 복구 시간)",
            "영향 사용자/서비스 범위",
        ],
        "성능/최적화": [
            "응답시간/처리량 변화",
            "오류율 감소",
            "리소스 사용량 감소",
        ],
        "자동화/파이프라인": [
            "수동 작업 감소 시간",
            "배포/운영 리드타임",
            "반복 작업 건수 감소",
        ],
        "배포/런칭": [
            "릴리스 빈도",
            "배포 실패율",
            "릴리스 리드타임",
        ],
        "품질/검증": [
            "테스트 커버리지",
            "결함 유입률",
            "QA 사이클 시간",
        ],
        "데이터/지표": [
            "대시보드/리포트 활용도",
            "분석 리드타임",
            "의사결정 개선 사례 수",
        ],
        "보안/권한": [
            "취약점/권한 이슈 감소",
            "보안 점검 대응 시간",
            "권한 승인 리드타임",
        ],
        "기능/기획": [
            "기능 사용률/전환율",
            "사용자 만족도/CS 감소",
            "요구사항 리드타임",
        ],
        "운영/모니터링": [
            "알림→조치 리드타임",
            "모니터링 커버리지",
            "운영 비용 절감",
        ],
    }
    items = []
    for label in theme_labels:
        items.extend(mapping.get(label, []))
    seen = set()
    uniq = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        uniq.append(item)
    return uniq


def pick_top(rows, n):
    def key_fn(row):
        return row.get("master_merged_at") or ""
    return sorted(rows, key=key_fn, reverse=True)[:n]


def short_issue(row):
    root_key_raw = (row.get("root_key") or "").strip()
    root_key = root_key_raw.rsplit("/browse/", 1)[-1] if "/browse/" in root_key_raw else root_key_raw
    upper_key = (row.get("upper_key") or "").strip()
    key = root_key or upper_key
    return key or "-"


def top_benefit_labels(benefit):
    labels = {
        "stability": "안정성/장애",
        "performance": "성능/최적화",
        "cost": "비용/운영 효율",
        "revenue": "매출/전환",
        "quality": "품질/QA",
        "ai": "AI/LLM",
    }
    ranked = sorted(
        ((key, count) for key, count in benefit.items() if count),
        key=lambda item: item[1],
        reverse=True,
    )
    return [labels[key] for key, _ in ranked[:3]]


def quarter_insights(rows, top_n=1):
    itpt_q, mgtt_q = split_issues(rows)
    total = len(rows)
    benefit = build_benefit_signals(rows)
    top_labels = top_benefit_labels(benefit)
    itpt_themes = top_themes(build_theme_signals(itpt_q, focus="itpt"), top_n=2)
    bullets = []
    if total == 0:
        bullets.append("- 해당 분기에 매칭된 이슈가 없어 기간/필터(assignee·업데이트 범위) 재확인 필요")
        bullets.append("- 분기 업무가 다른 프로젝트/에픽으로 이동했는지 확인 권장")
        return bullets
    bullets.append(f"- 주요 ITPT 연계 {len(itpt_q)}건, MGTT 루트 {len(mgtt_q)}건")
    if top_labels:
        bullets.append(f"- 기여 성격: {', '.join(top_labels)}")
    if itpt_themes:
        bullets.append(f"- ITPT 작업 성격: {', '.join(itpt_themes)}")
    if itpt_q:
        bullets.append(f"- 대표 사례: {short_issue(pick_top(itpt_q, top_n)[0])}")
    elif mgtt_q:
        bullets.append(f"- 대표 사례: {short_issue(pick_top(mgtt_q, top_n)[0])}")
    return bullets


def fmt_issue(row):
    root_key_raw = row.get("root_key") or ""
    root_key = root_key_raw.rsplit("/browse/", 1)[-1] if "/browse/" in root_key_raw else root_key_raw
    upper_key = row.get("upper_key") or ""
    merged = row.get("master_merged_at") or "-"
    parts = [root_key or upper_key]
    if upper_key:
        parts.append(f"ITPT: {upper_key}".strip())
    parts.append(f"merge: {merged}")
    return " / ".join([p for p in parts if p])


def main():
    args = parse_args()
    base = Path(args.base_dir)
    merged = base / "itpt-links.csv"
    if not merged.exists():
        raise SystemExit(f"Missing merged CSV: {merged}")

    out_path = Path(args.out_path) if args.out_path else base / f"evaluation-{args.year}.md"

    quarter_paths = [(q, base / q / "itpt-links.csv") for q in ("Q1", "Q2", "Q3", "Q4")]
    quarter_data = {}
    for q, path in quarter_paths:
        if path.exists():
            quarter_data[q] = load_csv(path)
        else:
            quarter_data[q] = []

    merged_rows = load_csv(merged)
    itpt_rows, mgtt_rows = split_issues(merged_rows)
    benefit = build_benefit_signals(merged_rows)
    benefit_labels = top_benefit_labels(benefit)
    itpt_theme_labels = top_themes(build_theme_signals(itpt_rows, focus="itpt"), top_n=3)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# {args.year} 개인 성과 평가 보고서\n\n")

        f.write("## 전체 성과 및 대표 성과\n")
        f.write(f"- ITPT 연계 총 {len(itpt_rows)}건\n")
        f.write(f"- MGTT 루트 총 {len(mgtt_rows)}건\n")
        f.write("### 대표 성과 (ITPT 중심, 키 기준)\n")
        for item in pick_top(itpt_rows, min(args.top_n, 10)):
            f.write(f"- {short_issue(item)}\n")
        f.write("\n")

        f.write("## 기여 요약 (MGTT 포함)\n")
        if mgtt_rows:
            for item in pick_top(mgtt_rows, min(args.top_n, 10)):
                f.write(f"- {short_issue(item)}\n")
        else:
            f.write("- MGTT 루트 성과가 없어 ITPT 중심으로 평가됨\n")
        f.write("\n")

        f.write("## 회사 기여/이익 관점\n")
        f.write(
            f"- 안정성/장애 대응 관련: {benefit['stability']}건\n"
            f"- 성능/최적화 관련: {benefit['performance']}건\n"
            f"- 비용/운영 효율 관련: {benefit['cost']}건\n"
            f"- 매출/전환 관련: {benefit['revenue']}건\n"
            f"- 품질/QA 관련: {benefit['quality']}건\n"
            f"- AI/LLM 관련: {benefit['ai']}건\n"
        )
        if benefit_labels:
            f.write(f"- 기여 성격 요약: {', '.join(benefit_labels)}\n")
        if itpt_theme_labels:
            f.write(f"- ITPT 작업 성격: {', '.join(itpt_theme_labels)}\n")
        f.write("\n")

        f.write("## 영향도 정량화를 위한 필요 항목\n")
        metrics = metric_suggestions(itpt_theme_labels or [])
        if metrics:
            for item in metrics:
                f.write(f"- {item}\n")
        else:
            f.write("- 장애/성능/운영/비용 관련 지표 정의 필요\n")
        f.write("\n")

        f.write("## 팀/조직 가치 확장을 위한 필요 항목\n")
        f.write("- 재사용 가능한 산출물(모듈/템플릿) 수와 적용 팀 수\n")
        f.write("- 배포/QA 리드타임 감소 및 프로세스 단축 수치\n")
        f.write("- 타팀 의존 이슈 감소 및 협업 이슈 해결 건수\n")
        f.write("- 문서/가이드 제공으로 온보딩 시간 감소\n\n")

        f.write("## 나의 강점\n")
        f.write("- ITPT 연계 기반으로 성과를 구조적으로 축적\n")
        if itpt_theme_labels:
            f.write(f"- {', '.join(itpt_theme_labels)} 영역에서 방향성 있는 개선 수행\n")
        if benefit_labels:
            f.write(f"- {', '.join(benefit_labels)} 관점에서 반복 기여\n")
        f.write("- 분기 단위 누적과 운영 이슈 대응을 꾸준히 수행\n\n")

        f.write("## 보강할 점\n")
        f.write(
            "- 성과를 수치화(시간 절감/장애 감소/전환율 개선)해 근거 강화\n"
            "- ITPT 작업의 맥락/의사결정/결과를 더 명확히 정리\n\n"
        )

        f.write("## 분기별 성과\n")
        for q, rows in quarter_data.items():
            itpt_q, mgtt_q = split_issues(rows)
            f.write(f"### {q}\n")
            f.write(f"- ITPT 연계: {len(itpt_q)}건\n")
            f.write(f"- MGTT 루트: {len(mgtt_q)}건\n")
            if itpt_q:
                top_item = pick_top(itpt_q, 1)[0]
                f.write(f"- 대표 성과 키: {short_issue(top_item)}\n")
            elif mgtt_q:
                top_item = pick_top(mgtt_q, 1)[0]
                f.write(f"- 대표 성과 키: {short_issue(top_item)}\n")
            f.write("\n")

        f.write("## 분기별 회고 및 인사이트\n")
        for q, rows in quarter_data.items():
            f.write(f"### {q}\n")
            for bullet in quarter_insights(rows, top_n=1):
                f.write(f"{bullet}\n")
            f.write("\n")

        f.write("## 전체 회고 및 인사이트\n")
        if itpt_theme_labels:
            f.write(f"- ITPT 작업은 {', '.join(itpt_theme_labels)} 중심으로 진행됨\n")
        f.write("- ITPT 중심의 결과는 확보되었으나, 영향도 정량화가 필요\n")
        f.write("- 분기별 지표와 성과를 묶어 팀/조직 차원의 가치로 확장 필요\n")

    print(f"Wrote evaluation report: {out_path}")


if __name__ == "__main__":
    main()
