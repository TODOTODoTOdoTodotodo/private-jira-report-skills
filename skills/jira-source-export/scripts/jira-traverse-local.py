#!/usr/bin/env python3
import argparse
import json
from collections import deque, defaultdict


def load_data(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    index = {}
    for item in data:
        key = item.get("issue_key")
        if key:
            index[key] = item
    return index


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


def traverse(index, root_key, max_depth):
    results = []
    missing = set()
    visited = set()
    queue = deque([(root_key, 0)])
    visited.add(root_key)

    while queue:
        current, depth = queue.popleft()
        issue = index.get(current)
        if not issue:
            missing.add(current)
            continue
        if depth >= max_depth:
            continue
        for nxt, relation in neighbors(issue):
            if nxt in visited:
                continue
            visited.add(nxt)
            to_project_key = (index.get(nxt) or {}).get("project_key")
            if not to_project_key:
                to_project_key = infer_project_key(nxt)
                if nxt not in index:
                    missing.add(nxt)
            results.append(
                {
                    "from_key": current,
                    "to_key": nxt,
                    "relation_type": relation,
                    "to_project_key": to_project_key,
                    "depth": depth + 1,
                }
            )
            queue.append((nxt, depth + 1))
    return results, missing


def main():
    parser = argparse.ArgumentParser(description="Traverse local Jira JSON graph.")
    parser.add_argument("input_json", help="Path to jira-source JSON file")
    parser.add_argument("root_key", help="Root issue key (e.g., MGTT-14108)")
    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--only-itpt", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--csv-output", default="")
    parser.add_argument("--batch-file", default="")
    parser.add_argument("--missing-output", default="")
    args = parser.parse_args()

    index = load_data(args.input_json)
    root_keys = []
    if args.batch_file:
        with open(args.batch_file, "r", encoding="utf-8") as handle:
            for line in handle:
                key = line.strip()
                if key:
                    root_keys.append(key)
    else:
        root_keys = [args.root_key]

    all_outputs = []
    for root_key in root_keys:
        edges, missing = traverse(index, root_key, args.max_depth)
        if args.only_itpt:
            edges = [e for e in edges if e.get("to_project_key") == "ITPT"]
        all_outputs.append({"root_key": root_key, "edges": edges, "missing_keys": sorted(missing)})

    if args.csv_output:
        import csv

        with open(args.csv_output, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["root_key", "from_key", "to_key", "relation_type", "to_project_key", "depth"])
            for item in all_outputs:
                root_key = item["root_key"]
                for edge in item["edges"]:
                    writer.writerow(
                        [
                            root_key,
                            edge.get("from_key"),
                            edge.get("to_key"),
                            edge.get("relation_type"),
                            edge.get("to_project_key"),
                            edge.get("depth"),
                        ]
                    )

    if args.missing_output:
        missing_all = []
        for item in all_outputs:
            missing_all.extend(item.get("missing_keys", []))
        with open(args.missing_output, "w", encoding="utf-8") as handle:
            for key in sorted(set(missing_all)):
                handle.write(f"{key}\n")

    if args.output or not args.csv_output:
        output = all_outputs if len(all_outputs) > 1 else all_outputs[0]
        if args.output:
            with open(args.output, "w", encoding="utf-8") as handle:
                json.dump(output, handle, ensure_ascii=True, indent=2)
        else:
            print(json.dumps(output, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
