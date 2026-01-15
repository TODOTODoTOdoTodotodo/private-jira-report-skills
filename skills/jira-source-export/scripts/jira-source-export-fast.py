#!/usr/bin/env python3
import argparse
import base64
import concurrent.futures as futures
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


def extract_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if value.get("type") == "text":
            return value.get("text", "")
        parts = []
        for item in value.get("content", []) or []:
            parts.append(extract_text(item))
        return "".join(parts)
    if isinstance(value, list):
        return "".join(extract_text(item) for item in value)
    return ""


def summarize_text(text, limit=None):
    max_len = int(get_env("DESCRIPTION_MAX_LEN", "280"))
    if limit is not None:
        max_len = limit
    cleaned = " ".join(str(text).split())
    if not cleaned:
        return ""
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


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
            existing = os.environ.get(env_key)
            if not existing:
                os.environ[env_key] = env_value


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
        self.timeout = int(get_env("HTTP_TIMEOUT", "30"))

    def _request(self, url, params=None):
        if params:
            url = url + "?" + urllib.parse.urlencode(params, doseq=True)
        attempt = 0
        backoff = self.backoff
        while True:
            req = urllib.request.Request(url, headers=self.headers)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
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

    def search_with_fields(self, jql, fields, start_at=0, max_results=100):
        return self._request(
            f"{self.base_url}/rest/api/3/search/jql",
            {
                "jql": jql,
                "fields": ",".join(fields),
                "startAt": str(start_at),
                "maxResults": str(max_results),
            },
        )

    def issue(self, key, fields):
        return self._request(
            f"{self.base_url}/rest/api/3/issue/{key}",
            {"fields": ",".join(fields)},
        )

    def comments(self, key, start_at=0, max_results=100):
        return self._request(
            f"{self.base_url}/rest/api/3/issue/{key}/comment",
            {"startAt": str(start_at), "maxResults": str(max_results)},
        )

    def myself(self):
        return self._request(f"{self.base_url}/rest/api/3/myself")


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


def paginate_search_with_fields(client, jql, max_results, fields, max_pages=0):
    issues = []
    start_at = 0
    pages = 0
    while True:
        resp = client.search_with_fields(jql, fields, start_at=start_at, max_results=max_results)
        page = resp.get("issues", [])
        issues.extend(page)
        total = resp.get("total")
        pages += 1
        if max_pages and pages >= max_pages:
            break
        if isinstance(total, int):
            start_at += max_results
            if start_at >= total:
                break
        else:
            if len(page) < max_results:
                break
            start_at += max_results
    return issues


def comment_match(client, key, account_ids, author_names, start_ts, end_ts):
    start_at = 0
    max_results = 100
    while True:
        resp = client.comments(key, start_at=start_at, max_results=max_results)
        comments = resp.get("comments", [])
        for comment in comments:
            author = comment.get("author", {})
            account = author.get("accountId") or ""
            name = author.get("displayName") or ""
            if account_ids and account not in account_ids and name not in author_names:
                continue
            created = comment.get("created")
            if created and start_ts <= created < end_ts:
                return True
        total = resp.get("total")
        if isinstance(total, int):
            start_at += max_results
            if start_at >= total:
                break
        else:
            if len(comments) < max_results:
                break
            start_at += max_results
    return False


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
    description = fields.get("description")
    description_text = extract_text(description)
    description_summary = summarize_text(description_text)
    return {
        "issue_key": issue.get("key"),
        "summary": fields.get("summary"),
        "description": description_text,
        "description_summary": description_summary,
        "project_key": (fields.get("project") or {}).get("key"),
        "issuetype": (fields.get("issuetype") or {}).get("name"),
        "parent_key": (fields.get("parent") or {}).get("key"),
        "issuelinks": issuelinks,
    }


def fetch_issue(client, key):
    issue = client.issue(
        key,
        ["summary", "description", "issuetype", "project", "parent", "issuelinks"],
    )
    return normalize_issue(issue)


