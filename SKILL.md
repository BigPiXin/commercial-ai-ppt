---
name: commercial-ai-ppt
description: "Use when the user asks to create, generate, write, design, import, or rebuild a commercial PowerPoint deck, proposal deck, solution presentation, pitch deck, slide images, no-text backgrounds, or editable PPT from text, documents, images, or product materials. This skill supports both automated image generation and bring-your-own-image workflows, then rebuilds editable PPT output through clean backgrounds and text-layer reconstruction."
---

# Commercial AI PPT Production

This skill turns user-provided solution content, product materials, documents, images, or rough requirements into a commercial-grade PPT workflow. It is a composite workflow: use specialized skills/tools as needed, but keep this skill as the top-level controller.

## Core Contract

Never skip the approval gates.

1. Phase 1 produces the PPT narrative, outline, and final slide-by-slide copy. Stop and ask the user to approve.
2. Phase 2 creates the local project folder, saves the approved plan as Markdown when available, then either generates text-overlaid slide images or imports user-supplied slide images into `/ppt`. Stop and ask the user to approve the images unless they explicitly already approved them.
3. Phase 3 generates or imports no-text backgrounds, then rebuilds the editable PPT with the existing image-to-PPT script. Notify the user when complete.

If the user asks to "continue" after a gate, resume from the next phase. If required inputs are missing, ask only for the missing content or file path. Do not require Evolink or any image provider for local image import; require provider credentials only when a remote generation, editing, upload, or clean-background model call is actually needed.

## Entry Modes

Choose the lightest mode that matches the user's actual inputs.

- Full production mode: use when the user provides source content and wants this skill to plan copy, generate slide images, generate clean backgrounds, and rebuild PPTX.
- Bring-your-own-slide-images mode: use when the user already has text-overlaid slide images from GPT image tools, Midjourney, Banana, other image models, designers, or manual work. Skip automated slide-image generation, create the project folder, copy/import those images into `/ppt`, record their source, and continue from image review or Phase 3.
- Bring-your-own-backgrounds mode: use when the user provides both text-overlaid slide images and matching clean no-text backgrounds. Skip image generation and clean-background generation, verify image counts and ordering, then run editable PPT reconstruction.
- Reconstruction-only mode: use when the user only wants an editable PPT from existing images. Do not force Phase 1 planning; ask only for missing image paths, page order, deck language if unknown, and whether the current images should be treated as approved.

External image tools are first-class inputs. Images made through direct GPT chat, image2, Banana, Midjourney, designers, or other systems are valid as long as they are accessible as local files or downloadable URLs.

## Required Inputs

Ask the user for source material before Phase 1 if Phase 1 is needed and the material is not already available:

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

- Write Phase 1 page titles, body copy, labels, captions, and review messages in the locked deck language.
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

For this user's current Mac only, if the existing local convention exists, it may be used as a user-specific override, not as a portable default:

```text
/Users/huxin/Desktop/test/template/<project-id>/
```

When running on Windows, use `Path.home()` or the chosen workspace root instead of Unix paths. Examples: `C:\Users\<name>\Desktop\ppt-projects\<project-id>` or `.\ppt-projects\<project-id>`.

## Path Reporting

Always report resolved paths, not just shorthand paths.

Rules:

- Resolve the project directory to an absolute path before creating files. In Python, use `Path(...).expanduser().resolve()`.
- Do not tell the user only `~/Desktop/...`, `./ppt-projects/...`, `/ppt`, or `/ppt-clean`; these are ambiguous across local machines, containers, sandboxes, SSH hosts, and project workspaces.
- Whenever reporting saved files, include the absolute project directory and absolute artifact folders.
- If a shorthand path is useful, show it only after the absolute path, for example: `/workspace/home/Desktop/ppt-projects/demo` (`~/Desktop/ppt-projects/demo` inside the runtime environment).
- If the runtime environment may not be the user's physical desktop, explicitly say that the path is inside the current runtime/workspace environment.
- `MANIFEST.md` must include `project_dir_abs`, `runtime_home_abs`, and the absolute paths for `ppt_dir`, `ppt_clean_dir`, and `ppt_editable_dir`.

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
  evolink_uploads.json
  MANIFEST.md
