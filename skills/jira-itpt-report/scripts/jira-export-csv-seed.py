#!/usr/bin/env python3
import argparse
import base64
import csv
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import time


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


def request_json(url, headers, params=None, data=None, timeout=30, max_retries=5, backoff=2.0):
    if params:
        url = url + "?" + urllib.parse.urlencode(params, doseq=True)
    attempt = 0
    delay = backoff
    while True:
        req = urllib.request.Request(url, headers=headers, data=data)
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


def build_headers(base_url, email, token):
    auth = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
    }


def find_development_field(base_url, headers, timeout, name_hint):
    fields = request_json(f"{base_url}/rest/api/3/field", headers, timeout=timeout)
    if not isinstance(fields, list):
        return ""
    name_hint = (name_hint or "development").lower()
    for field in fields:
        name = (field.get("name") or "").lower()
        if name == name_hint:
            return field.get("id") or ""
    for field in fields:
        name = (field.get("name") or "").lower()
        if name_hint in name:
            return field.get("id") or ""
    return ""


def parse_timestamp(value):
    if not value:
        return None
    raw = value.strip()
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


def format_korean_ampm(value):
    parsed = parse_timestamp(value)
    if not parsed:
        return value or ""
    text = parsed.strftime("%Y-%m-%d %I:%M %p")
    return text.replace("AM", "오전").replace("PM", "오후")


def search_page(base_url, headers, jql, fields, max_results, timeout, page_token=None):
    if page_token:
        payload = {"jql": jql, "nextPageToken": page_token, "fields": fields}
    else:
        payload = {"jql": jql, "fields": fields, "maxResults": max_results}
    data = json.dumps(payload).encode("utf-8")
    post_headers = dict(headers)
    post_headers["Content-Type"] = "application/json"
    return request_json(
        f"{base_url}/rest/api/3/search/jql",
        post_headers,
        data=data,
        timeout=timeout,
    )


def paginate_search(base_url, headers, jql, fields, max_results, max_pages, timeout):
    pages = 0
    seen = set()
    page_token = None
    while True:
        resp = search_page(
            base_url,
            headers,
            jql,
            fields,
            max_results,
            timeout,
            page_token=page_token,
        )
        issues = resp.get("issues", []) or []
        page_token = resp.get("nextPageToken")
        is_last = resp.get("isLast")
        new_count = 0
        for issue in issues:
            key = issue.get("key")
            if not key or key in seen:
                continue
            seen.add(key)
            new_count += 1
            yield issue
        pages += 1
        if max_pages and pages >= max_pages:
            break
        if page_token:
            if is_last is True:
                break
            continue
        if len(issues) < max_results:
            break
        if new_count == 0:
            break


def main():
    parser = argparse.ArgumentParser(description="Export Jira issues to CSV seed.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--projects", default="")
    parser.add_argument("--jql", default="")
    parser.add_argument("--development-field-id", default="")
    parser.add_argument("--development-field-name", default="development")
    parser.add_argument("--max-results", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    load_env_file(args.env_file)
    base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not base_url or not email or not token:
        raise SystemExit("Missing JIRA_* env for CSV seed export.")
    headers = build_headers(base_url, email, token)

    projects = [p.strip() for p in args.projects.split(",") if p.strip()]
    assignee_account_ids = os.environ.get("ASSIGNEE_ACCOUNT_IDS", "").strip()
    if not assignee_account_ids:
        assignee_account_ids = os.environ.get("ASSIGNEE_ACCOUNT_ID", "").strip()

    if args.jql:
        jql = args.jql
    else:
        if assignee_account_ids:
            assignees = [a.strip() for a in assignee_account_ids.split(",") if a.strip()]
            assignee_clause = "assignee in (" + ", ".join(assignees) + ")"
        else:
            assignee_clause = "assignee = currentUser()"
        if projects:
            project_filter = "project in (" + ", ".join(projects) + ")"
            jql = f"{project_filter} AND {assignee_clause}"
        else:
            jql = assignee_clause

    dev_field = args.development_field_id
    if not dev_field:
        dev_field = find_development_field(
            base_url, headers, args.timeout, args.development_field_name
        )
    fields = ["key", "project", "created", "updated"]
    if dev_field:
        fields.append(dev_field)

    out_path = args.out
    with open(out_path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "이슈 키",
                "프로젝트 키",
                "만듦",
                "업데이트",
                "사용자정의 필드 (development)",
            ]
        )
        for issue in paginate_search(
            base_url,
            headers,
            jql,
            fields,
            args.max_results,
            args.max_pages,
            args.timeout,
        ):
            fields_data = issue.get("fields", {}) or {}
            project_key = (fields_data.get("project") or {}).get("key", "")
            created = format_korean_ampm(fields_data.get("created") or "")
            updated = format_korean_ampm(fields_data.get("updated") or "")
            dev_value = fields_data.get(dev_field) if dev_field else None
            if isinstance(dev_value, (dict, list)):
                dev_value = json.dumps(dev_value, ensure_ascii=False)
            elif dev_value is None:
                dev_value = ""
            writer.writerow(
                [
                    issue.get("key", ""),
                    project_key,
                    created,
                    updated,
                    dev_value,
                ]
            )

    print(f"Wrote seed CSV: {out_path}")


if __name__ == "__main__":
    main()
