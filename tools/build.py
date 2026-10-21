"""Build the language versions of the site from src/index.html and src/i18n/*.json.

    python tools/build.py

Writes index.html (English) and <lang>/index.html for every other strings file.
{{> name}} in the template includes src/partials/name.html (the skyline, drawn by
tools/draw_skyline.py).
To add a language, copy src/i18n/en.json to src/i18n/<code>.json, translate the
values, set "_path" to "<code>/", draw its flag in "_flag" (SVG shapes in the
box x 4–24, y 4–38, clipped to a torn banner), and run the build. It stops with an error if a
key is missing or unused, so a half-translated language can't slip through.
Standard library only.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SITE = "https://tsryo.github.io/"
ORDER = ["en", "bg", "es", "nl"]  # switcher order; other languages follow alphabetically


def load_langs():
    langs = {}
    for f in sorted((SRC / "i18n").glob("*.json")):
        langs[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    codes = [c for c in ORDER if c in langs] + sorted(c for c in langs if c not in ORDER)
    return codes, langs


def check_keys(codes, langs):
    ref = set(langs["en"])
    ref_js = set(langs["en"]["js"])
    problems = []
    for code in codes:
        keys, js = set(langs[code]), set(langs[code].get("js", {}))
        for k in sorted(ref - keys):
            problems.append(f"{code}: missing {k}")
        for k in sorted(keys - ref):
            problems.append(f"{code}: unknown key {k}")
        for k in sorted(ref_js - js):
            problems.append(f"{code}: missing js.{k}")
    if problems:
        sys.exit("Strings don't match en.json:\n  " + "\n  ".join(problems))


CLOTH = "M4 4.5 H24 V30 L22 33 L20 30.5 L17.5 36 L14.5 31.5 L12 37 L9.5 32 L7 35 L4 31.5 Z"


def banner(flag):
    """A torn war banner on an iron rod, painted with the language's flag (its "_flag")."""
    return (
        '<svg class="banner" viewBox="0 0 28 40" aria-hidden="true" focusable="false">'
        f'<g clip-path="url(#banner-cloth)">{flag}'
        '<rect x="4" y="4" width="20" height="34" fill="url(#banner-folds)"/>'
        '<rect x="4" y="4" width="20" height="34" fill="url(#banner-age)"/></g>'
        f'<path class="banner-edge" d="{CLOTH}"/>'
        '<rect class="banner-rod" x="1" y="2" width="26" height="2.6" rx="1.3"/>'
        '<circle class="banner-knob" cx="1.6" cy="3.3" r="1.7"/><circle class="banner-knob" cx="26.4" cy="3.3" r="1.7"/>'
        '</svg>')


def lang_link(c, current, depth, langs):
    href = "../" * depth + langs[c]["_path"]
    name = html.escape(langs[c]["_name"])
    here = ' aria-current="true"' if c == current else ""
    return (f'        <li><a href="{href}" hreflang="{c}" lang="{c}" title="{name}"{here}>'
            f'{banner(langs[c]["_flag"])}<span class="visually-hidden">{name}</span></a></li>')


def render(template, code, codes, langs):
    s = langs[code]
    depth = s["_path"].count("/")
    values = {k: v for k, v in s.items() if not k.startswith("_") and k != "js"}
    values.update({
        "lang": code,
        "root": "../" * depth,
        "canonical": SITE + s["_path"],
        "og_locale": s["_locale"],
        "fl_plate_x": str(280 - int(s["fl_plate_w"]) / 2).rstrip("0").rstrip("."),
        "js_strings": json.dumps(s["js"], ensure_ascii=False).replace("</", "<\\/"),
        "alternates": "\n".join(
            [f'  <link rel="alternate" hreflang="{c}" href="{SITE}{langs[c]["_path"]}">' for c in codes]
            + [f'  <link rel="alternate" hreflang="x-default" href="{SITE}">']),
        "langs_nav": "\n".join(lang_link(c, code, depth, langs) for c in codes),
    })
    used = set()

    def sub(m):
        key = m.group(1)
        if key not in values:
            sys.exit(f"{code}: template uses unknown key {key}")
        used.add(key)
        return values[key]

    out = re.sub(r"\{\{(\w+)\}\}", sub, template)
    unused = {k for k in s if not k.startswith("_") and k != "js"} - used
    if unused:
        sys.exit(f"{code}: keys not used by the template: {', '.join(sorted(unused))}")
    return out


def main():
    codes, langs = load_langs()
    check_keys(codes, langs)
    template = (SRC / "index.html").read_text(encoding="utf-8")
    template = re.sub(r"\{\{> *(\w+) *\}\}\n?", lambda m: (SRC / "partials" / f"{m.group(1)}.html").read_text(encoding="utf-8"), template)
    for code in codes:
        out_dir = ROOT / langs[code]["_path"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(render(template, code, codes, langs), encoding="utf-8", newline="\n")
        print(f"built {code}: {(out_dir / 'index.html').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