```

Write progress into `MANIFEST.md` as each page completes. Report progress to the user page by page; do not leave long tasks silent.

`MANIFEST.md` must record the resolved absolute project directory, operating system, image model, resolution, and whether public asset publishing was used.
If user-supplied images are imported, `MANIFEST.md` must record `slide_image_source: user_supplied` and the original paths or URLs without secrets.

## Phase 1: Content And Chapter Planning

Goal: turn user material into a reviewed commercial presentation plan.

Steps:

1. Read the user's material and extract facts, product relationships, audience needs, and missing data.
2. Draft a page plan with page number, title, purpose, main message, copy blocks, visual idea, required assets, and risk notes.
3. Write full slide copy, not just a rough outline. Keep pages content-led, not poster-only.
4. Save or prepare `approved_plan.md` content, but do not enter Phase 2 yet.
5. Present the plan to the user and explicitly ask for approval.

Approval wording:

```text
请确认这份章节与页面文案是否可以进入图片生成阶段。你确认后，我再创建项目目录并开始逐页生成 PNG。
```

Phase 1 output should include:

- Deck title and intended audience.
- Slide list with each page's core message.
- Final text copy per page.
- Visual style brief.
- Known gaps or assumptions.

## Phase 2: Slide Image Acquisition

Enter Phase 2 after explicit Phase 1 approval, or immediately when the user supplies existing slide images and asks to import, continue, or rebuild from them.

Steps:

1. Create the output directory structure.
2. Save Phase 1 content to `source/approved_plan.md` when Phase 1 exists.
3. If the user supplied slide images, import them instead of generating new images.
4. If the user wants the skill to generate images, read `references/prompt-pack.md`, build one prompt per slide, save all prompts to `prompts/image_prompts.md`, and call the configured image model.
5. Save every text-overlaid slide image as PNG in `/ppt`, using two-digit page order.
6. Update `MANIFEST.md` after every imported or generated image.
7. Stop and ask the user to review the images before Phase 3, unless they explicitly said the supplied images are already approved.

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
- Quality: `medium` by default; use `high` only for a specific page if justified.
- `n`: `1` per page unless the user explicitly requests variants.
- Output: PNG.

Reference image rule:

- If the image model/API needs a URL for a local reference image, upload the local image through Evolink Files first and pass the returned `data.file_url`.
- Use Evolink Files for model-facing image URLs. If the user separately wants long-term publishing, finish this PPT workflow first and use a separate publishing workflow.
- Do not pass private local file paths to remote image APIs unless the tool explicitly uploads them.
- This rule applies only when a remote image API needs a URL. It does not apply when the user supplied final slide images for local reconstruction.

## Environment And Credential Preflight

Before Phase 2 image generation or Phase 3 clean-background generation:

- Check that the selected image model route is configured only if a model call is needed.
- If using Evolink upload or Evolink `gpt-image-2`, require `EVOLINK_API_KEY` or `EVOLINK_API_TOKEN` in the environment or an equivalent configured secret.
- If a key, login, subscription, quota, or model access is missing, stop and tell the user exactly what is missing.
- If the user supplied both `/ppt` images and matching `/ppt-clean` backgrounds, no image-provider credential is required for reconstruction.
- Never print, save, echo, or write API keys/tokens into prompts, Markdown files, `MANIFEST.md`, logs, URLs, or screenshots.
- Do not silently switch providers after authentication or quota failures. Ask the user before switching.
- Record only non-secret status in `MANIFEST.md`, such as `evolink_upload: available` or `image_provider: missing_key`.

## Evolink File Upload Bridge

Use Evolink Files as the preferred temporary public URL bridge for local reference images when a remote image API requires image URLs. This avoids repository authentication, repository permissions, and raw URL issues. Do not use this bridge for purely local image import or reconstruction.

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
python scripts/evolink_upload.py \
  /path/to/project/ppt/01_cover.png \
  --upload-path <project-id>/ppt \
  --manifest /path/to/project/evolink_uploads.json
```

The script uses Base64 upload for local files and URL upload for existing public HTTP(S) URLs, then prints the returned `file_url`. Set the token with:

```bash
export EVOLINK_API_KEY="..."
```

On Windows PowerShell:

```powershell
$env:EVOLINK_API_KEY="..."
python scripts/evolink_upload.py .\ppt\01_cover.png --upload-path <project-id>/ppt --manifest .\evolink_uploads.json
```

When calling `gpt-image-2` image editing or clean-background generation, pass the uploaded `file_url` in `image_urls`.

## Long-Term Publishing

Long-term sharing or repository publication is outside this PPT production workflow. The default workflow keeps authoritative files locally and uses Evolink Files only as a temporary model-facing URL bridge. If the user asks to publish final assets after completion, treat that as a separate task.

Phase 2 review wording:

```text
所有带文字版图片已落盘到：
<absolute_project_path>/ppt
请先审查页面视觉、文案、产品图和顺序；你确认图片可行后，我再生成无文字底图并重建可编辑 PPT。
```

If images were supplied by the user:

```text
我已把你提供的图片按页面顺序导入到：
<absolute_project_path>/ppt
请确认这些图片是否就是最终带文字版页面；你确认后，我再继续生成无文字底图并重建可编辑 PPT。
```

## Phase 3: Clean Backgrounds And Editable PPT

Enter Phase 3 only after explicit user approval of `/ppt` images, unless the user supplied those images and explicitly said they should be treated as final/approved.

Steps:

1. If the user supplied matching clean no-text backgrounds, import them into `/ppt-clean` and skip clean-background generation.
2. Otherwise, read `references/prompt-pack.md` and use the strict no-text prompt.
3. Generate one clean no-text background for every `/ppt/*.png`.
4. Save each clean image as `/ppt-clean/<same-stem>_clean.png`.
5. Verify `/ppt` and `/ppt-clean` have the same page count and matching stems.
6. Locate the bundled editable PPT script inside this skill:

```text
commercial-ai-ppt/scripts/build_editable_ppt_vision.py
```

7. Run the bundled script; do not write a replacement python-pptx implementation from scratch.
8. Use cross-platform OCR defaults: Apple Vision on macOS, RapidOCR on Windows/Linux, Tesseract or precomputed JSON only as fallback.
9. If a multimodal style pass is needed, create `style_overrides.json` and rerun the script with `--style-overrides`.
10. Validate the PPTX and report final paths.

Recommended command:

```bash
python scripts/build_editable_ppt_vision.py \
  --base /path/to/project \
  --ocr-backend auto \
  --output <project-id>_editable.pptx
```

Windows dependencies when needed:

```bash
python -m pip install python-pptx pillow rapidocr_onnxruntime opencv-python-headless
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

Use this skill's bundled `scripts/build_editable_ppt_vision.py` because it already includes:

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
