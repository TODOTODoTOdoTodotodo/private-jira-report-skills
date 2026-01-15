#!/usr/bin/env python3
import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise SystemExit(f"Missing required env: {name}")
    return value


def build_date_range():
    year = int(get_env("YEAR", "2025"))
    month = get_env("MONTH", "")
    start_override = get_env("START_DATE", "")
    end_override = get_env("END_DATE", "")

    if start_override and end_override:
        start_date = start_override
        end_date = end_override
    elif start_override or end_override:
        raise SystemExit("START_DATE and END_DATE must be set together.")
    elif month:
        month_num = int(month)
        if month_num < 1 or month_num > 12:
            raise SystemExit("MONTH must be between 1 and 12.")
        start_date = f"{year}/{month_num:02d}/01"
        if month_num == 12:
            end_date = f"{year + 1}/01/01"
        else:
            end_date = f"{year}/{month_num + 1:02d}/01"
    else:
        start_date = f"{year}/01/01"
        end_date = f"{year + 1}/01/01"

    start_ts = start_date.replace("/", "-") + "T00:00:00.000+0000"
    end_ts = end_date.replace("/", "-") + "T00:00:00.000+0000"
    return start_date, end_date, start_ts, end_ts


class JiraClient:
    def __init__(self, base_url, email, token, max_retries=5, backoff=2.0):
        self.base_url = base_url.rstrip("/")
        auth = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
        self.headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}
        self.max_retries = max_retries
        self.backoff = backoff

    def _request(self, url, params=None):
        if params:
            url = url + "?" + urllib.parse.urlencode(params, doseq=True)
        attempt = 0
        backoff = self.backoff
        while True:
            req = urllib.request.Request(url, headers=self.headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as err:
                if err.code in (429, 503) and attempt < self.max_retries:
                    retry_after = err.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else backoff
                    time.sleep(wait)
                    if not retry_after:
                        backoff *= 2
                    attempt += 1
                    continue
                raise
            except urllib.error.URLError:
                if attempt < self.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    attempt += 1
                    continue
                raise

    def search(self, jql, start_at=0, max_results=100):
        return self._request(
            f"{self.base_url}/rest/api/3/search/jql",
            {
                "jql": jql,
                "fields": "key",
                "startAt": str(start_at),
                "maxResults": str(max_results),
            },
        )

    def issue(self, key):
        return self._request(
            f"{self.base_url}/rest/api/3/issue/{key}",
            {"fields": "summary,issuetype,project,parent,issuelinks"},
        )

    def changelog(self, key, start_at=0, max_results=100):
        return self._request(
            f"{self.base_url}/rest/api/3/issue/{key}/changelog",
            {"startAt": str(start_at), "maxResults": str(max_results)},
        )


def paginate_search(client, jql, max_results, max_pages=0):
    keys = []
    start_at = 0
    pages = 0
    while True:
        resp = client.search(jql, start_at=start_at, max_results=max_results)
        issues = resp.get("issues", [])
        keys.extend([item.get("key") for item in issues if item.get("key")])
        total = resp.get("total")
        pages += 1
        if max_pages and pages >= max_pages:
            break
        if isinstance(total, int):
            start_at += max_results
            if start_at >= total:
                break
        else:
            if len(issues) < max_results:
                break
            start_at += max_results
    return keys


def normalize_issue(issue):
    fields = issue.get("fields", {})
    issuelinks = []
    for link in fields.get("issuelinks", []) or []:
        issue_key = None
        if "inwardIssue" in link:
            issue_key = link["inwardIssue"].get("key")
        elif "outwardIssue" in link:
            issue_key = link["outwardIssue"].get("key")
        issuelinks.append(
            {
                "type": link.get("type", {}).get("name"),
                "inward": link.get("type", {}).get("inward"),
                "outward": link.get("type", {}).get("outward"),
                "issue_key": issue_key,
            }
        )
    return {
        "issue_key": issue.get("key"),
        "summary": fields.get("summary"),
        "project_key": (fields.get("project") or {}).get("key"),
        "issuetype": (fields.get("issuetype") or {}).get("name"),
        "parent_key": (fields.get("parent") or {}).get("key"),
        "issuelinks": issuelinks,
    }


def activity_match(client, key, account_id, name_contains, start_ts, end_ts):
    start_at = 0
    max_results = 100
    while True:
        resp = client.changelog(key, start_at=start_at, max_results=max_results)
        histories = resp.get("values", [])
        for history in histories:
            author = history.get("author", {})
            if account_id and author.get("accountId") == account_id:
                created = history.get("created")
                if created and start_ts <= created < end_ts:
                    return True
            if name_contains:
                name = author.get("displayName", "")
                if name_contains in name:
                    created = history.get("created")
                    if created and start_ts <= created < end_ts:
                        return True
        total = resp.get("total")
        if isinstance(total, int):
            start_at += max_results
            if start_at >= total:
                break
        else:
            if len(histories) < max_results:
                break
            start_at += max_results
    return False


def fetch_if_activity(client, key, account_id, name_contains, start_ts, end_ts):
    if activity_match(client, key, account_id, name_contains, start_ts, end_ts):
        issue = client.issue(key)
        return normalize_issue(issue)
    return None


def main():
    parser = argparse.ArgumentParser(description="Export Jira issues by activity history.")
    parser.add_argument("output", nargs="?", default="jira-source-activity.json")
    args = parser.parse_args()

    base_url = get_env("JIRA_BASE_URL", required=True)
    email = get_env("JIRA_EMAIL", required=True)
    token = get_env("JIRA_API_TOKEN", required=True)
    account_id = get_env("JIRA_ACCOUNT_ID", required=False)
    name_contains = get_env("ACTIVITY_NAME_CONTAINS", "")
    projects = get_env("PROJECTS", "MGTT,ITPT")
    jql_extra = get_env("JQL_EXTRA", "")
    max_results = int(get_env("MAX_RESULTS", "100"))
    max_pages = int(get_env("MAX_PAGES", "0"))
    max_issues = int(get_env("MAX_ISSUES", "0"))
    concurrency = int(get_env("CONCURRENCY", "8"))

    start_date, end_date, start_ts, end_ts = build_date_range()
    print(f"date range: {start_date} to {end_date}")

    client = JiraClient(base_url, email, token)

    project_list = [p.strip() for p in projects.split(",") if p.strip()]
    project_filter = "project in (" + ", ".join(project_list) + ")"
    jql = f'updated >= "{start_date}" AND updated < "{end_date}" AND {project_filter}'
    if jql_extra:
        jql += f" AND {jql_extra}"

    keys = paginate_search(client, jql, max_results, max_pages)
    if max_issues:
        keys = keys[:max_issues]

    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        tasks = {
            pool.submit(fetch_if_activity, client, key, account_id, name_contains, start_ts, end_ts): key
            for key in keys
        }
        for future in as_completed(tasks):
            item = future.result()
            if item:
                results.append(item)

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=True, indent=2)
    print(f"Wrote: {args.output} ({len(results)} issues)")


if __name__ == "__main__":
    main()
