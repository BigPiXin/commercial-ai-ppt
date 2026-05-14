---
name: ppt-helper
description: "Use when the user asks to create, generate, write, design, import, or rebuild a PowerPoint deck, proposal deck, solution presentation, pitch deck, slide images, no-text backgrounds, or editable PPT from text, documents, images, or product materials. This skill supports both automated image generation and bring-your-own-image workflows, then rebuilds editable PPT output through clean backgrounds and text-layer reconstruction."
---

# PPT Helper

This skill turns user-provided solution content, product materials, documents, images, or rough requirements into a production-ready PPT workflow. It is a composite workflow: use specialized skills/tools as needed, but keep this skill as the top-level controller.

## Core Contract

Default to one continuous production run.

1. Plan the deck narrative, outline, and final slide-by-slide copy.
2. Create the local project folder and save the plan as `source/approved_plan.md`.
3. Generate or import text-overlaid slide images into `/ppt`.
4. Generate or import no-text backgrounds into `/ppt-clean`.
5. Rebuild the editable PPTX with this skill's bundled image-to-PPT script.
6. Validate the PPTX and report final artifacts.

Stop mid-run only when required inputs are missing, credentials/quota are unavailable, a tool or provider fails in a way that cannot be retried safely, or the user explicitly asks for review gates. Do not require Evolink or any image provider for local image import; require provider credentials only when a remote generation, editing, upload, or clean-background model call is actually needed.

Hard stop rule: if the user asks this skill to create a PPT from source material and has not supplied finished slide images, the workflow is full production. Full production must not continue unless a callable image-generation route is available. If no route is available, stop and guide the user toward the next actionable choice: provide an OpenAI-compatible image-generation URL/key/model so the agent can initialize the route, or provide already-generated slide images so the agent can import them and rebuild the PPT. Do not create a PPTX with `python-pptx`, HTML, SVG, Markdown, or local drawing code as a substitute for missing generated slide images.

Forbidden fallback sentence: never say or do "image generation is unavailable, so I will switch to bring-your-own-images mode" unless the user actually supplied slide image files or URLs. Missing image generation means stop, not substitute.

## Continuous State Machine

Treat phases as internal progress states, not conversational approval gates.

Allowed transitions:

- `draft_plan` -> `phase2_images`: after the plan and slide copy are written to `source/approved_plan.md`.
- `phase2_images` -> `phase3_ppt`: after all text-overlaid slide images are generated/imported, saved to `/ppt`, validated, and recorded.
- `phase3_ppt` -> `done`: after clean backgrounds and editable PPTX are both complete.

Forbidden transitions:

- Do not present Phase 1/2/3 as default menu choices or ask the user to approve each phase unless the user explicitly requested staged review.
- Do not ask whether generated images should be saved; saving is mandatory.
- Do not ask the user to choose between "generate backgrounds" and "package PPTX"; Phase 3 includes both steps.
- Do not infer that a file was generated, read, checked, or executed unless a tool call actually did it.

Bad guidance to avoid:

```text
请确认这份章节与逐页文案是否可以进入图片生成阶段。
所有带文字版图片已保存，请确认后我再生成无文字底图。
是否需要我生成无文字背景图或直接打包成 PPTX？
```

Correct progress guidance:

```text
我会按“文案规划 -> 带文字图片 -> 无文字底图 -> 可编辑 PPTX”连续完成。过程中会把每一步写入 MANIFEST.md；只有缺输入、缺凭证或工具失败时才暂停。
```

If the user explicitly asks for staged review, switch to review-gated mode and write `review_gates: enabled` in `MANIFEST.md`. In that mode, Phase 1 and Phase 2 may stop for user approval. Otherwise, continue through final PPTX delivery in one run.

Grounding rule: final or progress messages may say "generated", "checked", "ran", "saved", or "completed" only for actions backed by actual tool calls and real files. If the runtime is text-only or tools are unavailable, say that production cannot continue in text-only mode.

## Entry Modes

Choose the lightest mode that matches the user's actual inputs.

Default assumption:

- Treat full production as an image-generation-first workflow. The normal path is: approved plan -> model-generated slide images -> model-generated clean backgrounds -> editable PPT reconstruction.
- Switch away from that path only when the user explicitly says the slide images are already prepared, the clean backgrounds are already prepared, or they want reconstruction only.

