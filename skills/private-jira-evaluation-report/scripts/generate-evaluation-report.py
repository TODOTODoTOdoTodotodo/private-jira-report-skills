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
        if upper_key.startswith("ITPT-"):
            itpt.append(row)
        root_key = (row.get("root_key") or "").strip()
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


def pick_top(rows, n):
    def key_fn(row):
        return row.get("master_merged_at") or ""
    return sorted(rows, key=key_fn, reverse=True)[:n]


def fmt_issue(row):
    root_key = row.get("root_key") or ""
    root_summary = row.get("root_summary") or ""
    root_desc = row.get("root_description") or ""
    upper_key = row.get("upper_key") or ""
    upper_summary = row.get("upper_summary") or ""
    upper_desc = row.get("upper_description") or ""
    merged = row.get("master_merged_at") or "-"
    parts = [f"{root_key}: {root_summary}"]
    if root_desc:
        parts.append(f"요약: {root_desc}")
    if upper_key:
        parts.append(f"ITPT: {upper_key} {upper_summary}".strip())
        if upper_desc:
            parts.append(f"ITPT 요약: {upper_desc}")
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

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# {args.year} 개인 성과 평가 보고서\n\n")

        f.write("## 분기별 성과 요약\n")
        for q, rows in quarter_data.items():
            itpt_q, mgtt_q = split_issues(rows)
            f.write(f"### {q}\n")
            f.write(f"- ITPT 연계: {len(itpt_q)}건\n")
            f.write(f"- MGTT 루트: {len(mgtt_q)}건\n")
            for item in pick_top(itpt_q, min(args.top_n, 5)):
                f.write(f"  - {fmt_issue(item)}\n")
            f.write("\n")

        f.write("## 전체 성과 요약\n")
        f.write(f"- ITPT 연계 총 {len(itpt_rows)}건\n")
        f.write(f"- MGTT 루트 총 {len(mgtt_rows)}건\n")
        f.write("### 대표 성과 (ITPT 중심)\n")
        for item in pick_top(itpt_rows, args.top_n):
            f.write(f"- {fmt_issue(item)}\n")
        f.write("\n")

        f.write("## MGTT 기여 요약\n")
        for item in pick_top(mgtt_rows, min(args.top_n, 10)):
            f.write(f"- {fmt_issue(item)}\n")
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
        f.write("\n")

        f.write("## 나의 강점\n")
        f.write(
            "- ITPT 연계 중심의 성과 축적(기획/개발/QA 연계)\n"
            "- 분기 단위로 누적 성과를 안정적으로 수행\n"
            "- 운영 이슈 대응과 품질 개선의 지속적 수행\n\n"
        )

        f.write("## 보강할 점\n")
        f.write(
            "- 성과를 수치화(시간 절감/장애 감소/전환율 개선)하여 명확한 근거 보강\n"
            "- 분기별 대표 성과의 배경/행동/결과를 정리해 전달력 강화\n\n"
        )

        f.write("## 분기별 회고 및 인사이트\n")
        for q, rows in quarter_data.items():
            itpt_q, mgtt_q = split_issues(rows)
            f.write(f"### {q}\n")
            f.write(f"- 주요 ITPT 연계 {len(itpt_q)}건, MGTT 루트 {len(mgtt_q)}건\n")
            f.write("- 반복 발생 이슈는 근본 원인 제거가 필요\n")
            f.write("- 운영/품질 항목은 자동화와 예방 중심으로 전환\n\n")

        f.write("## 전체 회고 및 인사이트\n")
        f.write(
            "- ITPT 중심의 결과는 확보되었으나, 영향도 정량화가 필요\n"
            "- 분기별 지표와 성과를 묶어 팀/조직 차원의 가치로 확장 필요\n"
        )

    print(f"Wrote evaluation report: {out_path}")


if __name__ == "__main__":
    main()
