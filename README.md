# Commercial AI PPT Skill

AI-facing skill for producing commercial PowerPoint decks from user-provided solution content, documents, images, or product materials.

This repository is intentionally small. `SKILL.md` is the primary instruction file for AI agents. `references/` contains prompt templates that should be loaded only when needed. `scripts/` contains deterministic helpers for upload and editable PPT reconstruction.

## What This Skill Does

`commercial-ai-ppt` turns a long PPT production task into a continuous, auditable workflow:

1. Plan the deck from the user's source material.
2. Save the chapter structure and full slide copy.
3. Generate text-overlaid slide images, or import slide images the user made elsewhere.
4. Generate no-text slide backgrounds, or import clean backgrounds the user already has.
5. Rebuild an editable `.pptx` with clean backgrounds plus editable text layers.

The core design is: AI handles narrative, layout intent, and optional image generation; scripts handle repeatable file upload, OCR-assisted text extraction, layout reconstruction, and PPTX assembly.

## Continuous Production Contract

This skill defaults to one production run:

- Plan content, save `source/approved_plan.md`, generate/import `ppt/` images, generate/import `ppt-clean/` backgrounds, and build the editable PPTX without stopping for default phase approvals.
- Stop only when required inputs are missing, credentials/quota are unavailable, a tool/provider fails, or the user explicitly asks for staged review.
- If staged review is requested, record the gate in `MANIFEST.md`; never rely on chat memory alone to resume production.

## Repository Layout

```text
commercial-ai-ppt/
  SKILL.md
  README.md
  references/
    prompt-pack.md
  scripts/
    ocr_preflight.py
    run_editable_ppt.py
    evolink_upload.py
    build_editable_ppt_vision.py
```

## How AI Agents Should Use It

When the user asks to create, generate, design, rebuild, import, or convert a commercial PPT, load `SKILL.md` first and follow it as the top-level controller. Choose the shortest valid entry mode when the user already has slide images.

Only load `references/prompt-pack.md` when entering image generation or model-driven clean-background generation. Do not copy the full prompt pack into every turn unless the current phase needs a model prompt.

Use the bundled scripts instead of rewriting equivalent logic:

- `scripts/ocr_preflight.py` checks whether the current runtime can actually run PaddleOCR or RapidOCR before Phase 3 starts.
- `scripts/run_editable_ppt.py` is the stable reconstruction entrypoint. It runs preflight, honors OCR-runtime Python overrides, and then launches the actual builder.
- `scripts/evolink_upload.py` uploads local reference images through Evolink Files and returns temporary model-facing URLs.
- `scripts/build_editable_ppt_vision.py` rebuilds editable PowerPoint files from text-overlaid images and clean backgrounds after the runtime is known to be usable.

Never replace `run_editable_ppt.py` or `build_editable_ppt_vision.py` with an ad-hoc `python-pptx` fallback. If the scripts are not found, resolve the skill path or stop with a clear missing-script error.

## Core Workflow

Phase 1 is content planning. The AI reads the user's materials, extracts facts, drafts a slide-by-slide structure, writes the actual page copy, locks the deck language, and saves the working plan.

Phase 2 is slide image acquisition. The AI either generates slide images through the configured image model or imports user-supplied images made with GPT image tools, image2, Banana, Midjourney, designers, or other workflows. All accepted slide images are saved under `ppt/` and recorded in `MANIFEST.md`.

Phase 3 is editable reconstruction. The AI generates no-text backgrounds under `ppt-clean/`, or imports matching user-supplied clean backgrounds, then runs `run_editable_ppt.py` to create an editable PPTX under `ppt-editable/`.

## Important Guardrails