- Full production mode: use when the user provides source content and wants this skill to plan copy, generate slide images, generate clean backgrounds, and rebuild PPTX.
- Bring-your-own-slide-images mode: use when the user already has text-overlaid slide images from GPT image tools, Midjourney, Banana, other image models, designers, or manual work. Skip automated slide-image generation, create the project folder, copy/import those images into `/ppt`, record their source, then continue to clean backgrounds and editable PPT reconstruction.
- Bring-your-own-backgrounds mode: use when the user provides both text-overlaid slide images and matching clean no-text backgrounds. Skip image generation and clean-background generation, verify image counts and ordering, then run editable PPT reconstruction.
- Reconstruction-only mode: use when the user only wants an editable PPT from existing images. Do not force Phase 1 planning; ask only for missing image paths, page order, and deck language if unknown.
- Review-gated mode: use only when the user explicitly asks to approve copy or images before continuing. Record the gate in `MANIFEST.md` so a later turn can resume from real files, not from chat memory.

Mode safety rule:

- If the user asked for full production and the workflow still needs model-generated slide images or clean backgrounds, do not silently downgrade into bring-your-own-images mode or reconstruction-only mode just because image generation is not configured.
- In that case, stop and ask the user for one usable generation route: a callable `image2` path, a built-in image generation tool, a provider/base URL plus key, or pre-generated slide images.
- Do not jump straight to local PPT reconstruction unless the user explicitly changes mode or already supplied the required images.
- If the user says they already finished the image-generation step outside the skill, accept that as bring-your-own-slide-images mode and continue from image import plus PPT reconstruction.
- The sentence "image generation tool is unavailable" is not permission to switch modes. It is a blocking error in full production mode.
- Do not create a "visual reference", "HTML preview", "one-page PPT", "draft PPTX", or "python-pptx version" to replace the missing generated slide images. Those outputs are false completion for this skill.
- When blocked by missing image-generation configuration, be helpful and concrete. Say that the user can send the OpenAI-compatible image API URL, key, and model name, and the agent will initialize the configuration; or the user can send already-generated slide images, and the agent will turn them into a PPT.

External image tools are first-class inputs. Images made through direct GPT chat, image2, Banana, Midjourney, designers, or other systems are valid as long as they are accessible as local files or downloadable URLs.

## Required Inputs

Ask the user for source material before production if needed and the material is not already available:

- Business goal, audience, scenario, and expected deck length.
- Source content: pasted text, Markdown, Word/PDF/PPTX, product specs, brand assets, screenshots, or reference images.
- Existing slide images: local paths, directories, zip archives, or URLs if the user already generated or designed the PPT images elsewhere.
- Optional matching clean backgrounds if the user already has no-text versions.
- Visual direction: style, brand colors, examples, taboos, logo/product usage constraints.
- Output preference: default is 16:9 PNG images plus editable PPTX.

Do not invent product facts, model names, parameters, roadmap dates, or customer claims. Mark missing facts as `待补充` or ask the user. If the user supplies final slide images and only wants reconstruction, do not require the original source text.

## Language And Copy Fidelity

Lock the deck language before writing Phase 1. If the user explicitly names a language, use it. If not, infer it from the user's request and source material; Chinese requests or Chinese source content default to Simplified Chinese.

Rules:

- Write Phase 1 page titles, body copy, labels, captions, and progress messages in the locked deck language.
- Do not translate the deck into English just because the image prompt template is written in English.
- Preserve product names, model names, acronyms, protocol names, UI names, and technical parameters in their source form.
- For mixed Chinese/English enterprise decks, use Chinese for narrative copy and keep English only for proper nouns, product names, acronyms, and user-provided English phrases.
- Record `deck_language` in `approved_plan.md`, `prompts/image_prompts.md`, and `MANIFEST.md`.
- When building `image2` prompts, include a hard rule that all visible on-slide text must match the approved slide copy in `deck_language`; do not translate, romanize, summarize, or replace it with English.
- If the first generated page contains the wrong language, stop immediately, revise the prompt, and regenerate that page before continuing.

## Output Directory

Use a portable output root. Never hardcode a machine-specific path such as `/Users/huxin/...` as the general default.

Resolve the project directory in this order:

1. User-provided absolute or relative output path.
2. Environment variable `COMMERCIAL_PPT_OUTPUT_ROOT`, `AI_PPT_OUTPUT_ROOT`, or `PPT_OUTPUT_ROOT`.
3. Current workspace: `./ppt-projects/<project-id>/`.
4. User home fallback: `~/Desktop/ppt-projects/<project-id>/` if Desktop exists.
5. Final fallback: `~/ppt-projects/<project-id>/`.

