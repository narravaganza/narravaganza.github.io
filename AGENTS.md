# AGENTS.md
This repo is a Hugo-powered static site for publishing fiction and non-fiction writing. Agents are expected to help with frontend tasks and to act as creative partners to write or edit stories.

## Writing and editing stories

**CRITICAL: Before writing or editing any piece, you MUST read all existing piece in the same format from `content/` to absorb the author's voice.** Do not write in a generic style. Match the tone, cadence, sentence structure, and quirks of the existing work.
- You can see the voice docs in `_docs/voice-*` for reference.
- Add new pieces to the appropriate collection folder as Markdown, with the appropriate YAML front matter at the top.
- Stories that immediately require agent editing/suggesting will be annotated with _custom pipe bracket_ syntax: The text between [ and | is the text that needs revising. The text between | and ] is the instruction. For each annotation, respond in chat with the original text followed by 5 numbered suggestions.

## Translations
- Until the whole site becomes multilingual, keep translated pieces at their existing URLs; do not enable Hugo's multilingual configuration just for individual translations.
- Use `params.contentLanguage` (BCP 47 code, e.g. `en`, `es`, `it`) for a piece's language. Unspecified pieces inherit the site's language.
- On translations, also set `params.translationOf` to the original's logical content path (e.g. `/stories/flavour-of-facts`, without extension or trailing slash) and `params.listInCollection: false`. This links versions while listing each work once in the collection and feeds. Templates still render the translation normally.
- Mark original non-English works with their language, but do not hide them or set `translationOf` unless they are translations.
- Language names live in `data/languages.yml`. A later full multilingual rollout can migrate these relationships to Hugo's native language and translation features while preserving public URLs.

## Quick map
- Content collections
  - `content/stories/` : fiction stories (Markdown with YAML front matter)
  - `content/essays/` : non-fiction essays
  - `content/sketches/` : short sketches or experiments
  - `content/drafts/` : in-progress pieces (use `draft: true`)
- Layout and structure
  - `layouts/` : page templates (`baseof.html`, section templates, etc.)
  - `layouts/partials/` : reusable blocks (navigation, story list, etc.)
  - `layouts/shortcodes/` : content shortcodes (story roll)
- Styles and assets
  - `assets/css/styles.scss` : main site styles (Hugo compiles SCSS)
  - `assets/css/screenplay.scss` : screenplay-specific styles
  - `_sass/` : shared Sass files (fonts, helpers)
- `assets/images/originals/` : source images (preserve filenames and subfolders)
- `static/assets/` : published assets (fonts, AVIF images)
- Data
  - `data/` : site data files (navigation, taglines)
- Build output (do not edit by hand)
  - `docs/` : generated site files

## Frontend edits
- Prefer editing SCSS in `assets/css/` or `_sass/`. Hugo will compile it.
- Keep raster source files in `assets/images/originals/`. Do not replace or delete them.
- Originals are source-only: never mount them into the published site or copy them into `static/` or top-level image folders. Templates read source dimensions from `assets/images/originals/` or the manifest.
- Generate responsive AVIFs at quality 80 with `python3 scripts/optimize-images.py`.
  The normal `scripts/build.sh` workflow runs this automatically.
- Commit the generated files in `static/assets/images/` and the updated
  `data/images.json`. CI verifies that they match their source images.
- Content uses responsive AVIFs. The optimizer also generates explicit JPEG derivatives for local social-preview images; their `social` entries live in `data/images.json`. Keep original image URLs in content and `params.ogImage` so the manifest can resolve delivery assets.
- Use `python3 scripts/optimize-images.py --include-drafts` when images are only
  referenced by draft content.
- Do not convert SVGs, animated GIFs, favicons, or other non-content graphics
  automatically.
- Always run `hugo --destination ./tmp/` as a smoke test before considering work done.

### Browser verification artifacts
- Keep all browser verification artifacts under `tmp/playwright/`, which is ignored by Git.
- Run the Playwright CLI with `tmp/playwright/` as its working directory so its `.playwright-cli/` logs and snapshots stay there. Save screenshots there too.
- Do not create repository-root `.playwright-cli/` or `output/playwright/` directories.
- Never stage browser artifacts. Purge `tmp/playwright/` after verification unless the user asks to retain an artifact; preserve other files in `tmp/`.

### Building and serving
- Build to the `docs/` folder: `scripts/build.sh`
- Live preview: `hugo server --destination ./tmp/` 

## Conventions uand constraints
- Do not edit `docs/` directly; it is generated.
- Keep filenames URL-safe (lowercase, hyphenated) for new content.
- Keep previews concise; they are used in story lists.
