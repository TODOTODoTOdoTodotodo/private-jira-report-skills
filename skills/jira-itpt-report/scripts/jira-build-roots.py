#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Build root key list from Jira source JSON.")
    parser.add_argument("input_json")
    parser.add_argument("output_txt")
    parser.add_argument("--prefix", default="MGTT-")
    args = parser.parse_args()

    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    keys = sorted({row.get("issue_key") for row in data if row.get("issue_key", "").startswith(args.prefix)})
    Path(args.output_txt).write_text("\n".join(keys) + ("\n" if keys else ""), encoding="utf-8")


if __name__ == "__main__":
    main()
