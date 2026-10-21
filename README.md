# tsryo.github.io

Personal website of Tsvetan R. Yordanov (Tseko), served by GitHub Pages at https://tsryo.github.io/.

Static files, in English, Bulgarian and Spanish:

- `src/index.html`: the page template. Text is `{{key}}` placeholders.
- `src/i18n/<lang>.json`: the strings for each language (`en`, `bg`, `es`).
- `tools/build.py`: builds `index.html`, `bg/index.html` and `es/index.html` from the two above (`{{> name}}` includes `src/partials/name.html`). Standard library only.
- `css/style.css`: all styles. Colours are tokens at the top.
- `js/main.js`, `js/ambience.js`: optional extras (active nav link, Konami code, click-to-load SoundCloud, generative ambience). The page works without them.
- `404.html`: served by GitHub Pages for unknown URLs, so it uses root-absolute paths.
- `electron-to-pixel/`: an interactive explainer, linked from the story.
- `assets/`: self-hosted fonts (SIL OFL), images (including the skyline painting), the map (Natural Earth, public domain) and `pdf/resume.pdf`.

## Edit text

Change the template or the JSON files, never the generated `index.html` files, then rebuild:

```sh
python tools/build.py
```

The build stops if a language is missing a key or has one the template doesn't use.

## Add a language

1. Copy `src/i18n/en.json` to `src/i18n/<code>.json`.
2. Translate the values and set `_name`, `_code`, `_locale`, `_path` (`"<code>/"`) and `_flag` (the flag painted on its banner in the language switcher).
3. Run the build. The language switcher and `hreflang` links update themselves.

Fonts cover Latin and Cyrillic. A language in another script needs a font for it in `css/style.css`.

## Skyline art

The painting at the foot of the hero (a Bulgarian village at dusk, with Scotland, Valencia and the Netherlands on the horizon) is drawn by code:

```sh
python tools/render_skyline.py
python tools/build.py
```

`tools/draw_skyline.py` writes the artwork as SVG (seeded, so it always draws the same scene) and `src/partials/skyline.html`, the live layers over it: the sun, window glow, the windmill's sails, smoke and the saltire. `tools/render_skyline.py` runs it, renders the SVG with headless Edge or Chrome, and saves `assets/img/skyline-{1280,1920,2880}.webp` with Pillow. Only this step needs a browser and Pillow.

## Security

GitHub Pages can't send custom headers, so each page carries its Content Security Policy in a `<meta>` tag: scripts only from this site, no inline scripts or `eval`, Trusted Types required, and frames only from SoundCloud, whose player loads on request in a sandboxed iframe. To keep it working:

- Put scripts in `.js` files, never inline or in `on…` attributes.
- Strings in `src/i18n/*.json` go into the page as HTML, so only put trusted text there.

`frame-ancestors` only works as a header, so other sites can still frame the pages.

## Performance

- Sections below the hero skip rendering until the first paint (`content-visibility`). `main.js` lays them out afterwards, or at once when an in-page link is followed, so links land exactly.
- Prefer `transform` and `opacity` for animation: other properties repaint or re-lay out the page every frame.
- What's out of view rests: SVG animations pause, and sections get `.is-resting`.
- No `backdrop-filter` or fixed full-screen layers: both are slow on older machines.
- Visitors who turn on Save-Data or reduced motion get a still page.

## Preview

```sh
python -m http.server 8000
```

Then open http://localhost:8000/. Pushing to `main` publishes the site.
