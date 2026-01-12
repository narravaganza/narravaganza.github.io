# AGENTS.md

## Purpose
This repo is a Hugo-powered static site for publishing fiction and non-fiction writing. Agents are expected to help with frontend tasks and to act as creative partners to write or edit stories.

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

## How to be quickly productive
### Writing and editing stories
- Add new pieces to the appropriate collection folder as Markdown.
- Use YAML front matter at the top. At minimum, include `title` and `preview`.
- Keep the author voice consistent with existing pieces (in _stories/ and _sketches); match tone and cadence.
- When collaborating, propose a short outline or a few paragraph options before drafting a full piece.

### Frontend and CSS edits
- Prefer editing SCSS in `assets/css/` or `_sass/`. Hugo will compile it.
- If the change touches layout or shared components, check `layouts/` and `layouts/partials/`.
- Keep typography and spacing consistent with the existing aesthetic unless asked to redesign.
- Ensure builds pass by running `hugo build`

### Building and serving
- Build to the `docs/` folder: `hugo`
- Live preview: `hugo server --destination ./tmp/` 

## Conventions uand constraints
- Do not edit `docs/` directly; it is generated.
- Keep filenames URL-safe (lowercase, hyphenated) for new content.
- Keep previews concise; they are used in story lists.

## If you are unsure
Ask for:
- target section (story, essay, sketch)
- whether the user wants a light edit, a rewrite, or new material
