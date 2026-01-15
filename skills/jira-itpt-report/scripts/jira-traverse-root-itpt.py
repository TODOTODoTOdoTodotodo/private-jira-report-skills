#!/usr/bin/env python3
import argparse
import base64
import csv
import datetime as dt
import json
import os
import time
import urllib.parse
import urllib.request
from collections import deque


def load_data(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    index = {}
    for item in data:
        key = item.get("issue_key")
        if key:
            index[key] = item
    return index


def load_env_file(path):
    if not path:
        return
    if not os.path.exists(path):
        raise SystemExit(f"ENV_FILE not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env_key = key.strip()
            env_value = value.strip().strip('"').strip("'")
            if env_key and env_key not in os.environ:
                os.environ[env_key] = env_value


def request_json(url, headers, timeout, max_retries=5, backoff=2.0):
    attempt = 0
    delay = backoff
    while True:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code in (429, 503) and attempt < max_retries:
                retry_after = err.headers.get("Retry-After")
                sleep_for = float(retry_after) if retry_after else delay
                time.sleep(sleep_for)
                if not retry_after:
                    delay *= 2
                attempt += 1
                continue
            raise
        except urllib.error.URLError:
            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2
                attempt += 1
                continue
            raise


def neighbors(issue):
    rels = []
    parent = issue.get("parent_key")
    if parent:
        rels.append((parent, "parent"))
    for link in issue.get("issuelinks", []) or []:
        link_key = link.get("issue_key")
        if link_key:
            rels.append((link_key, "relates"))
    return rels


def infer_project_key(issue_key):
    if not issue_key or "-" not in issue_key:
        return None
    return issue_key.split("-", 1)[0]


def find_first_itpt(index, root_key, max_depth):
    root_summary = (index.get(root_key) or {}).get("summary") or ""
    visited = set()
    queue = deque([(root_key, 0)])
    visited.add(root_key)

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        issue = index.get(current)
        if not issue:
            continue
        for nxt, relation in neighbors(issue):
            if nxt in visited:
                continue
            visited.add(nxt)
            to_project_key = (index.get(nxt) or {}).get("project_key")
            if not to_project_key:
                to_project_key = infer_project_key(nxt)
            if to_project_key == "ITPT":
                return {
                    "root_key": root_key,
                    "root_summary": root_summary,
                    "from_key": current,
                    "upper_key": nxt,
                    "relation_type": relation,
                    "depth": depth + 1,
                }
            queue.append((nxt, depth + 1))
    return {
        "root_key": root_key,
        "root_summary": root_summary,
        "from_key": "",
        "upper_key": "",
        "relation_type": "",
        "depth": "",
    }


def get_issue_id(issue_key, base_url, headers, timeout, cache):
    if issue_key in cache:
        return cache[issue_key]
    url = f"{base_url}/rest/api/3/issue/{urllib.parse.quote(issue_key)}?fields="
    data = request_json(url, headers, timeout)
    issue_id = data.get("id", "")
    cache[issue_key] = issue_id
    return issue_id


def pick_merge_timestamp(pull):
    for key in (
        "mergedTimestamp",
        "completedTimestamp",
        "lastUpdate",
        "updatedOn",
        "closedTimestamp",
    ):
        val = pull.get(key)
        if val:
            return val
    return ""


def parse_merge_timestamp(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        ts = value
        if ts > 10**12:
            ts = ts / 1000.0
        return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if raw.isdigit():
        ts = int(raw)
        if ts > 10**12:
            ts = ts / 1000.0
        return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
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


def find_master_merge_date(pull_requests):
    candidates = []
    for pr in pull_requests or []:
        status = (pr.get("status") or "").upper()
        dest = ""
        destination = pr.get("destination")
        if isinstance(destination, dict):
            branch = destination.get("branch")
            if isinstance(branch, dict):
                dest = branch.get("name") or ""
            elif isinstance(branch, str):
                dest = branch
        elif isinstance(destination, str):
            dest = destination
        if status == "MERGED" and dest.lower() == "master":
            ts_raw = pick_merge_timestamp(pr)
            ts = parse_merge_timestamp(ts_raw)
            if ts:
                candidates.append(ts)
    if not candidates:
        return ""
    latest = max(candidates)
    return latest.isoformat()


def get_master_merge_date(issue_key, base_url, headers, timeout, id_cache):
    issue_id = get_issue_id(issue_key, base_url, headers, timeout, id_cache)
    if not issue_id:
        return ""
    params = urllib.parse.urlencode(
        {
            "issueId": issue_id,
            "applicationType": "bitbucket",
            "dataType": "pullrequest",
        }
    )
    url = f"{base_url}/rest/dev-status/1.0/issue/detail?{params}"
    data = request_json(url, headers, timeout)
    pull_requests = []
    for detail in data.get("detail", []) or []:
        prs = detail.get("pullRequests") or detail.get("pullrequests") or []
        pull_requests.extend(prs)
    return find_master_merge_date(pull_requests)


def unique_roots(path):
    seen = set()
    ordered = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            key = line.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            ordered.append(key)
    return ordered


def in_merge_range(merge_ts, start_date, end_date):
    if not start_date and not end_date:
        return True
    ts = parse_merge_timestamp(merge_ts)
    if not ts:
        return False
    day = ts.date()
    if start_date and day < start_date:
        return False
    if end_date and day >= end_date:
        return False
    return True


def parse_range(value):
    if not value:
        return None
    return dt.datetime.strptime(value, "%Y/%m/%d").date()


def main():
    parser = argparse.ArgumentParser(
        description="Find first ITPT parent per root and emit one row per root."
    )
    parser.add_argument("input_json", help="Path to jira-source JSON file")
    parser.add_argument("--batch-file", required=True, help="roots.txt path")
    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--csv-output", required=True)
    parser.add_argument("--env-file", default="")
    parser.add_argument("--include-master-merge", action="store_true")
    parser.add_argument("--merge-start", default="")
    parser.add_argument("--merge-end", default="")
    parser.add_argument("--http-timeout", type=int, default=60)
    args = parser.parse_args()

    index = load_data(args.input_json)
    roots = unique_roots(args.batch_file)

    rows = []
    include_master_merge = args.include_master_merge
    headers = {}
    base_url = ""
    id_cache = {}
    merge_start = parse_range(args.merge_start)
    merge_end = parse_range(args.merge_end)
    if include_master_merge:
        env_file = args.env_file or os.environ.get("ENV_FILE", "")
        if env_file:
            load_env_file(env_file)
        base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
        email = os.environ.get("JIRA_EMAIL", "")
        token = os.environ.get("JIRA_API_TOKEN", "")
        if base_url and email and token:
            auth = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode(
                "ascii"
            )
            headers = {
                "Authorization": f"Basic {auth}",
                "Accept": "application/json",
            }
        else:
            raise SystemExit("Missing JIRA_* env for master merge lookup.")

    for root_key in roots:
        row = find_first_itpt(index, root_key, args.max_depth)
        if include_master_merge:
            row["master_merged_at"] = get_master_merge_date(
                root_key, base_url, headers, args.http_timeout, id_cache
            )
            if not in_merge_range(row.get("master_merged_at"), merge_start, merge_end):
                continue
        rows.append(row)

    # Use UTF-8 with BOM for better Excel compatibility with Korean.
    with open(args.csv_output, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        columns = [
            "root_key",
            "root_summary",
            "from_key",
            "upper_key",
            "relation_type",
            "depth",
        ]
        if include_master_merge:
            columns.append("master_merged_at")
        writer.writerow(columns)
        for row in rows:
            data = [
                row.get("root_key", ""),
                row.get("root_summary", ""),
                row.get("from_key", ""),
                row.get("upper_key", ""),
                row.get("relation_type", ""),
                row.get("depth", ""),
            ]
            if include_master_merge:
                data.append(row.get("master_merged_at", ""))
            writer.writerow(data)


if __name__ == "__main__":
    main()