Use a machine-specific directory only when the user explicitly provides that path
in the current task or when it is configured through one of the output-root
environment variables above. Do not bake personal workstation paths into prompts,
project templates, or reusable skill instructions.

When running on Windows, use `Path.home()` or the chosen workspace root instead of Unix paths. Examples: `C:\Users\<name>\Desktop\ppt-projects\<project-id>` or `.\ppt-projects\<project-id>`.

## Path Reporting

Always report resolved paths, not just shorthand paths.

Rules:

- Resolve the project directory to an absolute path before creating files. In Python, use `Path(...).expanduser().resolve()`.
- Do not tell the user only `~/Desktop/...`, `./ppt-projects/...`, `/ppt`, or `/ppt-clean`; these are ambiguous across local machines, containers, sandboxes, SSH hosts, and project workspaces.
- Whenever reporting saved files, include the absolute project directory and absolute artifact folders.
- If a shorthand path is useful, show it only after the absolute path, for example: `/workspace/home/Desktop/ppt-projects/demo` (`~/Desktop/ppt-projects/demo` inside the runtime environment).
- If the runtime environment may not be the user's physical desktop, explicitly say that the path is inside the current runtime/workspace environment.
- If `COMMERCIAL_PPT_PUBLIC_BASE_URL`, `AI_PPT_PUBLIC_BASE_URL`, or `PPT_PUBLIC_BASE_URL` is configured, report both the absolute filesystem path and the corresponding URL for user-facing artifacts. URL-encode non-ASCII path segments with `urllib.parse.quote(rel, safe="/")`.
- `MANIFEST.md` must include `project_dir_abs`, `runtime_home_abs`, `public_base_url` when configured, and the absolute paths for `ppt_dir`, `ppt_clean_dir`, and `ppt_editable_dir`.

Create this structure before Phase 2 generation or image import:

```text
<project>/
  source/
    approved_plan.md
    imported_assets.md
  ppt/
    01_cover.png
    02_xxx.png
  ppt-clean/
    01_cover_clean.png
    02_xxx_clean.png
  ppt-editable/
    <project-id>_editable.pptx
    <project-id>_editable_text_layers.json
  prompts/
    image_prompts.md
    clean_background_prompts.md
  remote_assets.json
  upload_bridge_records.json
  MANIFEST.md
```

Write progress into `MANIFEST.md` as each page completes. Report progress to the user page by page; do not leave long tasks silent.

`MANIFEST.md` must record the resolved absolute project directory, operating system, image model, resolution, and whether public asset publishing was used.
If user-supplied images are imported, `MANIFEST.md` must record `slide_image_source: user_supplied` and the original paths or URLs without secrets.

Public URL reporting is a deployment feature, not a requirement. If no public base URL is configured, do not invent one; say that public URL access is not configured and continue with absolute local paths.

## Phase 1: Content And Chapter Planning

Goal: turn user material into a production-ready presentation plan.

Phase 1 is the internal planning step for the continuous run. It may create the project folder and write `source/approved_plan.md`. Do not stop after Phase 1 unless review-gated mode is explicitly enabled or required facts are missing.

Steps:

1. Read the user's material and extract facts, product relationships, audience needs, and missing data.
2. Draft a page plan with page number, title, purpose, main message, copy blocks, visual idea, required assets, and risk notes.
3. Write full slide copy, not just a rough outline. Keep pages content-led, not poster-only.
4. Save `approved_plan.md` under `source/`.
5. Continue to Phase 2 in the same run.

Phase 1 output should include:

- Deck title and intended audience.
- Slide list with each page's core message.
- Final text copy per page.
- Visual style brief.
- Known gaps or assumptions.

## Phase 2: Slide Image Acquisition

Enter Phase 2 after Phase 1 planning in the same run, or immediately when the user supplies existing slide images and asks to import, continue, or rebuild from them.

Phase 2 output is not a preview-only conversation artifact. Every generated or imported text-overlaid slide image must be written into the local project `/ppt` folder. Do not ask "whether to save"; save first, validate, record the files, then continue to Phase 3 unless review-gated mode is enabled.

Steps:

