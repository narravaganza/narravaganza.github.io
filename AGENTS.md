# AGENTS.md
This repo is a Hugo-powered static site for publishing fiction and non-fiction writing. Agents are expected to help with frontend tasks and to act as creative partners to write or edit stories.

## Writing and editing stories

**CRITICAL: Before writing or editing any piece, you MUST read all existing piece in the same format from `content/` to absorb the author's voice.** Do not write in a generic style. Match the tone, cadence, sentence structure, and quirks of the existing work.
- You can see the voice docs in `_docs/voice-*` for reference.
- Add new pieces to the appropriate collection folder as Markdown, with the appropriate YAML front matter at the top.
- Stories that immediately require agent editing/suggesting will be annotated with _custom pipe bracket_ syntax: The text between [ and | is the text that needs revising. The text between | and ] is the instruction. For each annotation, respond in chat with the original text followed by 5 numbered suggestions.

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
  - `static/assets/` : static assets (fonts, images)
- Data
  - `data/` : site data files (navigation, taglines)
- Build output (do not edit by hand)
  - `docs/` : generated site files

## Frontend edits
- Prefer editing SCSS in `assets/css/` or `_sass/`. Hugo will compile it.
- Always run `hugo --destination ./tmp/` as a smoke test before considering work done.

### Building and serving
- Build to the `docs/` folder: `hugo`
- Live preview: `hugo server --destination ./tmp/` 

## Conventions uand constraints
- Do not edit `docs/` directly; it is generated.
- Keep filenames URL-safe (lowercase, hyphenated) for new content.
- Keep previews concise; they are used in story lists.
