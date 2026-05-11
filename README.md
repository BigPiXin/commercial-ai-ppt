# Commercial AI PPT Skill

AI-facing skill for producing commercial PowerPoint decks from user-provided solution content, documents, images, or product materials.

This repository is intentionally small. `SKILL.md` is the primary instruction file for AI agents. `references/` contains prompt templates that should be loaded only when needed. `scripts/` contains deterministic helpers for upload and editable PPT reconstruction.

## What This Skill Does

`commercial-ai-ppt` turns a long PPT production task into a gated, auditable workflow:

1. Plan the deck from the user's source material.
2. Ask the user to approve the chapter structure and full slide copy.
3. Generate text-overlaid slide images, or import slide images the user made elsewhere.
4. Ask the user to approve the generated or imported images.
5. Generate no-text slide backgrounds, or import clean backgrounds the user already has.
6. Rebuild an editable `.pptx` with clean backgrounds plus editable text layers.

The core design is: AI handles narrative, layout intent, and optional image generation; scripts handle repeatable file upload, OCR-assisted text extraction, layout reconstruction, and PPTX assembly.

## Repository Layout

```text
commercial-ai-ppt/
  SKILL.md
  README.md
  references/
    prompt-pack.md
  scripts/
    evolink_upload.py
    build_editable_ppt_vision.py
    vision_ocr.swift
```

## How AI Agents Should Use It

When the user asks to create, generate, design, rebuild, import, or convert a commercial PPT, load `SKILL.md` first and follow it as the top-level controller. Do not skip approval gates, but do choose the shortest valid entry mode when the user already has slide images.

Only load `references/prompt-pack.md` when entering image generation or model-driven clean-background generation. Do not copy the full prompt pack into every turn unless the current phase needs a model prompt.

Use the bundled scripts instead of rewriting equivalent logic:

- `scripts/evolink_upload.py` uploads local reference images through Evolink Files and returns temporary model-facing URLs.
- `scripts/build_editable_ppt_vision.py` rebuilds editable PowerPoint files from text-overlaid images and clean backgrounds.
- `scripts/vision_ocr.swift` provides an Apple Vision OCR backend for macOS.

## Core Workflow

Phase 1 is content planning. The AI reads the user's materials, extracts facts, drafts a slide-by-slide structure, writes the actual page copy, locks the deck language, and asks for user approval.

Phase 2 is slide image acquisition. After Phase 1 approval, or immediately when the user already has slide images, the AI creates the project directory and either generates slide images through the configured image model or imports user-supplied images made with GPT image tools, image2, Banana, Midjourney, designers, or other workflows. All accepted slide images are saved under `ppt/`, recorded in `MANIFEST.md`, and reviewed before reconstruction.

Phase 3 is editable reconstruction. After image approval, the AI generates no-text backgrounds under `ppt-clean/`, or imports matching user-supplied clean backgrounds, then runs `build_editable_ppt_vision.py` to create an editable PPTX under `ppt-editable/`.

## Important Guardrails

- Never skip user approval between phases.
- Never invent product facts, model names, customer claims, roadmap dates, or technical parameters.
- Preserve the deck language. Chinese source content defaults to Simplified Chinese unless the user says otherwise.
- Do not translate visible slide text into English just because the prompt template is written in English.
- Treat user-supplied slide images as first-class inputs; do not force image generation when images already exist.
- Use 16:9, 2K, medium quality, and `n=1` by default for image generation.
- Never use 4K unless the user explicitly asks.
- Never print, save, log, or commit API keys.
- Do not require Evolink for local image import or reconstruction. Use Evolink Files only when a remote image model needs temporary model-facing URLs.
- Always report resolved absolute output paths. Do not only say `~/Desktop/...`, `./ppt-projects/...`, `/ppt`, or `/ppt-clean`, because those paths may refer to the runtime workspace rather than the user's physical desktop.
- Keep generated project outputs outside this repository unless the user explicitly asks to commit examples.

## Expected Runtime Inputs

The skill does not include API keys. Runtime credentials should be provided by the host environment, profile, or secret manager.

Common optional environment variables:

```text
EVOLINK_API_KEY
EVOLINK_API_TOKEN
COMMERCIAL_PPT_OUTPUT_ROOT
AI_PPT_OUTPUT_ROOT
PPT_OUTPUT_ROOT
```

If an image provider key, upload key, quota, or model access is missing, stop and tell the user what is missing instead of silently switching providers.

No image-provider credential is required when the user supplies both text-overlaid slide images and matching clean no-text backgrounds for local reconstruction.

## Output Contract

A completed run should produce a project folder like:

```text
<project>/
  source/approved_plan.md
  source/imported_assets.md
  ppt/
  ppt-clean/
  ppt-editable/
  prompts/
  evolink_uploads.json
  MANIFEST.md
```

`MANIFEST.md` and the final response should include resolved absolute paths for the project directory, generated image folders, final PPTX path, validation status, and any known limitations.

## License

MIT License. See [LICENSE](LICENSE).