def main():
    parser = argparse.ArgumentParser(description="Fast Jira source export.")
    parser.add_argument("output", nargs="?", default="jira-source.json")
    args = parser.parse_args()

    load_env_file(get_env("ENV_FILE", ""))

    base_url = get_env("JIRA_BASE_URL", required=True)
    email = get_env("JIRA_EMAIL", required=True)
    token = get_env("JIRA_API_TOKEN", required=True)
    projects = get_env("PROJECTS", "")
    jql_extra = get_env("JQL_EXTRA", "")
    match_mode = get_env("MATCH_MODE", "any")
    max_results = int(get_env("MAX_RESULTS", "100"))
    max_pages = int(get_env("MAX_PAGES", "0"))
    max_issues = int(get_env("MAX_ISSUES", "0"))
    concurrency = int(get_env("CONCURRENCY", "8"))

    start_date, end_date, start_ts, end_ts = build_date_range()
    no_date_filter = get_env("NO_DATE_FILTER", "")
    if no_date_filter and no_date_filter != "0":
        start_date = "1970/01/01"
        end_date = "2100/01/01"
        start_ts = "1970-01-01T00:00:00.000+0000"
        end_ts = "2100-01-01T00:00:00.000+0000"

    client = JiraClient(base_url, email, token)
    account_id = get_env("JIRA_ACCOUNT_ID", "")
    if not account_id:
        account_id = client.myself().get("accountId")
        if not account_id:
            raise SystemExit("Failed to resolve accountId from /myself.")
    author_names = set()
    display_names = get_env("COMMENT_AUTHOR_DISPLAY", "")
    if display_names:
        author_names.update(
            {name.strip() for name in display_names.split(",") if name.strip()}
        )
    if not author_names:
        display_name = get_env("JIRA_DISPLAY_NAME", "")
        if display_name:
            author_names.add(display_name)
    account_ids = {account_id} if account_id else set()

    comment_jql = f'updated >= "{start_date}" AND updated < "{end_date}"'
    assignee_jql = f'assignee WAS currentUser() DURING ("{start_date}","{end_date}")'
    comment_override = get_env("COMMENT_JQL", "")
    comment_template = get_env("COMMENT_JQL_TEMPLATE", "")
    comment_match_enabled = get_env("COMMENT_MATCH", "0") != "0"
    if projects:
        project_list = [p.strip() for p in projects.split(",") if p.strip()]
        project_filter = "project in (" + ", ".join(project_list) + ")"
        comment_jql += f" AND {project_filter}"
        assignee_jql += f" AND {project_filter}"
    if jql_extra:
        comment_jql += f" AND {jql_extra}"
        assignee_jql += f" AND {jql_extra}"

    if comment_template:
        comment_jql = comment_template.format(start_date=start_date, end_date=end_date)
        if projects:
            comment_jql += f" AND {project_filter}"
        if jql_extra:
            comment_jql += f" AND {jql_extra}"
    elif comment_override:
        comment_jql = comment_override
        if projects:
            comment_jql += f" AND {project_filter}"
        if jql_extra:
            comment_jql += f" AND {jql_extra}"

    assignee_override = get_env("ASSIGNEE_JQL", "")
    if assignee_override:
        assignee_jql = assignee_override

    if match_mode not in ("any", "comment", "assignee", "both"):
        raise SystemExit("MATCH_MODE must be one of: any, comment, assignee, both.")

    print(f"date range: {start_date} to {end_date}")
    print(f"match mode: {match_mode}")

    comment_candidates = []
    assignee_keys = []
    if match_mode in ("any", "comment", "both"):
        comment_candidates = paginate_search(client, comment_jql, max_results, max_pages)
    if match_mode in ("any", "assignee", "both"):
        assignee_keys = paginate_search(client, assignee_jql, max_results, max_pages)

    comment_matches = []
    comment_results = []
    if match_mode in ("any", "comment", "both"):
        if not comment_match_enabled:
            comment_issues = paginate_search_with_fields(
                client,
                comment_jql,
                max_results,
                ["summary", "description", "issuetype", "project", "parent", "issuelinks"],
                max_pages,
            )
            comment_results = [normalize_issue(issue) for issue in comment_issues]
            comment_matches = [item.get("issue_key") for item in comment_results if item.get("issue_key")]
        else:
            with futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                tasks = {
                    pool.submit(
                        comment_match, client, key, account_ids, author_names, start_ts, end_ts
                    ): key
                    for key in comment_candidates
                }
                for future in futures.as_completed(tasks):
                    key = tasks[future]
                    if future.result():
                        comment_matches.append(key)

    if match_mode == "comment":
        final_keys = sorted(set(comment_matches))
    elif match_mode == "assignee":
        final_keys = sorted(set(assignee_keys))
    elif match_mode == "both":
        final_keys = sorted(set(comment_matches).intersection(assignee_keys))
    else:
        final_keys = sorted(set(comment_matches).union(assignee_keys))

    results = []
    if match_mode == "assignee":
        issues = paginate_search_with_fields(
            client,
            assignee_jql,
            max_results,
            ["summary", "description", "issuetype", "project", "parent", "issuelinks"],
            max_pages,
        )
        results = [normalize_issue(issue) for issue in issues]
    elif match_mode == "comment" and not comment_match_enabled:
        results = comment_results
    elif match_mode in ("any", "both") and not comment_match_enabled:
        assignee_issues = paginate_search_with_fields(
            client,
            assignee_jql,
            max_results,
            ["summary", "description", "issuetype", "project", "parent", "issuelinks"],
            max_pages,
        )
        assignee_results = [normalize_issue(issue) for issue in assignee_issues]
        by_key = {item.get("issue_key"): item for item in comment_results if item.get("issue_key")}
        for item in assignee_results:
            key = item.get("issue_key")
            if not key:
                continue
            if match_mode == "both" and key not in comment_matches:
                continue
            if key not in by_key:
                by_key[key] = item
        results = list(by_key.values())
    else:
        with futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            if max_issues:
                final_keys = final_keys[:max_issues]
            tasks = {pool.submit(fetch_issue, client, key): key for key in final_keys}
            for future in futures.as_completed(tasks):
                results.append(future.result())

    if max_issues:
        results = results[:max_issues]

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=True, indent=2)

    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
