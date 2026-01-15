#!/usr/bin/env python3
import argparse
import json


def load(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser(description="Merge Jira source JSON files by issue_key.")
    parser.add_argument("base_json", help="Base JSON array")
    parser.add_argument("supplement_json", help="Supplement JSON array")
    parser.add_argument("output_json", help="Output JSON array")
    args = parser.parse_args()

    base = load(args.base_json)
    supplement = load(args.supplement_json)

    merged = {}
    for item in base:
        key = item.get("issue_key")
        if key:
            merged[key] = item
    for item in supplement:
        key = item.get("issue_key")
        if key and key not in merged:
            merged[key] = item

    with open(args.output_json, "w", encoding="utf-8") as handle:
        json.dump(list(merged.values()), handle, ensure_ascii=True, indent=2)


if __name__ == "__main__":
    main()