1. Create the output directory structure.
2. Save Phase 1 content to `source/approved_plan.md` when Phase 1 exists.
3. If the user supplied slide images, import them instead of generating new images.
4. If the user wants the skill to generate images, read `references/prompt-pack.md`, build one prompt per slide, save all prompts to `prompts/image_prompts.md`, and call the configured image model.
5. Save every text-overlaid slide image as PNG in `/ppt`, using two-digit page order.
6. Update `MANIFEST.md` after every imported or generated image.
7. Continue to Phase 3. Stop for image review only in review-gated mode.

If image generation completes but local saving fails, Phase 2 is not complete. Stop, report the failing page and path, and do not continue to Phase 3 until the local files are present and validated.

Remote generation persistence rules:

- Remote generation result URLs are temporary transport links, not durable source files.
- Immediately download every generated image result to local `/ppt` during Phase 2.
- Verify each saved image exists, is non-empty, opens as an image, and has the expected page order before moving on.
- Persist remote asset metadata locally. For every generated or uploaded image, write page identity, local file path, provider, model, reusable reference URL, download URL when present, provider file ID when present, expiry when known, and validation time to `remote_assets.json`; summarize the same non-secret mapping in `MANIFEST.md`.
- Treat `remote_assets.json` as a provider-agnostic asset table, not an Evolink-only record. It may contain assets from direct model APIs, OpenAI-compatible image gateways, proxy services, user-provided public URLs, or Evolink uploads.
- A remote URL is a valid reusable model-facing reference while it is inside its provider retention window or otherwise remains accessible and passes validation.
- The local `/ppt` image remains the durable source of truth; any saved URL is a cached transport reference, not the only copy.
- If the Phase 2 image model returns a hosted image URL such as `file_url`, `download_url`, or another reusable public URL, record it immediately in `remote_assets.json` as the Phase 3 reference URL. Do not discard it and re-upload the same local file later.
- If a generated result URL returns 404/403 or downloads invalid content, stop and report the failed page instead of continuing with missing local images.
- Do not use unchecked `curl -sL` or `curl -s -o` downloads. For Evolink `files.evolink.ai` result URLs, prefer:
  `curl -fL --retry 3 --retry-delay 2 --connect-timeout 15 --max-time 180 -A "Mozilla/5.0" -o "<local_png>" "<url>"`
  Then verify HTTP success, non-zero file size, and image validity before continuing.

Minimum `remote_assets.json` shape:

```json
{
  "assets": [
    {
      "page": 1,
      "role": "text_slide",
      "local_path_abs": "/absolute/project/ppt/01_cover.png",
      "provider": "openai-image",
      "model": "gpt-image-2",
      "source_kind": "generated",
      "transport": "remote_url",
      "reference_url": "https://example.com/asset/01_cover.png",
      "file_url": "https://files.evolink.ai/...",
      "download_url": "https://files.evolink.ai/...",
      "file_id": "optional-provider-file-id",
      "reusable_for_model_input": true,
      "created_at": "2026-05-11T10:00:00+08:00",
      "expires_at": "2026-05-14T10:00:00+08:00",
      "validated_at": "2026-05-11T10:05:00+08:00"
    }
  ]
}
```

User-supplied image import rules:

- Accept local image files, folders, zip archives, and downloadable HTTP(S) URLs.
- Supported formats: PNG, JPG/JPEG, and WebP. Convert to PNG when practical; otherwise preserve source format only if downstream scripts support it.
- Sort by natural filename order unless the user provides an explicit page order.
- Copy images into `/ppt`; do not modify originals in place.
- Save source mapping to `source/imported_assets.md`.
- If page order, missing pages, or duplicate versions are ambiguous, ask the user before continuing.
- Do not call Evolink, image2, or any remote image model just to import already-available slide images.

Image generation defaults:

- Model: `gpt-image-2` or the configured `image2` equivalent.
- Size: `16:9`.
- Resolution: `2K` by default. Never use `4K` unless the user explicitly asks.
- Quality: `medium` by default; pass it explicitly when the image tool has a `quality` parameter. Use `high` only when the user explicitly asks.
- `n`: `1` per page unless the user explicitly requests variants.
- Output: PNG.

Reference image rule:

