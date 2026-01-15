#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
from pathlib import Path


def parse_args():
  parser = argparse.ArgumentParser(description="Generate interview-style script from private Jira CSV.")
  parser.add_argument("--year", type=int, required=True, help="Target year (e.g., 2025)")
  parser.add_argument("--csv", dest="csv_path", required=True, help="Path to merged itpt-links.csv")
  parser.add_argument("--out", dest="out_path", required=False, help="Output markdown path")
  return parser.parse_args()


def read_rows(csv_path):
  rows = []
  with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
      rows.append(row)
  return rows


def year_from_iso(ts):
  if not ts:
    return None
  try:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).year
  except ValueError:
    return None


def main():
  args = parse_args()
  csv_path = Path(args.csv_path)
  if not csv_path.exists():
    raise SystemExit(f"CSV not found: {csv_path}")

  out_path = Path(args.out_path) if args.out_path else csv_path.with_name(f"interview-script-{args.year}.md")

  rows = read_rows(csv_path)
  roots = {}
  for row in rows:
    key = (row.get("root_key") or "").strip()
    if not key:
      continue
    if key not in roots:
      roots[key] = {
        "root_key": key,
        "root_summary": (row.get("root_summary") or "").strip(),
        "master_merged_at": (row.get("master_merged_at") or "").strip(),
      }

  total_roots = len(roots)
  merged_in_year = 0
  for item in roots.values():
    if year_from_iso(item.get("master_merged_at")) == args.year:
      merged_in_year += 1

  sample_items = sorted(
    roots.values(),
    key=lambda r: (r.get("master_merged_at") or "", r.get("root_key") or ""),
    reverse=True,
  )[:5]

  all_items = sorted(
    roots.values(),
    key=lambda r: (r.get("master_merged_at") or "", r.get("root_key") or ""),
    reverse=True,
  )

  with open(out_path, "w", encoding="utf-8") as f:
    f.write(f"# {args.year} 개인 업무 기여 요약 (면접 답변 스크립트)\n\n")
    f.write("## Q1. 2025년에 당신이 회사에 기여한게 뭐가있는지 말해봐라.\n")
    f.write("A. ")
    f.write(
      f"{args.year}년에는 개인 리포트 기준으로 총 {total_roots}건의 루트 이슈를 마무리했고, "
      f"그 중 master 브랜치에 merge된 기준으로 {merged_in_year}건이 해당 연도 내 결과로 확인되었습니다. "
      "주요 작업은 서비스 안정화, 기능 개선, 운영 대응에 집중했으며, 일정 내 완료와 품질 관리에 초점을 두었습니다.\n\n"
    )

    f.write("### 대표 성과 예시\n")
    if sample_items:
      for item in sample_items:
        key = item.get("root_key")
        summary = item.get("root_summary") or "(제목 없음)"
        merged = item.get("master_merged_at") or "-"
        f.write(f"- {key}: {summary} (master merge: {merged})\n")
    else:
      f.write("- (대표 성과 예시를 찾지 못했습니다)\n")
    f.write("\n")

    f.write("## 전체 이슈 목록\n")
    if all_items:
      for item in all_items:
        key = item.get("root_key")
        summary = item.get("root_summary") or "(제목 없음)"
        merged = item.get("master_merged_at") or "-"
        f.write(f"- {key}: {summary} (master merge: {merged})\n")
    else:
      f.write("- (이슈 목록이 없습니다)\n")
    f.write("\n")

    f.write("## Q2. 당신의 장점은 무엇인가?\n")
    f.write(
      "A. 첫째, 목표 대비 결과를 꾸준히 쌓는 실행력입니다. 분기별 목표를 작은 단위로 쪼개고, "
      "주차 단위로 병렬 처리해 리스크를 줄이면서 결과를 냈습니다. "
      "둘째, 품질 기준을 유지하는 습관입니다. merge 기준으로 결과를 확인하면서 품질과 마감 준수에 집중했습니다.\n\n"
    )

    f.write("## Q3. 보강할 부분은 무엇이며 어떻게 발전할 것인가?\n")
    f.write(
      "A. 더 체계적인 성과 스토리텔링과 영향도 정리가 필요합니다. "
      "향후에는 이슈별로 정량 지표(시간 절감, 장애 감소, 비용 절감 등)를 함께 기록하고, "
      "분기마다 대표 성과의 배경-행동-결과를 정리해 면접/평가에 즉시 활용 가능한 형태로 발전시키겠습니다.\n\n"
    )

    f.write("## Q4. 향후 목표는 무엇인가?\n")
    f.write(
      "A. 다음 해에는 단순 처리량을 넘어 핵심 지표 개선에 직접 기여하는 이슈 비중을 늘리겠습니다. "
      "또한 리포트 자동화 결과를 팀 공유 포맷으로 확장해 협업 효율까지 높이는 것이 목표입니다.\n"
    )

  print(f"Wrote interview script: {out_path}")


if __name__ == "__main__":
  main()
