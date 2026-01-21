# AGENTS.md
This repo is a Hugo-powered static site for publishing fiction and non-fiction writing. Agents are expected to help with frontend tasks and to act as creative partners to write or edit stories.

## Writing and editing stories
- **CRITICAL: Before writing or editing the body any new story, you MUST read all existing stories from `content/stories/` to absorb the author's voice.** Do not write in a generic style. Match the tone, cadence, sentence structure, and quirks of the existing work. The author's voice is distinctive: first-person, tangential, philosophical spiraling, absurdist escalation from mundane situations.
- Add new pieces to the appropriate collection folder as Markdown, with the appropriate YAML front matter at the top.

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
- If the change touches layout or shared components, check `layouts/` and `layouts/partials/`.
- Keep typography and spacing consistent with the existing aesthetic unless asked to redesign.
- Always run `hugo --destination ./tmp/` as a smoke test before considering work done.

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
