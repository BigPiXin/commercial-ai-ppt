#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from typing import Any


SUCCESS_STATUSES = {"succeeded", "completed", "success", "done", "finished"}
PENDING_STATUSES = {"queued", "pending", "running", "processing", "in_progress", "submitted"}
FAILED_STATUSES = {"failed", "error", "cancelled", "canceled", "timeout", "expired"}
URL_KEYS = {"url", "file_url", "download_url", "image_url"}


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def collect_urls(payload: Any) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for item in walk(payload):
        for key in URL_KEYS:
            val = item.get(key)
            if isinstance(val, str) and val.startswith(("http://", "https://")):
                if val not in seen:
                    seen.add(val)
                    urls.append(val)
    return urls


def collect_statuses(payload: Any) -> list[str]:
    statuses: list[str] = []
    for item in walk(payload):
        for key in ("status", "state"):
            val = item.get(key)
            if isinstance(val, str):
                statuses.append(val.strip().lower())
    return statuses


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract terminal image result URLs from OpenAI-compatible or provider-specific async responses."
    )
    parser.add_argument("json_file", nargs="?", help="JSON response file. Reads stdin when omitted.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-success", action="store_true")
    args = parser.parse_args()

    raw = open(args.json_file, encoding="utf-8").read() if args.json_file else sys.stdin.read()
    payload = json.loads(raw)
    statuses = collect_statuses(payload)
    urls = collect_urls(payload)

    has_failure = any(status in FAILED_STATUSES for status in statuses)
    has_success = any(status in SUCCESS_STATUSES for status in statuses)
    has_pending = any(status in PENDING_STATUSES for status in statuses)

    if has_failure:
        state = "failed"
    elif has_success and urls:
        state = "succeeded"
    elif has_pending:
        state = "pending"
    elif urls:
        state = "succeeded"
    else:
        state = "unknown"

    result = {
        "state": state,
        "statuses": statuses,
        "urls": urls,
        "primary_url": urls[0] if urls else None,
        "success": state == "succeeded",
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["primary_url"]:
            print(result["primary_url"])
        else:
            print(state)

    if args.require_success and not result["success"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
