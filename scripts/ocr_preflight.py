#!/usr/bin/env python3
"""Runtime preflight checks for OCR-backed editable PPT reconstruction."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

OCR_PYTHON_ENV_VARS = (
    "COMMERCIAL_PPT_OCR_PYTHON",
    "AI_PPT_OCR_PYTHON",
    "PPT_OCR_PYTHON",
    "OCR_RUNTIME_PYTHON",
)


def module_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def linux_cpu_flags() -> list[str]:
    if platform.system() != "Linux":
        return []
    cpuinfo = Path("/proc/cpuinfo")
    if not cpuinfo.exists():
        return []
    for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.lower().startswith("flags"):
            _key, _sep, value = line.partition(":")
            return value.strip().split()
    return []


def run_probe(code: str) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:
        return {"ok": False, "returncode": None, "detail": str(exc)}
    detail = (proc.stdout or proc.stderr or "").strip()
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "detail": detail}


def rapidocr_probe_code() -> str:
    return (
        "from PIL import Image\n"
        "import cv2\n"
        "try:\n"
        "    from rapidocr import RapidOCR\n"
        "except ImportError:\n"
        "    from rapidocr_onnxruntime import RapidOCR\n"
        "print('ok')"
    )


def recommended_backend() -> tuple[str | None, list[str], dict]:
    blockers: list[str] = []
    probes: dict[str, dict] = {}
    probes["paddle"] = run_probe("import paddle, paddleocr; print(paddle.__version__)")
    probes["rapidocr"] = run_probe(rapidocr_probe_code())

    flags = linux_cpu_flags()
    if platform.system() == "Linux" and module_exists("paddle") and "avx" not in flags:
        blockers.append("cpu_missing_avx_for_paddle")

    if probes["paddle"]["ok"]:
        return ("paddleocr", blockers, probes)
    if module_exists("paddle") and not probes["paddle"]["ok"]:
        detail = probes["paddle"]["detail"].lower()
        if probes["paddle"]["returncode"] == 132 or "illegal instruction" in detail:
            blockers.append("paddle_import_illegal_instruction")
        else:
            blockers.append("paddle_import_failed")

    if probes["rapidocr"]["ok"]:
        return ("rapidocr", blockers, probes)
    if (module_exists("rapidocr") or module_exists("rapidocr_onnxruntime")) and not probes["rapidocr"]["ok"]:
        blockers.append("rapidocr_import_failed")

    return (None, blockers, probes)


def build_report() -> dict:
    flags = linux_cpu_flags()
    backend, blockers, probes = recommended_backend()
    env_python = None
    for name in OCR_PYTHON_ENV_VARS:
        value = os.environ.get(name)
        if value:
            env_python = {"name": name, "value": value}
            break
    return {
        "python": {
            "executable": sys.executable,
            "version": sys.version.replace("\n", " "),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "cpu": {
            "flags": flags,
            "has_avx": "avx" in flags,
        },
        "modules": {
            "PIL": module_exists("PIL"),
            "pptx": module_exists("pptx"),
            "cv2": module_exists("cv2"),
            "paddle": module_exists("paddle"),
            "paddleocr": module_exists("paddleocr"),
            "rapidocr": module_exists("rapidocr"),
            "rapidocr_onnxruntime": module_exists("rapidocr_onnxruntime"),
        },
        "paths": {
            "python": shutil.which(Path(sys.executable).name),
            "resolved_python": str(Path(sys.executable).resolve()),
            "builder_script": str((SCRIPT_DIR / "build_editable_ppt_vision.py").resolve()),
        },
        "env": {
            "ocr_python": env_python,
        },
        "probes": probes,
        "recommended_backend": backend,
        "ready": backend is not None,
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight OCR runtime checks for editable PPT reconstruction.")
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    parser.add_argument("--require-ready", action="store_true", help="Exit non-zero when no OCR backend is usable.")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"python: {report['python']['executable']}")
        print(f"version: {report['python']['version']}")
        print(f"platform: {report['platform']['system']} {report['platform']['release']} {report['platform']['machine']}")
        print(f"recommended_backend: {report['recommended_backend'] or 'none'}")
        print(f"ready: {report['ready']}")
        if report["blockers"]:
            print("blockers:")
            for item in report["blockers"]:
                print(f"- {item}")
    return 0 if (report["ready"] or not args.require_ready) else 2


if __name__ == "__main__":
    raise SystemExit(main())