- If the image model/API needs a URL for a local reference image, use an existing valid URL from `remote_assets.json` first. Upload the local image through Evolink Files only when no valid cached URL exists.
- Do not assume the image provider is Evolink. If Phase 2 already produced a reusable model-facing URL through some other service, keep using that service's URL until it expires or fails validation.
- Use Evolink Files only as an optional upload bridge for local files that still need a model-facing URL. If the user separately wants long-term publishing, finish this PPT workflow first and use a separate publishing workflow.
- Do not pass private local file paths to remote image APIs unless the tool explicitly uploads them.
- This rule applies only when a remote image API needs a URL. It does not apply when the user supplied final slide images for local reconstruction.

## Environment And Credential Preflight

Before Phase 2 image generation or Phase 3 clean-background generation:

- Resolve the skill directory, then run `scripts/image_gen_preflight.py --mode full-production --json --require-ready` before generating or locally drawing any slide images in full-production mode.
- If this preflight exits non-zero, stop immediately and guide the user. Use wording like:

```text
我现在还缺少可调用的图片生成配置，所以不能直接进入完整 PPT 生成流程。你可以把 OpenAI 兼容的图片生成接口 URL、key 和模型名发给我，我来完成初始化配置后继续生成；或者你直接提供已经生成好的页面图片，我来帮你导入并转成可编辑 PPT。
```

Do not continue to Python/HTML/PPTX generation while waiting for the user's choice.
- Check that the selected image model route is configured only if a model call is needed.
- If the host provides a built-in image generation tool, use its configured credentials and do not require raw Evolink secrets just to call that tool.
- If using `scripts/remote_asset_upload.py` or direct Evolink HTTP calls, require `EVOLINK_API_KEY` or `EVOLINK_API_TOKEN` in the environment or an equivalent configured secret.
- If a key, login, subscription, quota, or model access is missing, stop and tell the user exactly what is missing.
- If the user asked for full production and no callable image generation route is available, explicitly ask the user to provide one usable generation configuration or already-generated slide images. Do not self-select local reconstruction as a fallback.
- If the user supplied both `/ppt` images and matching `/ppt-clean` backgrounds, no image-provider credential is required for reconstruction.
- Never print, save, echo, or write API keys/tokens into prompts, Markdown files, `MANIFEST.md`, logs, URLs, or screenshots.
- Do not silently switch providers after authentication or quota failures. Ask the user before switching.
- Record only non-secret status in `MANIFEST.md`, such as `upload_bridge: available` or `image_provider: missing_key`.

## OCR Runtime Preflight

Phase 3 depends on OCR unless the user provides precomputed OCR JSON. Check the runtime before starting reconstruction, especially on fresh Linux servers and containers:

```bash
python scripts/ocr_preflight.py
python scripts/ocr_preflight.py --json --require-ready
```

Use the same Python interpreter that will run reconstruction. Prefer PaddleOCR when the runtime supports it; use RapidOCR as the smaller fallback. For split-runtime deployments, point Phase 3 at a dedicated OCR interpreter with one of:

- `COMMERCIAL_PPT_OCR_PYTHON`
- `AI_PPT_OCR_PYTHON`
- `PPT_OCR_PYTHON`
- `OCR_RUNTIME_PYTHON`

Treat these variables as deployment-level selectors, not server-specific hacks. They exist so the same skill can run on different hosts where the best OCR-capable Python differs from the main agent Python.

```bash
python -m pip install python-pptx pillow paddlepaddle paddleocr opencv-python-headless
# fallback:
python -m pip install python-pptx pillow rapidocr_onnxruntime opencv-python-headless
```

Backend order:

- PaddleOCR first when both `paddle` and `paddleocr` are importable.
- RapidOCR when PaddleOCR is unavailable.
- `--ocr-backend json` when OCR has already been computed or the environment cannot install OCR packages.

If OCR setup fails, do not write a new one-off PPT builder. Either fix the OCR environment, point the workflow at a working OCR runtime Python, provide JSON files matching the script's expected shape, or stop and report the exact missing dependency. Never claim Phase 3 is complete if the final deck only contains flattened background images.

When Phase 3 runs through `scripts/run_editable_ppt.py`, keep the generated `OCR Runtime` section in `MANIFEST.md`. It is part of the delivery record and explains which Python and backend were actually used on that host.

## Evolink File Upload Bridge

Use Evolink Files as an optional temporary public URL bridge for local reference images when a remote image API requires image URLs and no reusable URL already exists. This avoids repository authentication, repository permissions, and raw URL issues. Do not use this bridge for purely local image import or reconstruction, and do not assume every generated image came from Evolink.

Official endpoints:

