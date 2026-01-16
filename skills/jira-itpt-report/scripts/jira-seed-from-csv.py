#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import json
from pathlib import Path


def parse_date(value):
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    raw = raw.replace("\uc624\uc804", "AM").replace("\uc624\ud6c4", "PM")
    for fmt in ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def parse_iso(value):
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            parsed = dt.datetime.strptime(raw, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed
        except ValueError:
            continue
    return None


def extract_json_blob(raw):
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    idx = text.find("json=")
    if idx == -1:
        if text.startswith("{") and "cachedValue" in text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return None
        return None
    start = text.find("{", idx)
    if start == -1:
        return None
    depth = 0
    end = None
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return None
    blob = text[start:end]
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def extract_merge_last_updated(dev_field):
    data = extract_json_blob(dev_field)
    if not data:
        return ""
    overall = (
        data.get("cachedValue", {})
        .get("summary", {})
        .get("pullrequest", {})
        .get("overall", {})
    )
    state = (overall.get("state") or "").upper()
    if state != "MERGED":
        return ""
    return overall.get("lastUpdated") or ""


def pick_column(fieldnames, candidates):
    for name in candidates:
        if name in fieldnames:
            return name
    return ""


def main():
    parser = argparse.ArgumentParser(description="Filter Jira CSV by date and emit key list.")
    parser.add_argument("--csv", required=True, help="Jira CSV export path")
    parser.add_argument("--start", required=True, help="YYYY/MM/DD inclusive")
    parser.add_argument("--end", required=True, help="YYYY/MM/DD exclusive")
    parser.add_argument("--projects", default="", help="Comma-separated project keys")
    parser.add_argument("--mode", choices=["dev", "plan_qa"], default="dev")
    parser.add_argument("--out-keys", required=True)
    parser.add_argument("--out-merge", default="")
    args = parser.parse_args()

    start_date = dt.datetime.strptime(args.start, "%Y/%m/%d").date()
    end_date = dt.datetime.strptime(args.end, "%Y/%m/%d").date()
    project_filter = {p.strip() for p in args.projects.split(",") if p.strip()}

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    keys = []
    seen = set()
    merge_map = {}

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit("CSV has no headers.")
        key_col = pick_column(reader.fieldnames, ["\uc774\uc288 \ud0a4", "Issue key", "Key"])
        proj_col = pick_column(reader.fieldnames, ["\ud504\ub85c\uc81d\ud2b8 \ud0a4", "Project key"])
        created_col = pick_column(reader.fieldnames, ["\ub9cc\ub4e6", "Created"])
        updated_col = pick_column(reader.fieldnames, ["\uc5c5\ub370\uc774\ud2b8", "Updated"])
        dev_col = pick_column(
            reader.fieldnames,
            [
                "\uc0ac\uc6a9\uc790\uc815\uc758 \ud544\ub4dc (development)",
                "Custom field (development)",
                "Development",
            ],
        )

        if not key_col:
            raise SystemExit("Missing issue key column in CSV.")
        if args.mode == "dev" and not dev_col:
            raise SystemExit("Missing development column for dev mode.")

        for row in reader:
            issue_key = (row.get(key_col) or "").strip()
            if not issue_key:
                continue
            project_key = (row.get(proj_col) or "").strip()
            if project_filter and project_key and project_key not in project_filter:
                continue

            if args.mode == "dev":
                last_updated = extract_merge_last_updated(row.get(dev_col, ""))
                if not last_updated:
                    continue
                merge_dt = parse_iso(last_updated)
                if not merge_dt:
                    continue
                merge_date = merge_dt.date()
                if not (start_date <= merge_date < end_date):
                    continue
                if issue_key not in seen:
                    keys.append(issue_key)
                    seen.add(issue_key)
                merge_map[issue_key] = last_updated
            else:
                updated_val = row.get(updated_col, "") if updated_col else ""
                created_val = row.get(created_col, "") if created_col else ""
                candidate_dt = parse_date(updated_val) or parse_date(created_val)
                if not candidate_dt:
                    continue
                day = candidate_dt.date()
                if not (start_date <= day < end_date):
                    continue
                if issue_key not in seen:
                    keys.append(issue_key)
                    seen.add(issue_key)

    Path(args.out_keys).write_text("\n".join(keys) + ("\n" if keys else ""), encoding="utf-8")
    if args.out_merge:
        Path(args.out_merge).write_text(
            json.dumps(merge_map, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
