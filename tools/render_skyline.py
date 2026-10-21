"""Draw the skyline and render it to the WebP files the page uses.

    python tools/render_skyline.py

Runs tools/draw_skyline.py, renders the SVG with headless Microsoft Edge or
Chrome (transparent background, 2880 px wide), then writes
assets/img/skyline-{1280,1920,2880}.webp with Pillow. Needs a Chromium browser
and Pillow; the site itself needs neither.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "img"
WIDTHS = (1280, 1920, 2880)
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "chromium", "google-chrome", "microsoft-edge",
]


def browser():
    for b in BROWSERS:
        if Path(b).exists() or shutil.which(b):
            return b
    sys.exit("No Chromium browser found for rendering.")


def main():
    from PIL import Image  # only this tool needs Pillow

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        svg = tmp / "skyline.svg"
        subprocess.run([sys.executable, str(ROOT / "tools" / "draw_skyline.py"), str(svg), str(ROOT / "src" / "partials" / "skyline.html")], check=True)
        w, h = WIDTHS[-1], round(WIDTHS[-1] * 760 / 2400)
        page = tmp / "render.html"
        page.write_text(f'<!doctype html><html style="background:transparent"><body style="margin:0;background:transparent">'
                        f'<img src="skyline.svg" width="{w}" height="{h}" style="display:block"></body></html>', encoding="utf-8")
        png = tmp / "skyline.png"
        subprocess.run([browser(), "--headless", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
                        "--allow-file-access-from-files", "--virtual-time-budget=15000", f"--screenshot={png}", f"--window-size={w},{h}",
                        page.as_uri()], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        art = Image.open(png).convert("RGBA")
        for width in WIDTHS:
            img = art if width == w else art.resize((width, round(width * 760 / 2400)), Image.LANCZOS)
            target = OUT / f"skyline-{width}.webp"
            img.save(target, quality=84, method=6, alpha_quality=90)
            print(f"{target.relative_to(ROOT)}: {img.size[0]}x{img.size[1]}, {os.path.getsize(target) // 1024} KB")


if __name__ == "__main__":
    main()