- Base64 upload: `POST https://files-api.evolink.ai/api/v1/files/upload/base64`
- Stream upload: `POST https://files-api.evolink.ai/api/v1/files/upload/stream`
- URL upload: `POST https://files-api.evolink.ai/api/v1/files/upload/url`

Behavior and constraints:

- All upload APIs require `Authorization: Bearer <token>`.
- The response contains `data.file_url`, `data.download_url`, `data.file_id`, and `data.expires_at`.
- Uploaded files expire after 72 hours. Always keep the authoritative copy in the local project folder.
- Single request supports one image.
- Supported upload formats: `image/jpeg`, `image/png`, `image/gif`, `image/webp`.
- Uploads consume user quota; if quota is exhausted, stop and ask for another method.

Use this skill's helper script for cross-platform local uploads:

```bash
python scripts/remote_asset_upload.py \
  /path/to/project/ppt/01_cover.png \
  --upload-path <project-id>/ppt \
  --manifest /path/to/project/upload_bridge_records.json
```

The script tries stream upload first for local files, falls back to Base64 upload if needed, and uses URL upload for existing public HTTP(S) URLs. It prints the returned `file_url`. Set the token with:

```bash
export EVOLINK_API_KEY="..."
```

On Windows PowerShell:

```powershell
$env:EVOLINK_API_KEY="..."
python scripts/remote_asset_upload.py .\ppt\01_cover.png --upload-path <project-id>/ppt --manifest .\upload_bridge_records.json
```

When a remote image API needs reference URLs, pass the best available validated URL in `image_urls`. That may be a Phase 2 generation URL from any provider or an Evolink-uploaded `file_url`.

## Long-Term Publishing

Long-term sharing or repository publication is outside this PPT production workflow. The default workflow keeps authoritative files locally and uses remote URLs only as temporary transport handles. If the user asks to publish final assets after completion, treat that as a separate task.

Phase 2 progress wording:

```text
所有带文字版图片已落盘到：
<absolute_project_path>/ppt
我会继续生成无文字底图并重建可编辑 PPT。
```

If images were supplied by the user:

```text
我已把你提供的图片按页面顺序导入到：
<absolute_project_path>/ppt
我会继续生成或导入无文字底图并重建可编辑 PPT。
```

## Phase 3: Clean Backgrounds And Editable PPT

Enter Phase 3 after Phase 2 image acquisition in the same run, unless review-gated mode is enabled and the workflow is intentionally paused for user inspection.

Phase 3 is a chained execution phase. After `/ppt` images are present and validated, generate/import all clean backgrounds and then run editable PPT reconstruction in the same phase. Ask for additional confirmation only if inputs are missing, provider credentials/quota fail, page counts mismatch, or the user explicitly asks to pause.

Before Phase 3 model calls:

- Treat local `/ppt` images as the source of truth.
- Verify that `/ppt` contains the expected number of text-overlaid slide images.
- If the clean-background model requires image URLs, use this strict source priority for each `/ppt` image:
  1. Reuse the Phase 2 generation result URL recorded in `remote_assets.json` (`reference_url` first, then `file_url`, then `download_url`) when it maps to the exact local page/image and has not passed `expires_at`.
  2. Validate the cached URL with a lightweight HTTP request or image-open check before using it. If validation passes, pass that URL directly in `image_urls`.
  3. Upload the local `/ppt` image through the upload bridge only when the cached URL is missing, expired, points to the wrong page, or returns 403/404/invalid content.
- Do not attempt a fresh Evolink upload before checking existing Phase 2 URLs. Fresh upload requires `EVOLINK_API_KEY`/`EVOLINK_API_TOKEN`; cached Phase 2 result URLs from other providers usually do not.
- If upload credentials are missing but valid Phase 2 URLs exist, continue with the valid cached URLs instead of stopping.
- Save any refreshed upload URL back to `remote_assets.json`.
- If a local `/ppt` image is missing, attempt one fresh download from recorded provenance only if available. If the download returns 404/403 or invalid image content, stop and ask the user to provide or regenerate the missing page. Do not fabricate the missing page and do not continue with a partial deck.
- Do not let a 404 page, JSON error body, or empty file stand in for an image.

Steps:

