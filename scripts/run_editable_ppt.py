#!/usr/bin/env python3
"""Launch editable PPT reconstruction with an explicit OCR runtime."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PREFLIGHT_SCRIPT = SCRIPT_DIR / "ocr_preflight.py"
BUILD_SCRIPT = SCRIPT_DIR / "build_editable_ppt_vision.py"
OCR_PYTHON_ENV_VARS = (
    "COMMERCIAL_PPT_OCR_PYTHON",
    "AI_PPT_OCR_PYTHON",
    "PPT_OCR_PYTHON",
    "OCR_RUNTIME_PYTHON",
)

MANIFEST_START = "<!-- OCR_PREFLIGHT_START -->"
MANIFEST_END = "<!-- OCR_PREFLIGHT_END -->"


def resolve_ocr_python(cli_value: str | None) -> str:
    if cli_value:
        return cli_value
    for name in OCR_PYTHON_ENV_VARS:
        value = os.environ.get(name)
        if value:
            return value
    return sys.executable


def format_probe_line(name: str, probe: dict) -> str:
    status = "ok" if probe.get("ok") else "failed"
    detail = str(probe.get("detail") or "").strip()
    if detail:
        detail = detail.replace("\n", " | ")
        return f"- `{name}`: `{status}` - {detail}"
    return f"- `{name}`: `{status}`"


def build_manifest_section(
    *,
    report: dict,
    ocr_python: str,
    requested_backend: str,
    effective_backend: str | None,
) -> str:
    lines = [
        MANIFEST_START,
        "## OCR Runtime",
        f"- `recorded_at`: `{datetime.now(timezone.utc).isoformat()}`",
        f"- `ocr_python`: `{ocr_python}`",
        f"- `python_version`: `{report['python']['version']}`",
        f"- `platform`: `{report['platform']['system']} {report['platform']['release']} {report['platform']['machine']}`",
        f"- `requested_backend`: `{requested_backend}`",
        f"- `recommended_backend`: `{report.get('recommended_backend') or 'none'}`",
        f"- `effective_backend`: `{effective_backend or 'none'}`",
        f"- `ready`: `{report.get('ready')}`",
    ]
    cpu = report.get("cpu") or {}
    if report["platform"]["system"] == "Linux":
        lines.append(f"- `cpu_has_avx`: `{cpu.get('has_avx')}`")
    env_python = (report.get("env") or {}).get("ocr_python")
    if env_python:
        lines.append(f"- `ocr_python_env`: `{env_python['name']}={env_python['value']}`")
    blockers = report.get("blockers") or []
    if blockers:
        lines.append(f"- `blockers`: `{', '.join(blockers)}`")
    else:
        lines.append("- `blockers`: `none`")
    lines.append("- `probes`:")
    for name, probe in (report.get("probes") or {}).items():
        lines.append(format_probe_line(name, probe))
    lines.append(MANIFEST_END)
    return "\n".join(lines) + "\n"


def write_manifest_section(base: Path, section: str) -> None:
    manifest_path = base / "MANIFEST.md"
    existing = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""
    start = existing.find(MANIFEST_START)
    end = existing.find(MANIFEST_END)
    if start != -1 and end != -1 and end > start:
        end += len(MANIFEST_END)
        updated = existing[:start].rstrip() + "\n\n" + section
        tail = existing[end:].lstrip()
        if tail:
            updated += "\n" + tail
    else:
        updated = existing.rstrip()
        if updated:
            updated += "\n\n"
        updated += section
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run editable PPT reconstruction with OCR runtime preflight.")
    parser.add_argument("--base", default=".", help="Project directory containing ppt/ and ppt-clean/")
    parser.add_argument("--output", default="editable_ocr_gradient.pptx", help="Output pptx filename")
    parser.add_argument("--ocr-backend", default="auto", choices=("auto", "paddleocr", "rapidocr", "json"))
    parser.add_argument("--ocr-json-dir", default=None, help="Directory of precomputed OCR JSON files for --ocr-backend=json")
    parser.add_argument("--font", default=None, help="PPT font name, e.g. PingFang SC or Microsoft YaHei")
    parser.add_argument("--style-overrides", default=None, help="Optional style override JSON file")
    parser.add_argument("--ocr-python", default=None, help="Explicit Python interpreter for OCR/PPT rebuild runtime")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip OCR runtime preflight checks")
    args = parser.parse_args()

    ocr_python = resolve_ocr_python(args.ocr_python)
    base = Path(args.base).expanduser().resolve()
    report = None
    if not args.skip_preflight:
        preflight_proc = subprocess.run(
            [ocr_python, str(PREFLIGHT_SCRIPT), "--json", "--require-ready"],
            capture_output=True,
            text=True,
            check=False,
        )
        if preflight_proc.returncode != 0:
            message = (preflight_proc.stdout or preflight_proc.stderr).strip()
            raise SystemExit(f"OCR preflight failed for {ocr_python}\n{message}")
        report = json.loads(preflight_proc.stdout)
        if args.ocr_backend == "auto" and not report.get("recommended_backend"):
            raise SystemExit(f"OCR preflight found no usable backend for {ocr_python}")
    else:
        preflight_proc = subprocess.run(
            [ocr_python, str(PREFLIGHT_SCRIPT), "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if preflight_proc.returncode == 0:
            report = json.loads(preflight_proc.stdout)

    effective_backend = args.ocr_backend
    if args.ocr_backend == "auto" and report:
        effective_backend = report.get("recommended_backend") or "auto"
    if report:
        section = build_manifest_section(
            report=report,
            ocr_python=ocr_python,
            requested_backend=args.ocr_backend,
            effective_backend=effective_backend,
        )
        write_manifest_section(base, section)

    cmd = [
        ocr_python,
        str(BUILD_SCRIPT),
        "--base",
        str(base),
        "--output",
        args.output,
        "--ocr-backend",
        effective_backend,
    ]
    if args.ocr_json_dir:
        cmd.extend(["--ocr-json-dir", args.ocr_json_dir])
    if args.font:
        cmd.extend(["--font", args.font])
    if args.style_overrides:
        cmd.extend(["--style-overrides", args.style_overrides])
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