- Do not insert phase approvals unless the user explicitly asks for staged review.
- Never ask whether generated Phase 2 images should be saved; save and validate them automatically.
- Treat clean-background generation plus editable PPTX reconstruction as one Phase 3 workflow.
- Never invent product facts, model names, customer claims, roadmap dates, or technical parameters.
- Preserve the deck language. Chinese source content defaults to Simplified Chinese unless the user says otherwise.
- Do not translate visible slide text into English just because the prompt template is written in English.
- Treat user-supplied slide images as first-class inputs; do not force image generation when images already exist.
- Use 16:9, 2K, medium quality, and `n=1` by default for image generation.
- Never use 4K unless the user explicitly asks.
- Never print, save, log, or commit API keys.
- Do not require Evolink for local image import or reconstruction. Use Evolink Files only when a remote image model needs temporary model-facing URLs.
- Treat remote image result URLs as temporary. Download generated slides to local `ppt/` immediately and use local files as the Phase 3 source of truth.
- Persist usable remote URL metadata in `remote_assets.json` and `MANIFEST.md`; Phase 3 should reuse Phase 2 generated image URLs while they are unexpired and validated, then refresh them from local files only when needed.
- Do not upload generated `ppt/` images before checking cached Phase 2 URLs. Missing Evolink upload credentials are not a blocker when valid generated result URLs already exist.
- Use failure-aware downloads and image validation; unchecked `curl -sL` / `curl -s -o` is not enough because 404/403 responses must stop the workflow. For Evolink result URLs, use `curl -fL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 180 -A "Mozilla/5.0" ...` or equivalent checked code.
- Always report resolved absolute output paths. Do not only say `~/Desktop/...`, `./ppt-projects/...`, `/ppt`, or `/ppt-clean`, because those paths may refer to the runtime workspace rather than the user's physical desktop.
- Do not claim that files were checked, generated, or executed unless actual tool calls produced or verified them.
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
COMMERCIAL_PPT_PUBLIC_BASE_URL
AI_PPT_PUBLIC_BASE_URL
PPT_PUBLIC_BASE_URL
COMMERCIAL_PPT_OCR_PYTHON
AI_PPT_OCR_PYTHON
PPT_OCR_PYTHON
OCR_RUNTIME_PYTHON
```

If an image provider key, upload key, quota, or model access is missing, stop and tell the user what is missing instead of silently switching providers.

No image-provider credential is required when the user supplies both text-overlaid slide images and matching clean no-text backgrounds for local reconstruction.

For Phase 3 reconstruction, run preflight first:

```bash
python scripts/ocr_preflight.py
python scripts/ocr_preflight.py --json --require-ready
```

For a split-runtime deployment, point the reconstruction entrypoint at a dedicated OCR interpreter:

```bash
export COMMERCIAL_PPT_OCR_PYTHON=/absolute/path/to/ocr-runtime/bin/python
```

Install the OCR/PPT stack into that interpreter when needed:

```bash
python -m pip install python-pptx pillow paddlepaddle paddleocr opencv-python-headless
# fallback:
python -m pip install python-pptx pillow rapidocr_onnxruntime opencv-python-headless
```

Use the stable launcher for reconstruction:

```bash
python scripts/run_editable_ppt.py --base /path/to/project --output demo_editable.pptx
```

The reconstruction script can also use precomputed OCR JSON via `--ocr-backend json --ocr-json-dir <dir>` when a runtime cannot install OCR dependencies.

## Compatibility Notes

- The skill is designed to stay portable across macOS, Linux, Windows, local workspaces, containers, and SSH hosts.
- OCR backend choice is runtime-dependent, not repository-dependent. A machine that can import PaddleOCR should use it; a machine that cannot should fall back to RapidOCR; a machine that cannot run either should use precomputed JSON.
- PaddleOCR compatibility depends on more than `pip install`. Real usability depends on the Python version, platform wheel availability, and CPU features exposed by the host or VM.
- The repository should be treated as compatible with multiple OCR backends and multiple Python runtimes. Do not assume the Hermes main interpreter is always the right OCR interpreter.

## Compatibility Matrix

| Environment | Recommended OCR | Notes |
| --- | --- | --- |
| macOS local workstation | `paddleocr` when importable, else `rapidocr` | Good default for creator workflows. Use a separate OCR Python if the main agent Python lacks OCR wheels. |
| Linux server with AVX and supported Paddle wheel | `paddleocr` | Best quality path for CPU-only deployments when the host can actually import Paddle. |
| Linux server without AVX or with incompatible Paddle wheel | `rapidocr` | Most portable server fallback. This is common in VMs and constrained cloud instances. |
| Windows workstation/server | `paddleocr` when importable, else `rapidocr` | Keep OCR runtime separate from the main agent Python when wheel availability differs. |
| Any host with no working OCR runtime | `json` | Use precomputed OCR JSON and skip live OCR entirely. |

`run_editable_ppt.py` writes an `OCR Runtime` section into `MANIFEST.md`, so every output folder records which Python and which backend were actually used.

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
  remote_assets.json
  evolink_uploads.json
  MANIFEST.md
```

`MANIFEST.md` and the final response should include resolved absolute paths for the project directory, generated image folders, final PPTX path, validation status, any known limitations, and the OCR runtime section written by `run_editable_ppt.py`.

If a deployment sets a public base URL environment variable, the agent should report both the filesystem path and the public URL. The repository does not hardcode server-specific hostnames or nginx paths.

## License

MIT License. See [LICENSE](LICENSE).
