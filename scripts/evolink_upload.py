#!/usr/bin/env python3
"""Upload local images or remote URLs to Evolink Files and emit public file URLs.

The script uses only Python standard library modules. Local files are uploaded
through the stream endpoint first, then retried through Base64 if the provider
edge rejects multipart upload in a constrained runtime.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


FILES_API_BASE = "https://files-api.evolink.ai/api/v1/files/upload"


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def request_json(endpoint: str, token: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "commercial-ai-ppt/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Evolink upload failed: HTTP {exc.code}: {body}") from exc


def upload_local_base64(path: Path, token: str, upload_path: str | None) -> dict:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    payload = {
        "base64_data": f"data:{mime_type};base64,{encoded}",
        "file_name": path.name,
    }
    if upload_path:
        payload["upload_path"] = upload_path
    return request_json(f"{FILES_API_BASE}/base64", token, payload)


def request_multipart(endpoint: str, token: str, fields: dict[str, str | None], file_field: str, path: Path) -> dict:
    boundary = f"----commercial-ai-ppt-{int(time.time() * 1000)}"
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    chunks: list[bytes] = []
    for name, value in fields.items():
        if value is None:
            continue
        chunks.extend([
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
            str(value).encode("utf-8"),
            b"\r\n",
        ])
    chunks.extend([
        f"--{boundary}\r\n".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{path.name}"\r\n'
        ).encode("utf-8"),
        f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
        path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ])
    req = urllib.request.Request(
        endpoint,
        data=b"".join(chunks),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "commercial-ai-ppt/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Evolink stream upload failed: HTTP {exc.code}: {body}") from exc


def upload_local_stream(path: Path, token: str, upload_path: str | None) -> dict:
    fields = {"file_name": path.name, "upload_path": upload_path}
    return request_multipart(f"{FILES_API_BASE}/stream", token, fields, "file", path)


def upload_remote_url(url: str, token: str, upload_path: str | None, file_name: str | None) -> dict:
    payload = {"file_url": url}
    if upload_path:
        payload["upload_path"] = upload_path
    if file_name:
        payload["file_name"] = file_name
    return request_json(f"{FILES_API_BASE}/url", token, payload)


def normalize_result(source: str, result: dict) -> dict:
    if not result.get("success"):
        raise RuntimeError(f"Evolink upload failed for {source}: {json.dumps(result, ensure_ascii=False)}")
    data = result.get("data") or {}
    return {
        "source": source,
        "file_id": data.get("file_id"),
        "file_name": data.get("file_name"),
        "mime_type": data.get("mime_type"),
        "file_size": data.get("file_size"),
        "file_url": data.get("file_url"),
        "download_url": data.get("download_url"),
        "expires_at": data.get("expires_at"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload images to Evolink Files and output file_url mappings.")
    parser.add_argument("inputs", nargs="+", help="Local image paths or public HTTP(S) URLs.")
    parser.add_argument("--upload-path", default=None, help="Optional Evolink upload_path, e.g. project-id/ppt.")
    parser.add_argument("--manifest", default=None, help="Optional JSON file to write upload results.")
    parser.add_argument("--token-env", default="EVOLINK_API_KEY", help="Env var containing the Evolink API key.")
    args = parser.parse_args()

    token = os.getenv(args.token_env) or os.getenv("EVOLINK_API_TOKEN")
    if not token:
        raise SystemExit(f"Missing Evolink token. Set {args.token_env} or EVOLINK_API_TOKEN.")

    records = []
    for item in args.inputs:
        print(f"Uploading {item}", file=sys.stderr, flush=True)
        if is_url(item):
            result = upload_remote_url(item, token, args.upload_path, None)
        else:
            path = Path(item).expanduser().resolve()
            if not path.exists():
                raise FileNotFoundError(path)
            try:
                result = upload_local_stream(path, token, args.upload_path)
            except RuntimeError as exc:
                print(f"Stream upload failed, retrying Base64 upload: {exc}", file=sys.stderr, flush=True)
                result = upload_local_base64(path, token, args.upload_path)
        record = normalize_result(item, result)
        records.append(record)
        print(record["file_url"], flush=True)
        time.sleep(0.2)

    output = {"uploaded": records}
    if args.manifest:
        manifest_path = Path(args.manifest).expanduser().resolve()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
