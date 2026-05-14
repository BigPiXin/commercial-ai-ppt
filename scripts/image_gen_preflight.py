#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


KNOWN_KEY_VARS = [
    "IMAGE2_API_KEY",
    "IMAGE_GEN_API_KEY",
    "IMAGE_GENERATION_API_KEY",
]

KNOWN_BASE_URL_VARS = [
    "IMAGE2_BASE_URL",
    "IMAGE_GEN_BASE_URL",
    "IMAGE_GENERATION_BASE_URL",
    "OPENAI_BASE_URL",
    "XIAOMI_BASE_URL",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _nested_get(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _bool_flag(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def detect_generation_route(config: dict[str, Any]) -> dict[str, Any]:
    routes: list[dict[str, str]] = []

    image_provider = str(_nested_get(config, "image_gen", "provider") or "").strip()
    image_model = str(_nested_get(config, "image_gen", "model") or "").strip()

    if image_provider and image_provider.lower() not in {"none", "disabled", "auto"}:
        routes.append(
            {
                "kind": "config.image_gen",
                "provider": image_provider,
                "detail": image_model or "(model unset)",
            }
        )

    for key_var in KNOWN_KEY_VARS:
        if os.getenv(key_var, "").strip():
            routes.append(
                {
                    "kind": "env.api_key",
                    "provider": key_var,
                    "detail": "present",
                }
            )

    if (
        os.getenv("OPENAI_API_KEY", "").strip()
        and os.getenv("OPENAI_BASE_URL", "").strip()
        and (
            os.getenv("OPENAI_IMAGE_MODEL", "").strip()
            or os.getenv("IMAGE_GEN_MODEL", "").strip()
            or os.getenv("IMAGE2_MODEL", "").strip()
        )
    ):
        routes.append(
            {
                "kind": "openai-compatible",
                "provider": "OPENAI_BASE_URL + OPENAI_API_KEY + image model",
                "detail": "present",
            }
        )

    if (
        os.getenv("XIAOMI_BASE_URL", "").strip()
        and (os.getenv("XIAOMI_API_KEY", "").strip() or os.getenv("MIMO_API_KEY", "").strip())
        and (
            os.getenv("XIAOMI_IMAGE_MODEL", "").strip()
            or os.getenv("IMAGE_GEN_MODEL", "").strip()
            or os.getenv("IMAGE2_MODEL", "").strip()
        )
    ):
        routes.append(
            {
                "kind": "openai-compatible",
                "provider": "XIAOMI_BASE_URL + XIAOMI_API_KEY/MIMO_API_KEY + image model",
                "detail": "present",
            }
        )

    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, str]] = []
    for route in routes:
        sig = (route["kind"], route["provider"], route["detail"])
        if sig in seen:
            continue
        seen.add(sig)
        deduped.append(route)

    return {
        "available": bool(deduped),
        "routes": deduped,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    hermes_home = Path(
        os.getenv("HERMES_HOME", str(Path.home() / ".hermes"))
    ).expanduser()
    config = _load_yaml(hermes_home / "config.yaml")
    route = detect_generation_route(config)

    user_images_present = args.user_images_present
    user_backgrounds_present = args.user_backgrounds_present

    generation_required = args.mode == "full-production"
    if args.mode == "byo-images":
        generation_required = not user_backgrounds_present
    elif args.mode in {"byo-backgrounds", "reconstruction-only"}:
        generation_required = False

    ready = True
    blockers: list[str] = []
    next_action = "continue"

    if args.mode == "full-production":
        if not route["available"]:
            ready = False
            next_action = "ask_user_for_generation_config"
            blockers.append(
                "Full production requires a callable image generation route."
            )
        if user_images_present:
            blockers.append(
                "User images are already present; the agent may switch only if the user explicitly asked for bring-your-own-images mode."
            )

    if args.mode == "byo-images" and not user_images_present:
        ready = False
        next_action = "ask_user_for_images_or_generation_config"
        blockers.append(
            "Bring-your-own-images mode requires user-supplied slide images."
        )

    if args.mode == "byo-backgrounds" and not (user_images_present and user_backgrounds_present):
        ready = False
        next_action = "ask_user_for_missing_assets"
        blockers.append(
            "Bring-your-own-backgrounds mode requires both slide images and matching clean backgrounds."
        )

    if args.mode == "reconstruction-only" and not user_images_present:
        ready = False
        next_action = "ask_user_for_images"
        blockers.append(
            "Reconstruction-only mode requires existing slide images."
        )

    if generation_required and route["available"]:
        next_action = "continue_with_generation"

    return {
        "ready": ready,
        "requested_mode": args.mode,
        "generation_required": generation_required,
        "generation_route_available": route["available"],
        "detected_routes": route["routes"],
        "user_images_present": user_images_present,
        "user_backgrounds_present": user_backgrounds_present,
        "hermes_home": str(hermes_home),
        "config_path": str(hermes_home / "config.yaml"),
        "next_action": next_action,
        "blockers": blockers,
        "user_message": (
            "Missing image generation route. Ask the user to provide image2/built-in image tool/provider+base_url+key, or explicitly switch to bring-your-own-images mode."
            if not ready and args.mode == "full-production"
            else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight full-production image generation requirements for ppt-helper."
    )
    parser.add_argument(
        "--mode",
        choices=[
            "full-production",
            "byo-images",
            "byo-backgrounds",
            "reconstruction-only",
        ],
        default="full-production",
    )
    parser.add_argument("--user-images-present", action="store_true")
    parser.add_argument("--user-backgrounds-present", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()

    report = build_report(args)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ready={report['ready']}")
        print(f"requested_mode={report['requested_mode']}")
        print(f"generation_required={report['generation_required']}")
        print(f"generation_route_available={report['generation_route_available']}")
        print(f"next_action={report['next_action']}")
        if report["detected_routes"]:
            print("detected_routes:")
            for route in report["detected_routes"]:
                print(f"  - {route['kind']}: {route['provider']} ({route['detail']})")
        if report["blockers"]:
            print("blockers:")
            for blocker in report["blockers"]:
                print(f"  - {blocker}")
        if report["user_message"]:
            print(f"user_message={report['user_message']}")

    if args.require_ready and not report["ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