1. If the user supplied matching clean no-text backgrounds, import them into `/ppt-clean` and skip clean-background generation.
2. Otherwise, read `references/prompt-pack.md` and use the strict no-text prompt.
3. Generate one clean no-text background for every `/ppt/*.png`.
4. Save each clean image as `/ppt-clean/<same-stem>_clean.png`.
5. Verify `/ppt` and `/ppt-clean` have the same page count and matching stems.
6. Locate the bundled editable PPT entrypoint inside this skill. Resolve the script path before running it; do not assume the current working directory is the skill directory.

```text
ppt-helper/scripts/run_editable_ppt.py
```

Script resolution order:

1. `<this-skill-dir>/scripts/run_editable_ppt.py`.
2. `./scripts/run_editable_ppt.py`.
3. `./ppt-helper/scripts/run_editable_ppt.py`.
4. `$HERMES_HOME/skills/ppt-helper/scripts/run_editable_ppt.py`.
5. `$CODEX_HOME/skills/ppt-helper/scripts/run_editable_ppt.py`.
6. `~/.codex/skills/ppt-helper/scripts/run_editable_ppt.py`.

If the script still cannot be found, stop and report the missing script path search. Do not create a simplified replacement and do not fall back to hand-written `python-pptx`.

7. Run the bundled launcher script; do not write a replacement python-pptx implementation from scratch.
8. Use OCR defaults: PaddleOCR first, RapidOCR second, precomputed JSON only when OCR has already been computed or the runtime cannot install OCR packages.
9. If a multimodal style pass is needed, create `style_overrides.json` and rerun the script with `--style-overrides`.
10. Validate the PPTX and report final paths.

Recommended command:

```bash
python <resolved_script_path> \
  --base /path/to/project \
  --output <project-id>_editable.pptx
```

Dependency install when needed:

```bash
python -m pip install python-pptx pillow paddlepaddle paddleocr opencv-python-headless
# fallback:
python -m pip install python-pptx pillow rapidocr_onnxruntime opencv-python-headless
```

Precomputed OCR JSON fallback:

```bash
python <resolved_script_path> \
  --base /path/to/project \
  --ocr-backend json \
  --ocr-json-dir /path/to/project/ppt-editable/ocr/json \
  --output <project-id>_editable.pptx
```

## No-Text Background Rules

Remove text glyphs only. Preserve all visual containers and slide structure.

Keep:

- Rounded rectangles, title bars, bottom caption bars, glass panels, borders, divider lines.
- Glow outlines, cyan/purple effects, HUD lines, dots, grids, decorations.
- Icons, pictograms, product/device images, cloud/database/network symbols.
- Badges, tabs, table lines, cylinders, module cards, layout frames.
- Product-photo text that is physically part of the product image.

Remove:

- Readable Chinese or English characters.
- Numbers, page text, titles, subtitles, labels, captions, brand words.
- Number glyphs inside badges, while keeping badge shapes.

The output must look like the same slide template with empty text placeholders, not a simplified background.

## Editable PPT Reconstruction Rules

Use this skill's bundled `scripts/run_editable_ppt.py` and `scripts/build_editable_ppt_vision.py` because they already include:

- Cross-platform OCR backend selection.
- Dynamic image-size mapping.
- Safe text box expansion.
- Font fallback: `PingFang SC`, `Microsoft YaHei`, `Noto Sans CJK SC`.
- `orig - clean` color sampling.
- Native PPT gradient text support.
- Optional multimodal style overrides.

Hard rules:

- Coordinates must come from OCR or verified visual bbox, never model guesswork.
- Complex visuals should stay in the clean background; rebuild text as editable PPT text.
- Do not paste the original text-overlaid PNG as a full-page image in the final PPT.
- Do not duplicate icons, products, borders, cards, or table lines if they already exist in the clean background.
- Set text frame margins to zero and disable wrapping for source single-line text.

## Validation

Before declaring completion:

1. Run `unzip -t <output.pptx>`.
2. Confirm page count equals `/ppt` image count.
3. Confirm each page has a clean background image.
4. Confirm editable text boxes exist and `offslide = 0` if a checker is available.
5. Inspect small titles, labels, body text, and table text; these fail before large titles do.
6. Check that text color is not broadly gray or black unless the original is.
7. Check that generated gradients are used where the source has glow or blue-white transitions.
8. Confirm `MANIFEST.md` lists all final artifacts.

Final response should be concise and include:

- Project directory.
- Absolute `/ppt`, `/ppt-clean`, and final PPTX paths.
- Validation status.
- Any known limitations or pages that need user review.
