# tsryo.github.io

Personal website of Tsvetan R. Yordanov, served by GitHub Pages at https://tsryo.github.io/.

Plain static files, no build step:

- `index.html`: the whole site, readable without JavaScript.
- `css/style.css`: all styles. Colours are tokens at the top.
- `js/main.js`: optional extras (active nav link, a Konami-code easter egg).
- `404.html`: served by GitHub Pages for unknown URLs, so it uses root-absolute paths.
- `assets/`: self-hosted fonts (SIL OFL), images and `pdf/resume.pdf`.

## Preview

```sh
python -m http.server 8000
```

Then open http://localhost:8000/. Opening `index.html` directly also works, except for `404.html`.

## Update

- Resume: replace `assets/pdf/resume.pdf`.
- Pushing to `main` publishes the site.
