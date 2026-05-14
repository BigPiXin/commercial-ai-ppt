# Prompt Pack

Use this file only when entering Phase 2 or Phase 3 of `ppt-helper` and a model call is actually needed. Do not load this file for pure local image import or reconstruction from already-supplied slide images/backgrounds.

## Reference URL Handling

When Phase 3 needs `image_urls` for clean-background generation, do not upload `/ppt` images first by default. Treat the Phase 2 image-generation result URL as the connected transport handle for the same slide:

- Read `remote_assets.json` and match each local `/ppt` image by page number and local path.
- Prefer the recorded Phase 2 `file_url`, then `download_url`, when it is unexpired and still validates as an image.
- Pass the validated cached URL directly as the clean-background request's `image_urls` value.
- Upload the local `/ppt` image only when the cached URL is missing, expired, mismatched, inaccessible, or invalid.
- Missing Evolink upload credentials are not a blocker when valid Phase 2 result URLs already exist.

## Phase 2 Image Generation Prompt Template

Create one prompt per slide. Keep product facts and page copy exactly aligned with `source/approved_plan.md`.

```text
Create a premium 16:9 PowerPoint slide image for an enterprise presentation.

Deck language:
{deck_language}

Language requirements:
- All visible on-slide text must be written in {deck_language}.
- Use exactly the approved slide copy below; do not translate it into English, romanize it, summarize it, or replace it with generic English words.
- Keep product names, model names, acronyms, and technical parameters in their original source form.
- If the approved copy is Chinese, every title, label, caption, body paragraph, chart/table header, and small annotation should remain Chinese unless it is a proper noun or acronym.

Visual style:
{visual_style}

Slide {page_number}: {slide_title}

Audience:
{audience}

Core message:
{core_message}

Required on-slide text:
{approved_slide_copy}

Layout requirements:
{layout_requirements}

Required assets and constraints:
{asset_constraints}

Design requirements:
- High-end executive presentation aesthetic, not a poster.
- Clear title hierarchy, readable subtitles and body copy.
- Use structured cards, tables, diagrams, icons, or product/image areas when useful.
- Every visible text element must come from Required on-slide text and stay in {deck_language}.
- Preserve exact product names, model names, numbers, and technical parameters from the approved plan.
- Do not invent logos, customers, certifications, product specs, dates, or fake UI text.
- Do not add English filler text, lorem ipsum, fake chart labels, or decorative pseudo-words.
- Leave enough empty space and visual rhythm for a real PPT slide.
- Use a consistent visual system across all pages.

Output:
- 16:9 PNG.
- Resolution 2K by default.
- No extra variants unless requested.
```

## Phase 3 Strict No-Text Background Prompt

Use this prompt when generating `/ppt-clean` from a text-overlaid slide image.

```text
Create a 16:9 clean editable PowerPoint background based on the reference slide.
Important: remove text glyphs only. Do not remove or simplify the visual containers that hold the text.
Remove all readable Chinese or English characters, numbers, page text, titles, subtitles, labels, captions, and branding words. Replace only the character strokes with matching local background, glow, or glass texture.
Preserve all non-text visual structure exactly:

Keep every rounded rectangle, bottom caption bar, glass panel, border, divider line, glow outline, cyan/purple light effect, HUD line, dotted decoration, cylinder layer, card placeholder, and layout frame.
Keep all icons and pictograms, including circular arrow icons, card icons, layer icons, device icons, cloud icons, database icons, network icons, and decorative symbols.
For numbered badges such as 01, 02, 03, remove the digits only, but keep the blue badge/tab shape, border, glow, and position.
For bottom horizontal title banners, remove the sentence only, but keep the full rounded rectangle border, inner glow, background fill, and left icon.
For layer modules, remove the words only, but keep the translucent cards, vertical separators, icons, cylinder rings, and layer layout.
The output should look like the same slide template with empty text placeholders, not a simplified background. No new text, no fake letters, no invented logos.
```

Recommended request defaults:

```json
{
  "model": "gpt-image-2",
  "size": "16:9",
  "resolution": "2K",
  "quality": "medium",
  "n": 1
}
```

## Multimodal Style Override Prompt

Use only after the first editable PPT has been generated and the issue is font size, brightness, color, or gradient.

```text
You are reviewing an editable PPT reconstruction.

Inputs:
1. Original text-overlaid slide image.
2. Clean no-text background image.
3. Rendered preview of the editable PPT output.
4. text_layers JSON with page and region indexes.

Task:
Return only JSON style overrides for regions whose font size, text color, or gradient visibly differs from the original.

Rules:
- Do not change bbox, page, index, text, or reading order.
- Do not merge or split text regions.
- Prefer small corrections: font_size_scale, font_size_delta, color, gradient, font_name.
- Fix small titles, labels, and body text too; do not only fix large titles.
- Use gradient only when the source visibly has glow or blue-white/cyan transition.
- If uncertain, omit the region.

Output schema:
{
  "slides": [
    {
      "page": 1,
      "regions": [
        {
          "index": 0,
          "font_size_scale": 1.05,
          "color": "#EAF7FF",
          "gradient": ["#7DE7FF", "#FFFFFF"],
          "font_name": "PingFang SC",
          "reason": "brief visual reason"
        }
      ]
    }
  ]
}
```
