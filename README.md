# tsryo.github.io

Personal website of Tsvetan R. Yordanov (Tseko), served by GitHub Pages at https://tsryo.github.io/.

Static files, in English, Bulgarian and Spanish:

- `src/index.html`: the page template. Text is `{{key}}` placeholders.
- `src/i18n/<lang>.json`: the strings for each language (`en`, `bg`, `es`).
- `tools/build.py`: builds `index.html`, `bg/index.html` and `es/index.html` from the two above. Standard library only.
- `css/style.css`: all styles. Colours are tokens at the top.
- `js/main.js`, `js/ambience.js`: optional extras (active nav link, Konami code, click-to-load SoundCloud, generative ambience). The page works without them.
- `404.html`: served by GitHub Pages for unknown URLs, so it uses root-absolute paths.
- `electron-to-pixel/`: an interactive explainer, linked from the story.
- `assets/`: self-hosted fonts (SIL OFL), images, the map (Natural Earth, public domain) and `pdf/resume.pdf`.

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

## Preview

```sh
python -m http.server 8000
```

Then open http://localhost:8000/. Pushing to `main` publishes the site.
