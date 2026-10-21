"""Draw the hero skyline as an ink-and-wash illustration.

    python tools/draw_skyline.py <art.svg> <src/partials/skyline.html>

The scene, looking into a sunset from a Bulgarian village: a Revival house with
a walnut tree, a stork, a well sweep, a stone fountain, haystacks and a lavender
field. On the horizon, smaller and hazier, the other homes: a Scottish tower
house on its crag, Valencia (Torres de Serranos, the Micalet, a blue-tiled dome,
an orange grove and a barraca) and the Netherlands (a windmill and canal houses).
The art SVG is rendered once to WebP (see README, "Skyline art"); the partial
holds the live layers drawn over it: the sun, glowing windows, chimney smoke,
the saltire and the windmill's sails.
Standard library only, and seeded, so the same code always draws the same scene.
"""
import math
import random
import sys
from pathlib import Path

W, H = 2400, 760
SUN = (930, 600)
INK = "#2b1608"
RIM = "#ffd38a"

DEFS = []
_IDS = set()
LIT = {"bg": [], "es": [], "sc": [], "nl": []}


# ---------------------------------------------------------------- helpers

def n(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def o(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def add_def(did, markup):
    if did not in _IDS:
        _IDS.add(did)
        DEFS.append(markup)


def poly(points):
    return "M" + " L".join(f"{n(x)} {n(y)}" for x, y in points) + " Z"


def line(points):
    return "M" + " L".join(f"{n(x)} {n(y)}" for x, y in points)


def smooth(points, closed=False):
    """Catmull-Rom through the points, as cubic Beziers."""
    p = ([points[-1]] + points + points[:2]) if closed else ([points[0]] + points + [points[-1]])
    d = f"M{n(p[1][0])} {n(p[1][1])}"
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{n(c1[0])} {n(c1[1])} {n(c2[0])} {n(c2[1])} {n(p2[0])} {n(p2[1])}"
    return d + (" Z" if closed else "")


def path(d, fill="none", stroke=None, w=1.5, op=None, extra=""):
    s = f'<path d="{d}" fill="{fill}"'
    if stroke:
        s += f' stroke="{stroke}" stroke-width="{n(w)}" stroke-linecap="round" stroke-linejoin="round"'
    if op is not None:
        s += f' opacity="{o(op)}"'
    return s + extra + "/>"


def ink(d, w=1.5, op=0.9):
    return path(d, "none", INK, w, op)


def rim(d, w=2.0, op=0.8):
    return path(d, "none", RIM, w, op)


def rect(x, y, w, h, fill, rx=0, op=None, stroke=None, sw=1.2, extra=""):
    s = f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{fill}"'
    if rx:
        s += f' rx="{n(rx)}"'
    if stroke:
        s += f' stroke="{stroke}" stroke-width="{n(sw)}"'
    if op is not None:
        s += f' opacity="{o(op)}"'
    return s + extra + "/>"


def ell(cx, cy, rx, ry, fill, op=None, stroke=None, sw=1.2, extra=""):
    s = f'<ellipse cx="{n(cx)}" cy="{n(cy)}" rx="{n(rx)}" ry="{n(ry)}" fill="{fill}"'
    if stroke:
        s += f' stroke="{stroke}" stroke-width="{n(sw)}"'
    if op is not None:
        s += f' opacity="{o(op)}"'
    return s + extra + "/>"


def group(items, filt=None, op=None, clip=None, extra=""):
    a = ""
    if filt:
        a += f' filter="url(#{filt})"'
    if op is not None:
        a += f' opacity="{o(op)}"'
    if clip:
        a += f' clip-path="url(#{clip})"'
    return f"<g{a}{extra}>" + "".join(items) + "</g>"


def _stops(stops):
    out = ""
    for st in stops:
        out += f'<stop offset="{o(st[0])}" stop-color="{st[1]}"' + (f' stop-opacity="{o(st[2])}"' if len(st) > 2 else "") + "/>"
    return out


def lin(gid, stops, x1=0, y1=0, x2=0, y2=1, user=None):
    """Linear gradient; user=(x1, y1, x2, y2) gives userSpaceOnUse coordinates."""
    if user:
        a = f'gradientUnits="userSpaceOnUse" x1="{n(user[0])}" y1="{n(user[1])}" x2="{n(user[2])}" y2="{n(user[3])}"'
    else:
        a = f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"'
    add_def(gid, f'<linearGradient id="{gid}" {a}>{_stops(stops)}</linearGradient>')
    return f"url(#{gid})"


def rad(gid, stops, cx, cy, r):
    add_def(gid, f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" cx="{n(cx)}" cy="{n(cy)}" r="{n(r)}">{_stops(stops)}</radialGradient>')
    return f"url(#{gid})"


def clip(cid, d):
    add_def(cid, f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
    return cid


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(lerp(x, y, t)):02x}" for x, y in zip(a, b))


def ridge(x0, x1, step, base, waves, seed, jitter=1.5):
    r = random.Random(seed)
    ph = [r.uniform(0, 6.283) for _ in waves]
    pts = []
    x = x0
    while x <= x1 + step:
        y = base + sum(a * math.sin(x * f + p) for (f, a), p in zip(waves, ph)) + r.uniform(-jitter, jitter)
        pts.append((x, y))
        x += step
    return pts


def y_on(pts, x):
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        if ax <= x <= bx:
            return lerp(ay, by, (x - ax) / (bx - ax))
    return pts[-1][1]


def hatch(x, y, w, h, op=0.45, pat="h1"):
    return rect(x, y, w, h, f"url(#{pat})", op=op)


def shade(x, y, w, h, side="right", strength=0.4, gid=None):
    """Darken one side of a face: the side turned away from the sun."""
    gid = gid or f"shade{side}{o(strength)}"
    stops = [(0, "#2a1830", 0), (1, "#2a1830", strength)]
    g = lin(gid, stops if side == "right" else stops[::-1], 0, 0, 1, 0)
    return rect(x, y, w, h, g)


def weathering(x0, x1, y0, y1, seed, count, col="#3a2418", op=0.14):
    """Soft rain streaks running down a wall."""
    r = random.Random(seed)
    out = []
    for _ in range(count):
        x = r.uniform(x0, x1)
        y = r.uniform(y0, y0 + (y1 - y0) * 0.35)
        ln = r.uniform((y1 - y0) * 0.2, (y1 - y0) * 0.65)
        out.append(path(f"M{n(x)} {n(y)} l{n(r.uniform(-1, 1))} {n(ln)}", "none", col, r.uniform(1.5, 4.5), op * r.uniform(0.5, 1)))
    return group(out, "blur3")


def hen(x, y, s=1.0, f=1, body="#efe6d8", seed=0):
    r = random.Random(seed)
    k = INK
    out = [path(poly([(x - f * 6 * s, y - 9 * s), (x - f * 13 * s, y - 17 * s), (x - f * 12 * s, y - 6 * s)]), mix(body, "#000000", 0.12)),
           ell(x, y - 7 * s, 8.5 * s, 6.2 * s, body), ell(x + f * 6.5 * s, y - 13 * s, 3.6 * s, 3.4 * s, body),
           path(f"M{n(x + f * 4.6 * s)} {n(y - 15.6 * s)} q{n(f * 1.4 * s)} {n(-3.4 * s)} {n(f * 2.8 * s)} {n(-0.4 * s)} q{n(f * 1.2 * s)} {n(-2.6 * s)} {n(f * 2.4 * s)} {n(0.6 * s)} Z", "#d8342a"),
           path(poly([(x + f * 9.6 * s, y - 13.6 * s), (x + f * 12.8 * s, y - 12.6 * s), (x + f * 9.6 * s, y - 11.6 * s)]), "#e0a030"),
           ell(x + f * 9 * s, y - 10.4 * s, 1 * s, 1.7 * s, "#d8342a"), ell(x + f * 7.6 * s, y - 13.8 * s, 0.7 * s, 0.7 * s, "#1e1612"),
           path(f"M{n(x - 1 * s)} {n(y - 1.5 * s)} v{n(4 * s)} M{n(x + 2.4 * s)} {n(y - 1.5 * s)} v{n(4 * s)}", "none", "#e0a030", 1.1 * s),
           ink(f"M{n(x - f * 4 * s)} {n(y - 9 * s)} q{n(f * 4 * s)} {n(4 * s)} {n(f * 8 * s)} {n(0)}", 0.9, 0.6),
           ink(smooth([(x - f * 8 * s, y - 4 * s), (x - f * 2 * s, y - 1 * s), (x + f * 6 * s, y - 3 * s), (x + f * 8 * s, y - 9 * s)]), 1, 0.7)]
    if body != "#efe6d8":
        out += [ell(x + r.uniform(-6, 6) * s, y - r.uniform(4, 10) * s, 1 * s, 0.8 * s, "#f0e0c8", 0.8) for _ in range(8)]
    return out


def wildflowers(x0, x1, y0, y1, seed, count):
    r = random.Random(seed)
    out = []
    for _ in range(count):
        x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        sz = 1.4 + (y - y0) / max(1, y1 - y0) * 1.6
        if r.random() < 0.5:
            out += [path(f"M{n(x)} {n(y + 6 * sz)} V{n(y)}", "none", "#4e6a2a", 0.9), ell(x, y, 2.2 * sz, 1.8 * sz, r.choice(["#d8241e", "#e83a2a", "#c01c18"])),
                    ell(x, y, 0.7 * sz, 0.7 * sz, "#1e1612")]
        else:
            out.append(path(f"M{n(x)} {n(y + 6 * sz)} V{n(y)}", "none", "#4e6a2a", 0.9))
            out += [ell(x + math.cos(a) * 1.6 * sz, y + math.sin(a) * 1.2 * sz, 1.1 * sz, 0.6 * sz, "#f6f0e2",
                        extra=f' transform="rotate({n(math.degrees(a))} {n(x + math.cos(a) * 1.6 * sz)} {n(y + math.sin(a) * 1.2 * sz)})"')
                    for a in [k * math.pi / 4 for k in range(8)]]
            out.append(ell(x, y, 0.9 * sz, 0.9 * sz, "#f0c030"))
    return out


# ---------------------------------------------------------------- filters and patterns

add_def("filters", '''
<filter id="hand" x="-3%" y="-6%" width="106%" height="112%" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="0.024" numOctaves="2" seed="3" result="n"/>
  <feDisplacementMap in="SourceGraphic" in2="n" scale="3" xChannelSelector="R" yChannelSelector="G"/>
</filter>
<filter id="wash" x="-6%" y="-12%" width="112%" height="124%" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="0.028" numOctaves="3" seed="8" result="n"/>
  <feDisplacementMap in="SourceGraphic" in2="n" scale="6" xChannelSelector="R" yChannelSelector="G" result="d"/>
  <feMorphology in="d" operator="erode" radius="1.6" result="e"/>
  <feComposite in="d" in2="e" operator="out" result="edge"/>
  <feColorMatrix in="edge" type="matrix" values="0.72 0 0 0 0  0 0.64 0 0 0  0 0 0.6 0 0  0 0 0 0.6 0" result="pool"/>
  <feMerge><feMergeNode in="d"/><feMergeNode in="pool"/></feMerge>
</filter>
<filter id="soft" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="9"/></filter>
<filter id="blur3" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>
<filter id="whiten" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 1 0"/></filter>
<filter id="paper" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
  <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="21" result="g"/>
  <feColorMatrix in="g" type="matrix" values="0 0 0 0 0.6  0 0 0 0 0.5  0 0 0 0 0.38  0.75 0 0 0 -0.28" result="gt"/>
  <feComposite in="gt" in2="SourceAlpha" operator="in" result="gm"/>
  <feBlend in="SourceGraphic" in2="gm" mode="multiply" result="b"/>
  <feTurbulence type="fractalNoise" baseFrequency="0.007" numOctaves="3" seed="5" result="m"/>
  <feColorMatrix in="m" type="matrix" values="0 0 0 0 1  0 0 0 0 0.93  0 0 0 0 0.82  0.55 0 0 0 -0.18" result="mt"/>
  <feComposite in="mt" in2="SourceAlpha" operator="in" result="mm"/>
  <feBlend in="b" in2="mm" mode="soft-light" result="out"/>
  <feComposite in="out" in2="SourceAlpha" operator="in"/>
</filter>
<pattern id="h1" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(-38)"><path d="M0 0 V5" stroke="#2b1608" stroke-width="0.9"/></pattern>
<pattern id="h2" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(40)"><path d="M0 0 V5" stroke="#2b1608" stroke-width="0.8"/></pattern>
<pattern id="h3" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(-38)"><path d="M0 0 V4" stroke="#2b1608" stroke-width="0.7"/></pattern>
<linearGradient id="tileG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6fd6dc"/><stop offset="0.5" stop-color="#2496a8"/><stop offset="1" stop-color="#145a6a"/></linearGradient>
''')

SCENE = []  # painter's order


# ---------------------------------------------------------------- sky: clouds, streaks and birds

def cloud(cx, cy, length, thick, seed, warm=0.5, op=1.0):
    """A dusk cloud: bumpy top, flat sunlit underside, watercolour edges."""
    r = random.Random(seed)
    nb = max(5, int(length / 55))
    x0, x1 = cx - length / 2, cx + length / 2
    pts = [(x0, cy + thick * 0.15)]
    for i in range(1, nb):
        t = i / nb
        env = math.sin(t * math.pi) ** 0.6
        pts.append((lerp(x0, x1, t) + r.uniform(-length / nb * 0.3, length / nb * 0.3), cy - env * thick * r.uniform(0.55, 1.0)))
    pts.append((x1, cy + thick * 0.1))
    bottom = []
    for i in range(1, 6):
        t = i / 6
        bottom.append((lerp(x1, x0, t) + r.uniform(-8, 8), cy + thick * 0.22 + thick * 0.12 * math.sin(t * math.pi) + r.uniform(-2, 2)))
    pts += bottom
    d = smooth(pts, closed=True)
    top_c, mid_c = mix("#6a5a8a", "#8a5a7e", warm), mix("#c88aa0", "#f0a08a", warm)
    bot_c = mix("#f0b8a8", "#ffe4a6", warm)
    g = lin(f"cl{seed}", [(0, top_c, 0.5 * op), (0.55, mid_c, 0.72 * op), (1, bot_c, (0.78 + 0.2 * warm) * op)],
            user=(0, cy - thick, 0, cy + thick * 0.35))
    lobes = []
    for _ in range(nb * 2):
        t = r.uniform(0.08, 0.92)
        env = math.sin(t * math.pi) ** 0.6
        lobes.append(ell(lerp(x0, x1, t), cy - env * thick * r.uniform(0.1, 0.5), r.uniform(20, 46), r.uniform(8, 18) * env + 4,
                         r.choice([mid_c, mix(mid_c, "#ffffff", 0.2), top_c]), 0.32 * op))
    underside = smooth([pts[nb]] + bottom + [pts[0]])
    return group([path(d, g, op=0.45, extra=' filter="url(#soft)"'),
                  group([path(d, g)] + lobes, "wash"),
                  path(underside, "none", mix("#ffd8b0", "#fff1c8", warm), 2.2, (0.35 + 0.55 * warm) * op)])


for args in [(860, 488, 760, 22, 5, 1.0), (1310, 446, 560, 30, 4, 0.85), (430, 458, 470, 24, 3, 0.7),
             (1770, 472, 520, 26, 7, 0.55), (2080, 186, 700, 46, 2, 0.15), (1590, 118, 460, 30, 1, 0.2),
             (2300, 360, 360, 30, 6, 0.3)]:
    SCENE.append(cloud(*args))
SCENE.append(cloud(110, 300, 300, 22, 8, 0.3, op=0.75))

streaks = []
r = random.Random(9)
for _ in range(16):
    x = r.uniform(420, 1520)
    y = r.uniform(522, 566)
    ln = r.uniform(80, 260)
    streaks.append(path(f"M{n(x)} {n(y)} q{n(ln / 2)} {n(r.uniform(-3, 3))} {n(ln)} {n(r.uniform(-2, 2))}", "none",
                        r.choice(["#ffe2a8", "#ffcf98", "#fff0c8"]), r.uniform(2, 5), r.uniform(0.25, 0.55)))
SCENE.append(group(streaks, "blur3"))

birds = []
for bx, by, s in [(1086, 398, 11), (1112, 384, 8), (1134, 406, 9), (1160, 378, 6), (1046, 414, 7), (1190, 392, 5), (1214, 402, 4)]:
    birds.append(ink(f"M{n(bx - s)} {n(by)} q{n(s * 0.5)} {n(-s * 0.55)} {n(s)} 0 q{n(s * 0.5)} {n(-s * 0.55)} {n(s)} 0", 1.7, 0.8))
SCENE.append(group(birds, "hand"))


# ---------------------------------------------------------------- far ranges and haze

def range_layer(pts, top, bottom, y0, y1, gid, ink_op=0.22, hatched=False, bottom_y=700):
    d = poly(pts + [(pts[-1][0], bottom_y), (pts[0][0], bottom_y)])
    items = [group([path(d, lin(gid, [(0, top), (1, bottom)], user=(0, y0, 0, y1)))], "wash"), ink(line(pts), 1.2, ink_op)]
    if hatched:
        items.append(group([path(d, "url(#h3)", op=0.12)], "hand"))
    return group(items)


balkan = ridge(-30, 1080, 10, 506, [(0.0045, 30), (0.013, 15), (0.04, 5)], 11)
SCENE.append(range_layer(balkan, "#a7b6b4", "#76898a", 450, 640, "rgBalkan", hatched=True))
highlands = ridge(1040, 1640, 10, 548, [(0.006, 20), (0.017, 9), (0.05, 3)], 23)
SCENE.append(range_layer(highlands, "#ab93b0", "#7a6687", 490, 640, "rgHigh", hatched=True))
vhills = ridge(1560, 2030, 10, 574, [(0.008, 8), (0.021, 4)], 24)
SCENE.append(range_layer(vhills, "#b9b49c", "#8e9278", 552, 640, "rgVal"))
SCENE.append(rect(-10, 560, W + 20, 80, lin("haze", [(0, "#ffc898", 0), (0.6, "#ffc898", 0.35), (1, "#ffd8a8", 0.5)]), op=0.9))
SCENE.append(group([ell(380, 600, 420, 18, "#fff0e8", 0.35), ell(1360, 604, 300, 14, "#f4e8ff", 0.3),
                    ell(1770, 608, 260, 12, "#fff4e0", 0.3), ell(2200, 610, 280, 12, "#f0f0ff", 0.3)], "soft"))


# ---------------------------------------------------------------- middle distance

foot = ridge(-30, 980, 8, 598, [(0.006, 12), (0.017, 7), (0.05, 2.5)], 31)
SCENE.append(range_layer(foot, "#97a160", "#6b7840", 570, 660, "rgFoot", ink_op=0.3))
vill = []
r = random.Random(41)
for x in [776, 808, 842, 870, 902, 938, 960]:
    y = y_on(foot, x) + 2
    w = r.uniform(9, 13)
    vill += [rect(x, y - 7, w, 7, "#efe2c6"), path(poly([(x - 2, y - 7), (x + w / 2, y - 12.5), (x + w + 2, y - 7)]), "#b14b2b"),
             rect(x + w * 0.35, y - 4.5, 2.2, 2.4, "#ffcf6e")]
vill += [rect(912, y_on(foot, 912) - 22, 6, 16, "#efe2c6"), path(poly([(910, y_on(foot, 912) - 22), (915, y_on(foot, 912) - 32), (920, y_on(foot, 912) - 22)]), "#8a7a6a")]
for x in [760, 792, 826, 888, 924, 952, 50, 240]:
    y = y_on(foot, x)
    hgt = r.uniform(26, 40)
    vill += [ell(x, y - hgt / 2, 4.2, hgt / 2, "#3e4a26"), ell(x + 1.4, y - hgt / 2 - 2, 2.2, hgt / 2 - 3, "#5f6c34")]
SCENE.append(group(vill, "hand"))

# The distant homes go here, once their drawing functions are defined (see the end of the file).
FAR_INDEX = len(SCENE)


# ---------------------------------------------------------------- ground, road and shadows

gpts = [(x, 646 + 6 * math.sin(x * 0.004) + 4 * math.sin(x * 0.011 + 1)) for x in range(-20, W + 40, 20)]
gfill = lin("ground", [(0, "#7a7a3e"), (0.26, "#958a4e"), (0.38, "#c49a60"), (0.6, "#d1a26a"), (0.75, "#a67f5c"), (1, "#6e4e58")], user=(0, 0, W, 0))
SCENE.append(group([path(poly(gpts + [(W + 40, H + 10), (-20, H + 10)]), gfill)], "wash"))

road_l = [(300, 770), (420, 724), (560, 698), (720, 682), (880, 672), (1060, 664), (1240, 657), (1420, 651), (1534, 648)]
road_r = [(1556, 648), (1440, 654), (1270, 661), (1090, 669), (920, 680), (760, 694), (620, 712), (520, 740), (470, 770)]
road = [group([path(smooth(road_l) + " L" + smooth(road_r)[1:] + " Z", "#e0b682", op=0.9)], "wash"),
        ink(smooth(road_l), 1.2, 0.45), ink(smooth(road_r), 1.2, 0.35)]
for k in (0.32, 0.68):
    rut = [(lerp(a[0], b[0], k), lerp(a[1], b[1], k)) for a, b in zip(road_l, road_r[::-1])]
    road.append(ink(smooth(rut), 1, 0.25))
r = random.Random(61)
for _ in range(70):
    t = r.random()
    x = lerp(330, 1530, t ** 1.3)
    y = lerp(760, 650, t ** 0.8) + r.uniform(-8, 8)
    road.append(ell(x, y, r.uniform(1.5, 3.5) * (1.4 - t), r.uniform(1, 2) * (1.4 - t), r.choice(["#b98e5e", "#a37a4e", "#f0cd9a"]), 0.8))
SCENE.append(group(road, "hand"))

# Long shadows fall toward the viewer, away from the low sun.
sh = "#2a1a24"
shadows = [path(poly([(342, 660), (692, 660), (610, 700), (250, 712), (300, 676)]), sh, op=0.28),
           path(poly([(-20, 662), (320, 662), (250, 690), (-20, 700)]), sh, op=0.22),
           path(poly([(1062, 664), (1158, 664), (1236, 690), (1112, 696)]), sh, op=0.24),
           path(poly([(901, 664), (911, 664), (990, 716), (972, 718)]), sh, op=0.2)]
SCENE.append(group(shadows, "wash"))

tufts = []
r = random.Random(62)
for _ in range(120):
    x = r.uniform(-10, 760)
    y = r.uniform(662, 735)
    s = r.uniform(5, 11) * (0.6 + (y - 660) / 120)
    col = r.choice(["#5a6a2e", "#6f7d36", "#86903f", "#4a5826"])
    for a in (-0.5, 0, 0.45):
        tufts.append(path(f"M{n(x)} {n(y)} q{n(a * s * 0.6)} {n(-s * 0.6)} {n(a * s * 1.2)} {n(-s)}", "none", col, 1.5, 0.95))
for _ in range(70):
    x = r.uniform(980, 1460)
    y = r.uniform(668, 748)
    s = r.uniform(4, 9) * (0.6 + (y - 660) / 120)
    for a in (-0.5, 0, 0.45):
        tufts.append(path(f"M{n(x)} {n(y)} q{n(a * s * 0.6)} {n(-s * 0.6)} {n(a * s * 1.2)} {n(-s)}", "none", r.choice(["#5a6a2e", "#6f7d36", "#86903f"]), 1.4, 0.9))
SCENE.append(group(tufts, "hand"))


# ---------------------------------------------------------------- Bulgaria: walnut tree

def walnut(cx, cy, rx, ry, tx, base_y, seed):
    r = random.Random(seed)
    trunk_pts = [(tx - 13, base_y), (tx - 7, cy + 40), (tx - 30, cy - 10), (tx - 24, cy - 16), (tx - 2, cy + 22), (tx + 4, cy - 30),
                 (tx + 12, cy - 28), (tx + 8, cy + 30), (tx + 34, cy + 4), (tx + 38, cy + 12), (tx + 12, cy + 48), (tx + 15, base_y)]
    trunk = [path(poly(trunk_pts), lin("walnutBark", [(0, "#3a2516"), (0.6, "#5e3f26"), (1, "#7a5432")], 0, 0, 1, 0)), ink(poly(trunk_pts), 1.4, 0.8)]
    for k in range(7):
        trunk.append(ink(f"M{n(tx - 8)} {n(base_y - 10 - k * 14)} q4 -5 9 -2", 1, 0.5))
    trunk.append(rim(f"M{n(tx + 14)} {n(base_y - 4)} L{n(tx + 11)} {n(cy + 48)}", 1.8, 0.6))
    blobs = []
    for _ in range(95):
        a = r.uniform(0, 6.283)
        d = math.sqrt(r.random())
        x = cx + math.cos(a) * rx * d
        y = cy + math.sin(a) * ry * d
        size = r.uniform(20, 44) * (1.1 - d * 0.35)
        light = (math.cos(a) * d * 0.6 - math.sin(a) * d * 0.5 + 1) / 2 + r.uniform(-0.12, 0.12)
        blobs.append((light, x, y, size, d, a))
    blobs.sort()
    leaves = [ell(x, y, s, s * 0.82, mix("#24321c", "#7f9244", light)) for light, x, y, s, d, a in blobs]
    tex = []
    for light, x, y, s, d, a in blobs:
        if light > 0.6 and r.random() < 0.55:
            for _ in range(3):
                lx, ly = x + r.uniform(-s * 0.5, s * 0.5), y + r.uniform(-s * 0.5, s * 0.2)
                tex.append(ell(lx, ly, 4.4, 2, mix("#6f8240", "#a3b25e", light - 0.5), 0.7, extra=f' transform="rotate({n(r.uniform(-60, 60))} {n(lx)} {n(ly)})"'))
        if d > 0.7:
            p0 = (x + math.cos(a - 0.9) * s, y + math.sin(a - 0.9) * s * 0.82)
            p1 = (x + math.cos(a + 0.9) * s, y + math.sin(a + 0.9) * s * 0.82)
            tex.append(ink(f"M{n(p0[0])} {n(p0[1])} A{n(s)} {n(s * 0.82)} 0 0 1 {n(p1[0])} {n(p1[1])}", 1.3, 0.5))
            if math.cos(a) > 0.2:
                tex.append(rim(f"M{n(p0[0])} {n(p0[1])} A{n(s)} {n(s * 0.82)} 0 0 1 {n(p1[0])} {n(p1[1])}", 1.4, 0.45))
        if light < 0.32:
            tex.append(ell(x, y + s * 0.2, s * 0.7, s * 0.5, "url(#h1)", 0.2))
    limbs = [ink(f"M{n(tx + 6)} {n(cy + 10)} q{n(-30)} {n(-30)} {n(-70)} {n(-40)}", 3, 0.55),
             ink(f"M{n(tx + 6)} {n(cy + 4)} q{n(30)} {n(-40)} {n(80)} {n(-50)}", 3, 0.5),
             ink(f"M{n(tx + 2)} {n(cy - 20)} q{n(4)} {n(-30)} {n(-6)} {n(-60)}", 2.4, 0.45)]
    nuts = [ell(cx + r.uniform(-rx * 0.6, rx * 0.7), cy + r.uniform(-ry * 0.4, ry * 0.6), 2.8, 2.8, "#8a9a4c") for _ in range(12)]
    return group([group(trunk, "hand"), group(leaves, "wash"), group(limbs, "hand", op=0.8), group(tex + nuts, "hand")])


SCENE.append(walnut(122, 455, 168, 122, 128, 604, 71))


# ---------------------------------------------------------------- Bulgaria: garden wall, gate, house

def rubble(x0, y0, x1, y1, seed, colors, row=(9, 15), width=(13, 28)):
    r = random.Random(seed)
    out = [rect(x0, y0, x1 - x0, y1 - y0, "#8a7864")]
    y = y0
    while y < y1:
        h = r.uniform(*row)
        x = x0 - r.uniform(0, 12)
        while x < x1:
            w = r.uniform(*width)
            sx, sy = max(x0, x) + 1.1, y + 1.1
            sw, sh_ = min(x + w, x1) - sx - 1.1, min(y + h, y1) - sy - 1.1
            if sw > 3 and sh_ > 3:
                out.append(rect(sx, sy, sw, sh_, r.choice(colors), rx=min(sw, sh_) * r.uniform(0.3, 0.5), stroke=INK, sw=0.7, extra=' stroke-opacity="0.45"'))
            x += w
        y += h
    return out


def tiles_rows(x_at, y0, y1, step_y, step_x, seed, base, lit_from_right=True):
    """Barrel tiles: rows of small arches between the roof edges given by x_at(y) -> (left, right)."""
    r = random.Random(seed)
    out = []
    y = y0
    while y < y1:
        xl, xr = x_at(y + step_y)
        x = xl - r.uniform(0, step_x)
        while x < xr:
            t = (x - xl) / max(1, xr - xl)
            col = mix(base, "#e58a56", (t if lit_from_right else 1 - t) * 0.5 + r.uniform(-0.1, 0.1))
            out.append(path(f"M{n(x)} {n(y + step_y)} q{n(step_x / 2)} {n(-step_y * 0.75)} {n(step_x)} 0 V{n(y)} h{n(-step_x)} Z", col))
            out.append(ink(f"M{n(x)} {n(y + step_y)} q{n(step_x / 2)} {n(-step_y * 0.75)} {n(step_x)} 0", 0.9, 0.55))
            x += step_x
        y += step_y
    return out


def geraniums(x, y, seed):
    r = random.Random(seed)
    pot = [(x - 7, y - 9), (x + 7, y - 9), (x + 5, y), (x - 5, y)]
    out = [path(poly(pot), "#b8603a"), ink(poly(pot), 0.9, 0.7)]
    out += [ell(x + r.uniform(-9, 9), y - 11 - r.uniform(0, 5), 3.2, 2.2, "#4f6a2e") for _ in range(6)]
    out += [ell(x + r.uniform(-8, 8), y - 14 - r.uniform(0, 7), 2.2, 2.2, r.choice(["#e0303c", "#ff5a52", "#c21e32"])) for _ in range(9)]
    return out


def window(x, y, w, h, key, shutter="#355e5c"):
    out = [rect(x - 15, y - 1, 13, h + 2, shutter, stroke=INK, sw=1), rect(x + w + 2, y - 1, 13, h + 2, shutter, stroke=INK, sw=1)]
    for sx in (x - 15, x + w + 2):
        for k in range(3):
            out.append(ink(f"M{n(sx + 2)} {n(y + 6 + k * (h / 3))} h9", 0.8, 0.55))
    out += [rect(x - 3, y - 3, w + 6, h + 6, "#4a2a12"), rect(x, y, w, h, lin("pane", [(0, "#ffe9a8"), (1, "#f2a24a")])),
            ink(f"M{n(x + w / 2)} {n(y)} V{n(y + h)} M{n(x)} {n(y + h * 0.45)} H{n(x + w)}", 2, 0.9),
            ink(poly([(x - 3, y - 3), (x + w + 3, y - 3), (x + w + 3, y + h + 3), (x - 3, y + h + 3)]), 1.2, 0.8),
            rect(x - 6, y + h + 3, w + 12, 4, "#6a4424", stroke=INK, sw=0.9)]
    LIT[key].append((x, y, w, h))
    return out


def peppers(x, top, length, seed):
    """A string of red peppers drying under the eaves."""
    r = random.Random(seed)
    out = [ink(f"M{n(x)} {n(top)} V{n(top + length)}", 0.8, 0.8)]
    y = top + 5
    while y < top + length:
        for side in (-1, 1):
            a = side * r.uniform(12, 38)
            out.append(ell(x + side * 3.5, y + 3, 2.3, 6.5, r.choice(["#c0241e", "#d8332a", "#a81c18", "#e04a2a"]),
                           extra=f' transform="rotate({n(a)} {n(x)} {n(y)})"'))
        y += 6.5
    out.append(ell(x, top + length + 2, 2, 3, "#5a6a2a"))
    return out


def cat(x, y, s=1.0):
    """A cat on the garden wall, watching the sunset."""
    k = "#1e1612"
    out = [ell(x, y - 10 * s, 7.5 * s, 10 * s, k), ell(x + 3.5 * s, y - 22 * s, 5.6 * s, 5 * s, k),
           path(poly([(x - 0.5 * s, y - 24 * s), (x + 1 * s, y - 31 * s), (x + 3.5 * s, y - 26 * s)]), k),
           path(poly([(x + 4.5 * s, y - 26 * s), (x + 7.5 * s, y - 31 * s), (x + 8.5 * s, y - 23.5 * s)]), k),
           path(f"M{n(x - 6 * s)} {n(y - 2 * s)} q{n(-13 * s)} {n(2 * s)} {n(-11 * s)} {n(-13 * s)}", "none", k, 2.6 * s),
           rim(f"M{n(x + 7 * s)} {n(y - 14 * s)} q{n(1.5 * s)} {n(6 * s)} {n(0.5 * s)} {n(12 * s)} M{n(x + 8.6 * s)} {n(y - 24 * s)} q{n(0.8 * s)} {n(2 * s)} {n(0)} {n(4 * s)}", 1.2, 0.85)]
    return out


def bulgarian_house():
    out = []
    wall = rubble(-20, 600, 320, 660, 81, ["#bcaa8e", "#a8967a", "#cbb99c", "#9e8c72"])
    wall += tiles_rows(lambda y: (-24, 324), 588, 600, 6, 9, 82, "#9a3c22")
    wall += [ink(line([(-24, 600), (324, 600)]), 1.4, 0.8), hatch(-20, 600, 340, 14, 0.3)]
    wall += cat(168, 589, 1.1)
    out.append(group(wall, "hand"))
    gate = [rect(212, 560, 9, 100, "#5a3818", stroke=INK, sw=1.2), rect(283, 560, 9, 100, "#5a3818", stroke=INK, sw=1.2),
            rect(221, 572, 62, 88, lin("gateWood", [(0, "#7a4e28"), (1, "#5a3618")], 0, 0, 1, 0))]
    gate += [ink(f"M{n(221 + k * 9)} 572 V660", 0.9, 0.6) for k in range(7)]
    gate += [ink("M252 572 V660", 1.8, 0.9), ell(247, 618, 2.2, 2.2, "#c9a35a"), ell(257, 618, 2.2, 2.2, "#c9a35a")]
    gate += [ell(xx, yy, 1.1, 1.1, INK, 0.7) for yy in (584, 640) for xx in range(226, 282, 9)]
    gate += tiles_rows(lambda y: (204 + (562 - y) * 0.9, 300 - (562 - y) * 0.9), 548, 562, 7, 8, 83, "#a8442a")
    gate.append(ink(poly([(200, 562), (226, 546), (278, 546), (304, 562)]), 1.4, 0.85))
    out.append(group(gate, "hand"))

    house = rubble(342, 548, 692, 658, 91, ["#c9b597", "#b8a284", "#d6c3a2", "#a99377"], row=(10, 16), width=(14, 30))
    house += [hatch(342, 548, 350, 30, 0.35), shade(342, 548, 350, 110, "left", 0.3, "houseShade")]
    house.append(path("M380 658 V604 A26 22 0 0 1 432 604 V658 Z", lin("doorWood", [(0, "#6a4222"), (1, "#4a2c14")], 0, 0, 1, 0)))
    house += [ink(f"M{n(386 + k * 10)} 604 V658", 0.9, 0.6) for k in range(5)]
    house += [ink("M406 588 V658", 1.6, 0.9), ink("M380 658 V604 A26 22 0 0 1 432 604 V658", 1.6, 0.9)]
    for k in range(9):
        a = math.pi * (1 - k / 8)
        house.append(ink(f"M{n(406 + math.cos(a) * 26)} {n(604 - math.sin(a) * 22)} L{n(406 + math.cos(a) * 36)} {n(604 - math.sin(a) * 32)}", 1.1, 0.7))
    house += [ink("M370 604 A36 32 0 0 1 442 604", 1.3, 0.8), ell(414, 630, 3.2, 3.2, "none", stroke="#c9a35a", sw=1.4)]
    house += [rect(596, 584, 34, 28, "#3a2414"), rect(599, 587, 28, 22, lin("cellarLit", [(0, "#ffd88a"), (1, "#d88a3e")]))]
    LIT["bg"].append((599, 587, 28, 22))
    house += [ink(f"M{n(603 + k * 7)} 587 V609", 1.6, 0.85) for k in range(4)]
    house += [rect(450, 634, 58, 6, "#7a5230", stroke=INK, sw=1), ink("M455 640 V656 M503 640 V656", 2, 0.85)]
    house += [rect(536, 626, 30, 30, "#7a5230", stroke=INK, sw=1), ink("M536 636 H566 M536 646 H566", 0.9, 0.6),
              path("M540 626 Q551 612 562 626", "none", "#c9a35a", 1.6)]
    out.append(group(house, "hand"))

    up = []
    for bx in (350, 430, 510, 590, 670):
        up.append(path(f"M{n(bx - 3)} 548 Q{n(bx - 4)} 572 {n(bx + 10)} 586 L{n(bx + 14)} 582 Q{n(bx + 4)} 570 {n(bx + 5)} 548 Z", "#5a3418"))
        up.append(ink(f"M{n(bx - 3)} 548 Q{n(bx - 4)} 572 {n(bx + 10)} 586 L{n(bx + 14)} 582 Q{n(bx + 4)} 570 {n(bx + 5)} 548", 1, 0.8))
    up += [rect(312, 540, 408, 10, "#5a3418", stroke=INK, sw=1.2),
           rect(312, 438, 408, 102, lin("whitewash", [(0, "#f7e8ca"), (0.7, "#ecd4ac"), (1, "#dcbc90")])),
           hatch(312, 438, 408, 26, 0.3), rect(312, 446, 408, 14, "#7ea6b4")]
    up.append(path("M312 453 " + " ".join(f"L{n(312 + i * 8)} {n(449 if i % 2 else 457)}" for i in range(1, 52)), "none", "#a8402a", 2, 0.95))
    up += [ell(316 + i * 16, 453, 1.6, 1.6, "#f6e6c4") for i in range(26)]
    up.append(ink("M312 446 H720 M312 460 H720", 1, 0.7))
    up += [rect(tx, 438, 6, 102, "#5a3418", stroke=INK, sw=0.9) for tx in (312, 392, 472, 552, 632, 714)]
    for wx in (348, 428, 508, 588):
        up += window(wx, 474, 34, 46, "bg")
        up += geraniums(wx + 17, 530, wx)
    up += [rect(638, 462, 76, 78, "#6a4a30"), rect(652, 470, 30, 50, lin("chardakDoor", [(0, "#ffdc90"), (1, "#e08a44")]))]
    LIT["bg"].append((652, 470, 30, 50))
    up += [rect(px, 462, 5, 78, "#5a3418", stroke=INK, sw=0.8) for px in (640, 676, 708)]
    up.append(rect(638, 504, 76, 4, "#5a3418"))
    up += [rect(bx, 508, 2.4, 32, "#6a4424") for bx in range(642, 712, 6)]
    kil = [rect(646, 500, 56, 38, "#a8302a")]
    for i, kx in enumerate((656, 674, 692)):
        kil += [path(poly([(kx, 506), (kx + 8, 519), (kx, 532), (kx - 8, 519)]), "#1e1612"),
                path(poly([(kx, 512), (kx + 4, 519), (kx, 526), (kx - 4, 519)]), "#e9d2a0" if i != 1 else "#3a6a5a")]
    kil += [rect(646, 500, 56, 4, "#1e1612"), rect(646, 534, 56, 4, "#1e1612")]
    kil += [ink(f"M{n(fx)} 538 v5", 0.8, 0.7) for fx in range(647, 702, 3)]
    up += kil
    up += [shade(312, 438, 408, 102, "left", 0.25, "upShade"), ink(poly([(312, 438), (720, 438), (720, 550), (312, 550)]), 1.6, 0.9),
           rim("M720 440 V548", 2.6, 0.9)]
    up += peppers(330, 441, 52, 1) + peppers(622, 441, 44, 2)
    out.append(group(up, "hand"))

    vine = [path("M704 658 C700 630 716 616 708 596 C700 578 716 566 712 552", "none", "#5a3a20", 4, 1),
            ink("M704 658 C700 630 716 616 708 596 C700 578 716 566 712 552", 1, 0.8)]
    r = random.Random(97)
    for _ in range(38):
        x = r.uniform(652, 766)
        y = r.uniform(548, 600) if x > 700 else r.uniform(548, 566)
        vine.append(path(f"M{n(x)} {n(y)} l-6 -4 l2 -6 l5 3 l3 -6 l4 6 l5 -2 l-1 7 l4 3 l-8 3 Z", r.choice(["#4e6a2a", "#6a8434", "#3e5624", "#86983e"])))
    for gx, gy in ((728, 590), (750, 578), (690, 572)):
        vine += [ell(gx + r.uniform(-5, 5), gy + r.uniform(0, 14), 2.8, 2.8, r.choice(["#5a2a5e", "#743a7a", "#4a2050"])) for _ in range(9)]
    out.append(group(vine, "hand"))

    roof = [rect(284, 432, 466, 9, "#4a2a12")]
    roof += [rect(rx_, 436, 7, 6, "#6a4424") for rx_ in range(290, 748, 18)]
    roof_poly = [(282, 434), (430, 352), (602, 352), (750, 434)]
    roof.append(path(poly(roof_poly), lin("roofBase", [(0, "#8a3420"), (1, "#c45a32")], 0, 0, 1, 0)))
    roof.append(group(tiles_rows(lambda y: (282 + (434 - y) * (148 / 82), 750 - (434 - y) * (148 / 82)), 352, 434, 8, 11, 101, "#a3402a"),
                      clip=clip("roofClip", poly(roof_poly))))
    roof += [path("M430 352 H602", "none", "#7a2e18", 5), ink("M430 352 H602", 1.2, 0.9), ink(poly(roof_poly), 1.8, 0.95),
             rim("M602 353 L748 433", 2.4, 0.85), rim("M432 352 H600", 1.6, 0.6), hatch(284, 441, 466, 6, 0.4)]
    roof += [rect(548, 326, 26, 34, lin("chim", [(0, "#efdcbc"), (1, "#c9ae88")], 0, 0, 1, 0), stroke=INK, sw=1.3),
             rect(544, 321, 34, 6, "#6a3a20", stroke=INK, sw=1.1), ink("M556 336 h10 M552 346 h18", 0.9, 0.5)]
    out.append(group(roof, "hand"))

    st = []
    r = random.Random(111)
    for _ in range(60):
        x = 561 + r.uniform(-24, 24)
        y = 318 + r.uniform(-5, 4)
        a = r.uniform(-0.5, 0.5)
        st.append(path(f"M{n(x)} {n(y)} l{n(math.cos(a) * 11)} {n(math.sin(a) * 4)}", "none", r.choice(["#5a3a1e", "#7a5430", "#3e2814"]), 1.6))
    sx, sy = 556, 312
    st += [path(f"M{n(sx - 2)} {n(sy)} l-1 -22 M{n(sx + 3)} {n(sy)} l0 -22", "none", "#d8442a", 1.6),
           ell(sx + 3, sy - 30, 14, 7.5, "#f6f0e4", stroke=INK, sw=1.2, extra=f' transform="rotate(-12 {n(sx + 3)} {n(sy - 30)})"'),
           path(f"M{n(sx - 3)} {n(sy - 26)} L{n(sx + 17)} {n(sy - 24)} L{n(sx + 13)} {n(sy - 32)} L{n(sx + 1)} {n(sy - 32)} Z", "#1e1a18"),
           path(f"M{n(sx - 7)} {n(sy - 33)} Q{n(sx - 14)} {n(sy - 42)} {n(sx - 11)} {n(sy - 50)}", "none", "#f6f0e4", 5),
           ink(f"M{n(sx - 4)} {n(sy - 33)} Q{n(sx - 12)} {n(sy - 42)} {n(sx - 9)} {n(sy - 51)}", 1, 0.7),
           ell(sx - 11, sy - 52, 4, 3.6, "#f6f0e4", stroke=INK, sw=1),
           path(f"M{n(sx - 14)} {n(sy - 52)} L{n(sx - 29)} {n(sy - 44)} L{n(sx - 14)} {n(sy - 50)} Z", "#d8442a", stroke=INK, w=0.8),
           ell(sx - 12, sy - 53, 0.9, 0.9, "#1e1a18"), rim(f"M{n(sx + 15)} {n(sy - 33)} q2 4 -2 8", 1.4, 0.8)]
    out.append(group(st, "hand"))
    return group(out)


SCENE.append(bulgarian_house())


def well_sweep():
    stone = rubble(776, 628, 846, 662, 121, ["#b5a083", "#a28e72", "#c4b092"], row=(8, 12), width=(10, 18))
    out = [group(stone, clip=clip("wellClip", "M776 630 H846 V662 Q811 670 776 662 Z")),
           ell(811, 630, 35, 9, "#a8937a", stroke=INK, sw=1.3), ell(811, 630, 27, 6, "#2a1a10"), ink("M776 630 V662 Q811 670 846 662 V630", 1.4, 0.9)]
    wood = "#3a2414"
    out += [path("M901 664 L903 524 L909 524 L911 664 Z", wood), ink("M901 664 L903 524 M911 664 L909 524", 1.2, 0.9),
            path("M903 528 L895 510 M909 528 L917 510", "none", wood, 5), ink("M903 528 L895 510 M909 528 L917 510", 1, 0.9),
            path("M800 418 L980 590", "none", wood, 6.5), ink("M798 416 L982 592", 1, 0.6), rim("M802 415 L978 583", 1.8, 0.85),
            ell(978, 594, 14, 10, "#6a5a4a", stroke=INK, sw=1.2), path("M966 590 Q978 584 990 592", "none", "#8a6a4a", 1.6),
            ink("M800 418 L801 560", 1.1, 0.9), path("M792 560 L810 560 L807 580 L795 580 Z", "#6a4424", stroke=INK, w=1.1),
            ink("M793 560 Q801 550 809 560", 1, 0.8), rim("M909 528 V662", 1.4, 0.7)]
    return group(out, "hand")


SCENE.append(well_sweep())
SCENE.append(group(wildflowers(300, 760, 676, 736, 131, 46) + hen(520, 700, 1.25, 1, "#efe6d8", 1) + hen(566, 712, 1.3, -1, "#b8642a", 2)
                   + hen(476, 716, 1.2, 1, "#8a5a3a", 3), "hand"))


# ---------------------------------------------------------------- stone and domes

def ashlar(x0, y0, x1, y1, seed, top="#e9bc82", bottom="#bf8650", row=11):
    r = random.Random(seed)
    out = [rect(x0, y0, x1 - x0, y1 - y0, lin(f"ash{seed}", [(0, top), (1, bottom)]))]
    y = y0
    k = 0
    while y < y1:
        out.append(ink(f"M{n(x0)} {n(y)} H{n(x1)}", 0.7, 0.35))
        x = x0 + (r.uniform(4, 16) if k % 2 else 0)
        while x < x1:
            w = r.uniform(18, 32)
            out.append(rect(x + 0.5, y + 0.5, min(w, x1 - x) - 1, min(row, y1 - y) - 1, r.choice(["#ffffff", "#000000"]), op=r.uniform(0.02, 0.07)))
            out.append(ink(f"M{n(x)} {n(y)} V{n(min(y + row, y1))}", 0.6, 0.3))
            x += w
        y += row
        k += 1
    return out


def dome(cx, base, rx, ry, seed, colours, lat_n=7, lon_n=14):
    r = random.Random(seed)
    out = []

    def pt(lat, lon):
        return (cx + rx * math.cos(lat) * math.sin(lon), base - ry * math.sin(lat))
    for i in range(lat_n):
        la0, la1 = (math.pi / 2) * i / lat_n, (math.pi / 2) * (i + 1) / lat_n
        for j in range(lon_n):
            lo0, lo1 = -math.pi / 2 + math.pi * j / lon_n, -math.pi / 2 + math.pi * (j + 1) / lon_n
            q = [pt(la0, lo0), pt(la0, (lo0 + lo1) / 2), pt(la0, lo1), pt(la1, lo1), pt(la1, (lo0 + lo1) / 2), pt(la1, lo0)]
            out.append(path(poly(q), colours[(i + j) % 2] if r.random() > 0.08 else colours[2]))
    for j in range(lon_n + 1):
        lo = -math.pi / 2 + math.pi * j / lon_n
        out.append(ink(line([pt(math.pi / 2 * k / 16, lo) for k in range(17)]), 0.7, 0.5))
    for i in range(1, lat_n):
        la = math.pi / 2 * i / lat_n
        out.append(ink(line([pt(la, -math.pi / 2 + math.pi * k / 24) for k in range(25)]), 0.6, 0.4))
    gid = f"domeShade{seed}"
    add_def(gid, f'<radialGradient id="{gid}" cx="0.3" cy="0.42" r="0.8"><stop offset="0" stop-color="#fff4d0" stop-opacity="0.55"/>'
                 f'<stop offset="0.45" stop-color="#ffffff" stop-opacity="0"/><stop offset="1" stop-color="#0a1a24" stop-opacity="0.6"/></radialGradient>')
    shell = f"M{n(cx - rx)} {n(base)} A{n(rx)} {n(ry)} 0 0 1 {n(cx + rx)} {n(base)} Z"
    out += [path(shell, f"url(#{gid})"), ink(shell, 1.6, 0.95),
            rim(f"M{n(cx - rx + 2)} {n(base - 2)} A{n(rx)} {n(ry)} 0 0 1 {n(cx - rx * 0.2)} {n(base - ry * 0.98)}", 2.4, 0.8)]
    return out


# ---------------------------------------------------------------- Scotland: crag, heather, pines, tower house, cow

def heather(x, y, w, seed):
    r = random.Random(seed)
    out = [ell(x, y, w, w * 0.42, r.choice(["#3e4a2a", "#4a4a2e", "#54502e"]))]
    for _ in range(int(w * 1.6)):
        px = x + r.uniform(-w * 0.9, w * 0.9)
        py = y - r.uniform(0, w * 0.45) + abs(px - x) / w * w * 0.22
        out.append(ell(px, py, r.uniform(1.3, 2.5), r.uniform(1.1, 1.9), r.choice(["#b77cc2", "#9a5aa8", "#c99ad0", "#8a4a98"])))
    return out


def scots_pine(x, y, h, seed, lean=0.0):
    r = random.Random(seed)
    top = (x + lean * h, y - h)
    trunk_d = (f"M{n(x - 6)} {n(y)} Q{n(x - 2)} {n(y - h * 0.5)} {n(top[0] - 2)} {n(top[1] + 20)} "
               f"L{n(top[0] + 2)} {n(top[1] + 20)} Q{n(x + 4)} {n(y - h * 0.5)} {n(x + 6)} {n(y)} Z")
    items = [path(trunk_d, lin(f"pine{seed}", [(0, "#c8623a"), (0.45, "#a84a2c"), (1, "#3a2418")])), ink(trunk_d, 1.1, 0.85)]
    items += [ink(f"M{n(lerp(x, top[0], t) - 3)} {n(lerp(y, top[1], t))} q3 -2 6 0", 0.8, 0.5) for t in (0.15, 0.3, 0.45, 0.6)]
    clumps = []
    for k in range(4):
        cy = top[1] + 8 + k * h * 0.11
        cx = top[0] + (-1 if k % 2 else 1) * r.uniform(10, 34) * (0.6 + k * 0.15)
        wdt = r.uniform(44, 70) * (0.75 + k * 0.12)
        clumps.append((cx, cy, wdt))
        anchor = (lerp(x, top[0], 1 - k * 0.16), lerp(y, top[1], 1 - k * 0.16) + 6)
        items.append(path(f"M{n(anchor[0])} {n(anchor[1])} Q{n((cx + anchor[0]) / 2)} {n(cy + 6)} {n(cx)} {n(cy + 2)}", "none", "#4a2c1e", 3))
    mass, needles = [], []
    for cx, cy, wdt in clumps:
        mass.append(ell(cx, cy + 5, wdt / 2, 9, "#1a2416"))
        for j in range(9):
            ex = cx + r.uniform(-wdt * 0.45, wdt * 0.45)
            ey = cy + r.uniform(-7, 3)
            lit = ex < cx
            mass.append(ell(ex, ey, r.uniform(9, 16), r.uniform(5, 8), mix("#22301c", "#5f7238", 0.75 if lit else 0.25)))
        for j in range(26):
            a = r.uniform(math.pi, 2 * math.pi)
            ex = cx + math.cos(a) * wdt * 0.5 * r.uniform(0.7, 1.05)
            ey = cy + math.sin(a) * 9 * r.uniform(0.7, 1.1)
            needles.append(path(f"M{n(ex)} {n(ey)} l{n(math.cos(a) * 5)} {n(math.sin(a) * 4)}", "none", "#2a3a22" if ex > cx else "#7a8c48", 1.2))
        needles.append(rim(f"M{n(cx - wdt * 0.45)} {n(cy - 3)} q{n(wdt * 0.2)} {n(-8)} {n(wdt * 0.45)} {n(-7)}", 1.3, 0.55))
    return group([group(items, "hand"), group(mass, "wash"), group(needles, "hand")])


def slate_cone(x0, x1, base, apex, seed):
    cx = (x0 + x1) / 2
    shape = poly([(x0, base), (cx, apex), (x1, base)])
    rows = []
    y = apex + 6
    k = 0
    while y < base:
        half = (x1 - x0) / 2 * (y - apex) / (base - apex)
        x = cx - half - (3 if k % 2 else 0)
        while x < cx + half:
            rows.append(path(f"M{n(x)} {n(y)} q3 5 6 0", "none", INK, 0.6, 0.6))
            x += 6
        y += 5
        k += 1
    return [path(shape, lin(f"slate{seed}", [(0, "#8a94a6"), (0.5, "#4a5468"), (1, "#2e3444")], 0, 0, 1, 0)),
            group(rows, clip=clip(f"cone{seed}", shape)), ink(shape, 1.3, 0.95), rim(f"M{n(x0 + 1)} {n(base - 1)} L{n(cx)} {n(apex + 1)}", 1.8, 0.8)]


def scottish_castle():
    out = []
    sil = [(1812, 700), (1850, 676), (1876, 652), (1904, 626), (1928, 604), (1950, 584), (1964, 570), (1988, 562), (2050, 564), (2120, 557), (2200, 561),
           (2268, 559), (2300, 572), (2328, 596), (2360, 620), (2412, 634), (2412, 704)]
    cr = [path(poly(sil), lin("cragBase", [(0, "#5a4652"), (1, "#3a2c38")]))]
    facets = [([(1876, 652), (1904, 626), (1928, 604), (1950, 584), (1964, 570), (1988, 562), (1996, 586), (1978, 612), (1956, 640), (1926, 668), (1890, 676)], "#b08068"),
              ([(1988, 562), (2050, 564), (2060, 590), (2040, 620), (2010, 648), (1978, 672), (1956, 640), (1978, 612), (1996, 586)], "#8e6c66"),
              ([(2050, 564), (2120, 557), (2128, 584), (2110, 612), (2080, 640), (2060, 668), (2010, 648), (2040, 620), (2060, 590)], "#7a5e62"),
              ([(2120, 557), (2200, 561), (2210, 592), (2186, 626), (2150, 660), (2080, 640), (2110, 612), (2128, 584)], "#6a5260"),
              ([(2200, 561), (2268, 559), (2300, 572), (2328, 596), (2300, 626), (2250, 652), (2186, 626), (2210, 592)], "#58445a")]
    for pts, col in facets:
        cr += [path(poly(pts), col), ink(poly(pts), 0.9, 0.45)]
    r = random.Random(181)
    for _ in range(16):
        x0, y0 = r.uniform(1890, 2300), r.uniform(574, 664)
        cr.append(ink(f"M{n(x0)} {n(y0)} q{n(r.uniform(10, 30))} {n(r.uniform(-3, 3))} {n(r.uniform(30, 70))} {n(r.uniform(-2, 4))}", 0.8, 0.4))
    for _ in range(24):
        x0, y0 = r.uniform(1900, 2320), r.uniform(568, 644)
        cr.append(ink(f"M{n(x0)} {n(y0)} l{n(r.uniform(-5, 5))} {n(r.uniform(10, 30))}", 0.9, 0.5))
    cr += [path(poly([(1904, 626), (1928, 604), (1950, 584), (1964, 570), (1980, 590), (1950, 630), (1920, 652)]), "url(#h1)", op=0.18),
           rim(line(sil[2:8]), 2.6, 0.85), rim(line(sil[7:12]), 1.4, 0.5)]
    for _ in range(60):
        x0, y0 = r.uniform(1900, 2320), r.uniform(572, 660)
        cr.append(ell(x0, y0, r.uniform(1.5, 3.5), r.uniform(1, 2.2), r.choice(["#b8b08a", "#9aa07a", "#c8c09a"]), 0.6))
    for _ in range(30):
        x0, y0 = r.uniform(1900, 2320), r.uniform(578, 660)
        cr += [path(f"M{n(x0)} {n(y0)} q{n(a * 3)} -5 {n(a * 6)} -8", "none", "#5a6a3a", 1.2, 0.9) for a in (-1, 0.2, 1)]
    grass_top = [(1962, 572), (1990, 562), (2050, 565), (2120, 558), (2200, 562), (2268, 560), (2298, 572), (2270, 575), (2200, 571), (2120, 569), (2050, 575), (1990, 573)]
    cr.append(path(smooth(grass_top, closed=True), "#5a6a3a"))
    for k in range(7):
        cr += heather(1980 + k * 46 + r.uniform(-8, 8), 570 + r.uniform(-2, 2), r.uniform(12, 20), 300 + k)
    for _ in range(40):
        x = r.uniform(1860, 2400)
        y = r.uniform(668, 706)
        cr.append(ell(x, y, r.uniform(2, 5), r.uniform(1.5, 3), r.choice(["#6a5660", "#7a646a", "#54444e"]), stroke=INK, sw=0.6))
    out.append(group(cr, "hand"))

    moor_h = []
    for k in range(22):
        moor_h += heather(1830 + k * 27 + r.uniform(-10, 10), 640 + r.uniform(-14, 30), r.uniform(10, 24), 400 + k)
    for k in range(26):
        moor_h += heather(1800 + k * 24 + r.uniform(-8, 8), 690 + r.uniform(-8, 12), r.uniform(16, 28), 500 + k)
    out.append(group(moor_h, "hand"))
    out.append(scots_pine(1906, 646, 196, 191, -0.04))

    bk = [rect(1958, 516, 86, 48, lin("harlB", [(0, "#ead8b8"), (1, "#c2ac8c")], 0, 0, 1, 0))]
    bk += [rect(1960 + k * 15, 506, 9, 11, "#dccaa8", stroke=INK, sw=0.9) for k in range(6)]
    bk += [path("M1990 564 V540 Q2001 528 2012 540 V564 Z", "#3a2414"), ink("M1990 564 V540 Q2001 528 2012 540 V564", 1.2, 0.9),
           shade(1958, 516, 86, 48, "right", 0.3, "bkShade"), ink(poly([(1958, 516), (2044, 516), (2044, 564), (1958, 564)]), 1.3, 0.9),
           rim("M1959 518 V562 M1959 517 H2040", 1.8, 0.75)]
    out.append(group(bk, "hand"))

    wg = [rect(2150, 452, 112, 110, lin("harlW", [(0, "#e8d4b2"), (1, "#b8a284")], 0, 0, 1, 0)),
          path(poly([(2146, 452), (2166, 410), (2246, 410), (2266, 452)]), lin("slateW", [(0, "#6a7488"), (1, "#3a4252")]))]
    for k in range(8):
        y = 414 + k * 5
        xl, xr = 2166 - (y - 410) * 0.476, 2246 + (y - 410) * 0.476
        x = xl
        while x < xr:
            wg.append(path(f"M{n(x)} {n(y)} q3 4 6 0", "none", INK, 0.6, 0.55))
            x += 6
    wg.append(ink(poly([(2146, 452), (2166, 410), (2246, 410), (2266, 452)]), 1.3, 0.95))
    for dx in (2180, 2218):
        wg += [rect(dx, 426, 16, 20, "#e2cfae", stroke=INK, sw=1), path(f"M{n(dx - 2)} 426 L{n(dx + 8)} 414 L{n(dx + 18)} 426 Z", "#d8c4a2", stroke=INK, w=1),
               rect(dx + 4, 431, 8, 11, "#ffd27a"), ink(f"M{n(dx + 8)} 431 V442", 0.9, 0.9)]
        LIT["sc"].append((dx + 4, 431, 8, 11))
    wg += [rect(2240, 392, 16, 20, "#d8c4a2", stroke=INK, sw=1), rect(2238, 388, 20, 5, "#a89478", stroke=INK, sw=0.9)]
    for wx, wy in ((2176, 476), (2212, 476), (2238, 500), (2176, 516)):
        wg += [rect(wx, wy, 9, 14, "#ffd27a"), ink(poly([(wx, wy), (wx + 9, wy), (wx + 9, wy + 14), (wx, wy + 14)]), 1, 0.9), rect(wx - 1.5, wy - 2.5, 12, 2.5, "#a89478")]
        LIT["sc"].append((wx, wy, 9, 14))
    wg += [weathering(2150, 2262, 452, 562, 185, 26, "#4a3a3a", 0.16), shade(2150, 452, 112, 110, "right", 0.4, "wgShade"), ink(poly([(2150, 452), (2262, 452), (2262, 562), (2150, 562)]), 1.4, 0.95)]
    out.append(group(wg, "hand"))

    steps = [(2040, 410)]
    x, y = 2040, 410
    for _ in range(5):
        steps += [(x, y - 13), (x + 9, y - 13)]
        x, y = x + 9, y - 13
    steps += [(x, y - 13), (2105, y - 13)]
    right_side = [(2145 - (px - 2040), py) for px, py in steps[::-1]]
    gable = steps + right_side + [(2145, 562), (2040, 562)]
    mt = [path(poly(gable), lin("harlM", [(0, "#f0dcba"), (0.65, "#dcc6a2"), (1, "#b8a284")], 0, 0, 1, 0))]
    for qy in range(418, 562, 14):
        odd = (qy // 14) % 2
        mt += [rect(2040, qy, 9 if odd else 6, 7, "#c2aa86", op=0.9), rect(2136 if odd else 2139, qy, 9 if odd else 6, 7, "#a89070", op=0.9)]
    mt += [rect(2082, 300, 26, 30, "#d8c4a2", stroke=INK, sw=1.2), rect(2080, 296, 30, 5, "#a89478", stroke=INK, sw=1),
           rect(2085, 288, 6, 9, "#a8542e", stroke=INK, sw=0.8), rect(2099, 288, 6, 9, "#a8542e", stroke=INK, sw=0.8)]
    for wx, wy, ww, wh in ((2060, 426, 10, 16), (2115, 426, 10, 16), (2086, 466, 12, 20), (2058, 506, 10, 16), (2118, 504, 10, 16), (2090, 352, 9, 13)):
        mt += [rect(wx, wy, ww, wh, "#ffd27a"), ink(poly([(wx, wy), (wx + ww, wy), (wx + ww, wy + wh), (wx, wy + wh)]), 1, 0.9),
               ink(f"M{n(wx + ww / 2)} {n(wy)} V{n(wy + wh)}", 0.8, 0.8), rect(wx - 2, wy - 3, ww + 4, 3, "#a89478")]
        LIT["sc"].append((wx, wy, ww, wh))
    mt += [path("M2084 562 V540 Q2092 530 2100 540 V562 Z", "#4a2a12"), ink("M2084 562 V540 Q2092 530 2100 540 V562", 1.1, 0.9),
           ell(2070, 546, 2.5, 2.5, INK), ell(2122, 546, 2.5, 2.5, INK), weathering(2040, 2145, 410, 562, 186, 34, "#4a3a3a", 0.16),
           shade(2040, 300, 105, 262, "right", 0.38, "mtShade"),
           path(poly([(2116, 416), (2145, 416), (2145, 562), (2124, 562)]), "url(#h2)", op=0.25),
           ink(poly(gable), 1.6, 0.95), rim(line(steps), 1.8, 0.85), rim("M2041 412 V560", 2.4, 0.9)]
    out.append(group(mt, "hand"))
    tur = []
    for tx in (2026, 2132):
        tur.append(rect(tx, 402, 24, 42, lin("turret", [(0, "#efdcb8"), (1, "#b8a284")], 0, 0, 1, 0), stroke=INK, sw=1.2))
        tur += [path(f"M{n(tx + 1 + k * 3)} {n(444 + k * 5)} H{n(tx + 23 - k * 3)}", "none", INK, 1.2, 0.8) for k in range(3)]
        tur += [path(poly([(tx, 444), (tx + 24, 444), (tx + 12, 462)]), "#cdb896", stroke=INK, w=1.1),
                rect(tx + 9, 414, 6, 12, "#ffd27a"), ink(poly([(tx + 9, 414), (tx + 15, 414), (tx + 15, 426), (tx + 9, 426)]), 0.9, 0.9)]
        LIT["sc"].append((tx + 9, 414, 6, 12))
        tur += slate_cone(tx - 3, tx + 27, 404, 364, tx)
    out.append(group(tur, "hand"))
    stair = [rect(2140, 382, 22, 180, lin("stair", [(0, "#ecd8b4"), (1, "#b49e80")], 0, 0, 1, 0), stroke=INK, sw=1.2)]
    for wy in (410, 452, 496):
        stair.append(rect(2148, wy, 6, 10, "#ffd27a"))
        LIT["sc"].append((2148, wy, 6, 10))
    stair += slate_cone(2136, 2166, 384, 336, 2150)
    stair.append(path("M2151 336 V288", "none", "#2a2a30", 1.6))
    out.append(group(stair, "hand"))
    out.append(scots_pine(2350, 632, 216, 192, 0.05))
    return group(out)




# ---------------------------------------------------------------- foreground: roses (Bulgaria) and thistles (Scotland)

def roses(seed):
    r = random.Random(seed)
    bush = [ell(r.uniform(-30, 300), r.uniform(690, 780), r.uniform(16, 34), r.uniform(12, 22), r.choice(["#24301c", "#2e3c22", "#3a4a28", "#44562c"])) for _ in range(46)]
    det = []
    for _ in range(70):
        x, y = r.uniform(-20, 290), r.uniform(680, 760)
        det.append(ell(x, y, 5, 2.4, r.choice(["#4e6430", "#5e7438", "#3e5226"]), extra=f' transform="rotate({n(r.uniform(0, 180))} {n(x)} {n(y)})"'))
    for _ in range(26):
        x, y = r.uniform(-10, 280), r.uniform(676, 744)
        rr = r.uniform(5.5, 9.5)
        det += [ell(x, y, rr, rr * 0.88, r.choice(["#e8879a", "#f0a2b2", "#d86a84"])), ell(x - rr * 0.2, y - rr * 0.2, rr * 0.55, rr * 0.48, "#f8c2cc", 0.9),
                ink(f"M{n(x - rr * 0.5)} {n(y)} a{n(rr * 0.5)} {n(rr * 0.42)} 0 1 1 {n(rr * 0.5)} {n(rr * 0.2)} a{n(rr * 0.25)} {n(rr * 0.2)} 0 1 0 {n(-rr * 0.3)} {n(-rr * 0.2)}", 0.9, 0.7)]
    return group([group(bush, "wash"), group(det, "hand")])


# ---------------------------------------------------------------- the distant homes: Scotland, Valencia, the Netherlands

SC_T = (112, 278, 0.58)    # translate x, translate y and scale of each distant home
ES_T = (1560, 270, 0.56)
NL_T = (1990, 246, 0.6)
FAR_CLIP_Y = 652


def placed(draw, key, t):
    """Draw a home in its own coordinates, then shrink it into the distance; its lit windows follow."""
    tx, ty, sc = t
    before = len(LIT[key])
    g = draw()
    LIT[key][before:] = [(tx + sc * x, ty + sc * y, sc * w, sc * h) for x, y, w, h in LIT[key][before:]]
    return f'<g transform="translate({n(tx)} {n(ty)}) scale({o(sc)})">{g}</g>'


def pointed(cx, spring, half, base, k=1.4):
    """A pointed (Gothic) arch opening; returns the path and the height of its apex."""
    r_ = half * k
    apex = spring - math.sqrt(r_ ** 2 - (r_ - half) ** 2)
    return (f"M{n(cx - half)} {n(base)} V{n(spring)} A{n(r_)} {n(r_)} 0 0 1 {n(cx)} {n(apex)} "
            f"A{n(r_)} {n(r_)} 0 0 1 {n(cx + half)} {n(spring)} V{n(base)} Z"), apex


def battlements(x0, x1, top, w=9, gap=6, h=11, col="#d8b888"):
    out = []
    x = x0
    while x + w <= x1 + 0.1:
        out += [rect(x, top, w, h, col), ink(f"M{n(x)} {n(top + h)} V{n(top)} H{n(x + w)} V{n(top + h)}", 0.9, 0.7)]
        x += w + gap
    return out


def serranos():
    """Torres de Serranos, Valencia's Gothic city gate."""
    out = ashlar(70, 440, 160, 600, 760, "#e6c896", "#b48c5c", 12)
    out += [rect(66, 436, 98, 8, "#c9a06a", stroke=INK, sw=0.9)] + battlements(68, 162, 424, 8, 6, 12, "#dcbc8c")
    for k in range(7):
        d, _ = pointed(81 + k * 11.6, 470, 4, 486)
        out += [path(d, "#8a6440", op=0.85), ink(d, 0.7, 0.7)]
    out.append(rect(72, 486, 86, 4, "#a8804e"))
    d, _ = pointed(115, 548, 24, 600, 1.3)
    out += [path(d, lin("serGate", [(0, "#ffdc96"), (1, "#c87a3a")])), ink(d, 1.6, 0.95), path(pointed(115, 548, 31, 600, 1.3)[0], "none", INK, 1, 0.55)]
    LIT["es"].append((97, 526, 36, 74))
    out.append(shade(70, 424, 90, 176, "right", 0.25, "serShadeC"))
    for tx in (0, 160):
        out += ashlar(tx, 420, tx + 70, 600, 700 + tx, "#e2c290", "#b08858", 12)
        out.append(rect(tx - 5, 418, 80, 10, "#c9a06a", stroke=INK, sw=0.9))
        out += [path(f"M{n(tx - 3 + k * 10)} 428 l3 9 l4 0 l3 -9 Z", "#a8804e", stroke=INK, w=0.6) for k in range(8)]
        out += battlements(tx - 5, tx + 75, 406, 9, 5.2, 12)
        for wy in (468, 530):
            d, _ = pointed(tx + 35, wy, 5, wy + 18)
            out += [path(d, "#3a2414"), ink(d, 0.9, 0.8)]
        out += [shade(tx, 418, 70, 182, "right", 0.38, "serShade"), ink(poly([(tx, 420), (tx + 70, 420), (tx + 70, 600), (tx, 600)]), 1.4, 0.95),
                rim(f"M{n(tx + 1)} 422 V598", 2, 0.85)]
    return out


def micalet():
    """El Micalet, the octagonal Gothic bell tower of Valencia Cathedral."""
    x0, x1, top, base = 318, 366, 330, 600
    out = [path(poly([(x0, base), (x0, top), (x0 + 9, top - 3), (x0 + 9, base)]), "#ecd09a"),
           rect(x0 + 9, top - 3, 30, base - top + 3, lin("micFront", [(0, "#e0be88"), (1, "#b8925e")])),
           path(poly([(x1 - 9, top - 3), (x1, top), (x1, base), (x1 - 9, base)]), "#a8865a"),
           ink(f"M{n(x0 + 9)} {n(top - 3)} V{base} M{n(x1 - 9)} {n(top - 3)} V{base}", 1.1, 0.7)]
    out += [rect(x0 - 1, y, x1 - x0 + 2, 4, "#b89060", stroke=INK, sw=0.7) for y in (520, 450, 392)]
    for cx in (x0 + 18, x0 + 30):
        d, _ = pointed(cx, 358, 4.6, 386)
        out += [path(d, "#3a2414"), ink(d, 0.9, 0.85)]
    out.append(path(pointed(x0 + 24, 470, 3.5, 486)[0], "#ffd27a"))
    LIT["es"].append((x0 + 20.5, 464, 7, 22))
    out.append(rect(x0 - 3, top - 8, x1 - x0 + 6, 8, "#d4b07c", stroke=INK, sw=0.9))
    out += [rect(x0 - 1 + k * 7.4, top - 14, 3.5, 6, "#d4b07c") for k in range(7)]
    out += [rect(x0 + 16, top - 44, 16, 30, "#dcbc88", stroke=INK, sw=0.9), path(pointed(x0 + 24, top - 28, 4, top - 16)[0], "#3a2414"),
            path(poly([(x0 + 14, top - 44), (x0 + 24, top - 58), (x0 + 34, top - 44)]), "#b8925e", stroke=INK, w=0.9),
            path(f"M{n(x0 + 24)} {n(top - 58)} V{n(top - 70)} M{n(x0 + 20)} {n(top - 66)} H{n(x0 + 28)}", "none", "#3a3028", 1.4),
            ink(poly([(x0, base), (x0, top), (x1, top), (x1, base)]), 1.4, 0.95), rim(f"M{n(x0 + 1)} {n(top + 2)} V{n(base - 2)}", 2, 0.85)]
    return out


def basilica():
    """A Valencian church dome in blue glazed tiles, with gold ribs and a lantern."""
    cx = 520
    out = [rect(cx - 44, 404, 88, 40, lin("drumV", [(0, "#ead0a0"), (1, "#c09868")], 0, 0, 1, 0)), rect(cx - 48, 398, 96, 7, "#b89060", stroke=INK, sw=0.9)]
    for k in range(5):
        wx = cx - 36 + k * 16
        d, _ = pointed(wx + 4, 420, 3.5, 436)
        out += [path(d, "#ffd27a"), ink(d, 0.8, 0.85)]
        LIT["es"].append((wx + 0.5, 414, 7, 22))
    out.append(ink(poly([(cx - 44, 404), (cx + 44, 404), (cx + 44, 444), (cx - 44, 444)]), 1.1, 0.9))
    out += dome(cx, 398, 46, 54, 805, ["#2a6fb8", "#2462a8", "#e6c06a"], 7, 14)
    for j in range(1, 8):
        lo = -math.pi / 2 + math.pi * j / 8
        out.append(path(line([(cx + 46 * math.cos(la) * math.sin(lo), 398 - 54 * math.sin(la)) for la in [math.pi / 2 * k / 14 for k in range(15)]]),
                        "none", "#e6c06a", 1.5, 0.85))
    out += [rect(cx - 9, 330, 18, 16, "#e0c290", stroke=INK, sw=0.9), path(f"M{n(cx - 11)} 332 Q{n(cx)} 316 {n(cx + 11)} 332 Z", "#2a6fb8", stroke=INK, w=0.9),
            path(f"M{n(cx)} 318 V298 M{n(cx - 5)} 306 H{n(cx + 5)}", "none", "#e6c06a", 1.8)]
    LIT["es"].append((cx - 5, 334, 10, 10))
    return out


def valencia_houses():
    """Old-town houses with tiled roofs, shutters and wrought-iron balconies."""
    r = random.Random(820)
    out = []
    x = 214
    for w, h, col in [(66, 150, "#e6c49a"), (58, 128, "#e8b8a0"), (72, 170, "#f0dca8"), (60, 140, "#dca878"), (70, 160, "#ecd0b4"), (62, 124, "#e4c08c")]:
        top = 600 - h
        roof = [(x - 4, top), (x + 8, top - 16), (x + w - 8, top - 16), (x + w + 4, top)]
        out += [rect(x, top, w, h, lin(f"vh{x}", [(0, col), (1, mix(col, "#7a5a40", 0.35))])), path(poly(roof), "#b8583a"), ink(poly(roof), 1, 0.85)]
        out += [ink(f"M{n(x - 4 + k * 2.2)} {n(top - 16 + k * 2.7)} H{n(x + w + 4 - k * 2.2)}", 0.6, 0.5) for k in range(1, 6)]
        out.append(rect(x - 2, top, w + 4, 4, mix(col, "#ffffff", 0.3), stroke=INK, sw=0.7))
        rows = int((h - 30) // 34)
        cols = max(2, int(w // 24))
        for rr in range(rows):
            wy = top + 14 + rr * 34
            for cc in range(cols):
                wx = x + (w - cols * 20) / 2 + cc * 20 + 4
                lit = r.random() < 0.35
                out += [rect(wx, wy, 12, 20, "#ffd27a" if lit else "#4a3a30"), rect(wx - 3, wy, 3, 20, "#4a6a44"), rect(wx + 12, wy, 3, 20, "#4a6a44")]
                if lit:
                    LIT["es"].append((wx, wy, 12, 20))
                if rr < rows - 1 and r.random() < 0.7:
                    out += [rect(wx - 5, wy + 20, 22, 2, "#2a2420"), path(f"M{n(wx - 5)} {n(wy + 13)} H{n(wx + 17)}", "none", "#2a2420", 1)]
                    out += [path(f"M{n(wx - 5 + k * 3.6)} {n(wy + 20)} v-7", "none", "#2a2420", 0.8) for k in range(7)]
                    if r.random() < 0.6:
                        out.append(ell(wx + r.uniform(-2, 14), wy + 12, 3, 2.4, r.choice(["#d8342a", "#e84a6a", "#f08a2a"])))
        out += [shade(x, top, w, h, "right", 0.3, "vhShade"), ink(poly([(x, top), (x + w, top), (x + w, 600), (x, 600)]), 1.2, 0.9),
                rim(f"M{n(x + 1)} {n(top + 2)} V598", 1.4, 0.6)]
        x += w + r.uniform(-4, 2)
    return out


def orange_trees(x0, x1, base, size, seed):
    r = random.Random(seed)
    out = []
    x = x0 + r.uniform(0, 18)
    while x < x1:
        s_ = size * r.uniform(0.85, 1.12)
        out += [rect(x - 1.6, base - 7, 3.2, 9, "#4a3020"), ell(x, base - s_ * 0.9, s_, s_ * 0.85, "#2e4422"),
                ell(x - s_ * 0.3, base - s_ * 1.15, s_ * 0.6, s_ * 0.45, "#56763a", 0.9)]
        out += [ell(x + r.uniform(-s_ * 0.75, s_ * 0.75), base - s_ * 0.9 + r.uniform(-s_ * 0.55, s_ * 0.5), 1.9, 1.9, r.choice(["#f08a24", "#ff9c30", "#e07818"])) for _ in range(7)]
        out += [ink(f"M{n(x - s_)} {n(base - s_ * 0.9)} a{n(s_)} {n(s_ * 0.85)} 0 0 1 {n(2 * s_)} 0", 0.8, 0.5),
                rim(f"M{n(x - s_ * 0.9)} {n(base - s_ * 1.1)} q{n(s_ * 0.4)} {n(-s_ * 0.6)} {n(s_)} {n(-s_ * 0.7)}", 1.2, 0.5)]
        x += s_ * 2 + r.uniform(4, 14)
    return out


def barraca(x, base):
    """A thatched barraca from the huerta around Valencia, with the cross on its ridge."""
    w = 64
    out = [rect(x, base - 32, w, 32, lin("barWall", [(0, "#f6eee0"), (1, "#d8ccb8")], 0, 0, 1, 0)), ink(poly([(x, base - 32), (x + w, base - 32), (x + w, base), (x, base)]), 1, 0.85),
           rect(x + 26, base - 24, 12, 24, "#3a2a1e"), rect(x + 24, base - 26, 16, 2, "#2a5aa0"), rect(x + 24, base - 26, 2, 26, "#2a5aa0"), rect(x + 38, base - 26, 2, 26, "#2a5aa0"),
           rect(x + 8, base - 22, 8, 8, "#ffd27a"), rect(x + 48, base - 22, 8, 8, "#ffd27a")]
    LIT["es"].extend([(x + 8, base - 22, 8, 8), (x + 48, base - 22, 8, 8)])
    apex = (x + w / 2, base - 98)
    roof = [(x - 6, base - 30), apex, (x + w + 6, base - 30)]
    out.append(path(poly(roof), lin("thatch", [(0, "#d9b060"), (1, "#9a7034")], 0, 0, 1, 0)))
    r = random.Random(830)
    for k in range(26):
        bx = lerp(x - 6, x + w + 6, k / 25)
        out.append(path(f"M{n(lerp(apex[0], bx, 0.15))} {n(lerp(apex[1], base - 30, 0.15))} L{n(bx)} {n(base - 30)}", "none", r.choice(["#b88a3e", "#8a6a2e", "#e0c070"]), 1, 0.7))
    out += [ink(poly(roof), 1.2, 0.95), rim(f"M{n(x - 6)} {n(base - 30)} L{n(apex[0])} {n(apex[1])}", 1.8, 0.85),
            path(f"M{n(apex[0])} {n(apex[1])} v-12 M{n(apex[0] - 4)} {n(apex[1] - 8)} h8", "none", "#f2efe6", 1.8)]
    return out


def valencia():
    out = micalet() + basilica() + valencia_houses() + serranos()
    out += orange_trees(180, 720, 588, 15, 841) + orange_trees(190, 720, 600, 17, 842) + barraca(640, 606) + orange_trees(200, 620, 612, 19, 843)
    return group(out, "hand")


def windmill(x, base):
    """A Dutch smock mill; its sails turn in the live overlay."""
    out = [rect(x + 6, base - 36, 108, 36, "#8a4a32")]
    out += [ink(f"M{n(x + 6)} {n(base - 36 + k * 6)} H{n(x + 114)}", 0.5, 0.35) for k in range(1, 6)]
    body = [(x + 14, base - 36), (x + 40, base - 196), (x + 80, base - 196), (x + 106, base - 36)]
    out.append(path(poly(body), lin("millBody", [(0, "#7a6a50"), (0.5, "#5a4e3c"), (1, "#3a3228")], 0, 0, 1, 0)))
    out += [ink(f"M{n(lerp(x + 14, x + 106, k / 8))} {n(base - 36)} L{n(lerp(x + 40, x + 80, k / 8))} {n(base - 196)}", 0.7, 0.4) for k in range(1, 8)]
    sy = base - 100
    out += [path(f"M{n(x + 2)} {n(sy + 5)} L{n(x + 22)} {n(sy + 44)} M{n(x + 118)} {n(sy + 5)} L{n(x + 98)} {n(sy + 44)}", "none", "#4a3420", 2.4),
            rect(x - 10, sy, 140, 5, "#4a3420", stroke=INK, sw=0.8), path(f"M{n(x - 10)} {n(sy - 12)} H{n(x + 130)}", "none", "#4a3420", 1.4)]
    out += [path(f"M{n(x - 10 + k * 10)} {n(sy)} v-12", "none", "#4a3420", 1) for k in range(15)]
    out += [rect(x + 52, base - 30, 16, 30, "#3a2414"), rect(x + 55, sy - 32, 10, 14, "#ffd27a")]
    LIT["nl"].append((x + 55, sy - 32, 10, 14))
    out.append(group([shade(x, base - 200, 120, 200, "right", 0.32, "millShade")], clip=clip("millBodyClip", poly(body))))
    cap = f"M{n(x + 34)} {n(base - 196)} Q{n(x + 40)} {n(base - 232)} {n(x + 60)} {n(base - 232)} Q{n(x + 80)} {n(base - 232)} {n(x + 86)} {n(base - 196)} Z"
    out += [path(cap, "#3a3a40"), ink(cap, 1.2, 0.95), rim(f"M{n(x + 35)} {n(base - 197)} Q{n(x + 41)} {n(base - 230)} {n(x + 60)} {n(base - 231)}", 1.6, 0.8),
            ell(x + 60, base - 212, 5, 5, "#2a2420"), ink(poly(body), 1.3, 0.95), rim(f"M{n(x + 15)} {n(base - 38)} L{n(x + 41)} {n(base - 194)}", 1.8, 0.85)]
    return out


def gable(kind, x, w, bt):
    """Amsterdam gables: step, neck, bell or spout. Returns the outline and its top."""
    gx = x + w / 2
    if kind == "step":
        steps, rise = 4, 11
        sw_ = w / (2 * steps + 2)
        left = [(x, bt)]
        for k in range(steps):
            left += [(x + k * sw_, bt - (k + 1) * rise), (x + (k + 1) * sw_, bt - (k + 1) * rise)]
        top = bt - (steps + 1) * rise
        left += [(x + steps * sw_, top), (gx, top)]
        return poly(left + [(2 * gx - px, py) for px, py in left[::-1]]), top
    if kind == "neck":
        top = bt - 62
        return (f"M{n(x)} {n(bt)} Q{n(x)} {n(bt - 20)} {n(x + w * 0.3)} {n(bt - 24)} V{n(bt - 52)} L{n(gx)} {n(top)} L{n(x + w * 0.7)} {n(bt - 52)} "
                f"V{n(bt - 24)} Q{n(x + w)} {n(bt - 20)} {n(x + w)} {n(bt)} Z"), top
    if kind == "bell":
        top = bt - 62
        return (f"M{n(x)} {n(bt)} C{n(x)} {n(bt - 30)} {n(gx - w * 0.4)} {n(bt - 34)} {n(gx - w * 0.22)} {n(bt - 50)} Q{n(gx)} {n(bt - 74)} {n(gx + w * 0.22)} {n(bt - 50)} "
                f"C{n(gx + w * 0.4)} {n(bt - 34)} {n(x + w)} {n(bt - 30)} {n(x + w)} {n(bt)} Z"), top
    top = bt - 56
    return f"M{n(x)} {n(bt)} L{n(gx - w * 0.16)} {n(bt - 40)} V{n(top)} H{n(gx + w * 0.16)} V{n(bt - 40)} L{n(x + w)} {n(bt)} Z", top


def canal_house(x, base, w, h, kind, col, seed, lean):
    r = random.Random(seed)
    bt = base - h
    gx = x + w / 2
    gd, top = gable(kind, x, w, bt)
    out = [rect(x, bt, w, h, lin(f"brick{seed}", [(0, col), (1, mix(col, "#1a1010", 0.3))])), path(gd, col)]
    out += [ink(f"M{n(x)} {n(y)} H{n(x + w)}", 0.4, 0.22) for y in range(int(bt) + 4, base, 5)]
    cols = 3 if w >= 58 else 2
    for fl in range(int((h - 34) // 30)):
        wy = bt + 10 + fl * 30
        for c in range(cols):
            wx = x + w * (c + 0.5) / cols - 6
            lit = r.random() < 0.4
            out += [rect(wx, wy, 12, 19, "#ffd27a" if lit else "#2a2a30", stroke="#f2efe6", sw=1.2),
                    ink(f"M{n(wx + 6)} {n(wy)} V{n(wy + 19)} M{n(wx)} {n(wy + 9)} H{n(wx + 12)}", 0.7, 0.8)]
            if lit:
                LIT["nl"].append((wx, wy, 12, 19))
    lit_g = r.random() < 0.5
    out.append(rect(gx - 5, bt - 22, 10, 14, "#ffd27a" if lit_g else "#2a2a30", stroke="#f2efe6", sw=1.1))
    if lit_g:
        LIT["nl"].append((gx - 5, bt - 22, 10, 14))
    out += [rect(gx - 1.5, top + 5, 3, 9, "#2a2020"), path(f"M{n(gx)} {n(top + 14)} v5 q2 2 3 0", "none", "#2a2020", 0.9),
            rect(gx - 7, base - 24, 14, 24, "#2e4a3a", stroke="#f2efe6", sw=1), rect(gx - 11, base - 4, 22, 4, "#8a8a80"),
            path(gd, "none", "#f2efe6", 1.5), shade(x, bt, w, h, "right", 0.28, "nlShade"),
            ink(poly([(x, bt), (x + w, bt), (x + w, base), (x, base)]), 1.1, 0.9), rim(f"M{n(x + 1)} {n(bt + 2)} V{n(base - 2)}", 1.4, 0.6)]
    return f'<g transform="rotate({o(lean)} {n(gx)} {n(base)})">' + "".join(out) + "</g>"


def netherlands():
    out = windmill(40, 600)
    tulip = ["#d8242e", "#f2c230", "#e85a8a", "#f6f0e2", "#c81e3a", "#f08a24"]
    for k in range(6):
        t0, t1 = k / 6, (k + 0.62) / 6
        out.append(path(poly([(lerp(0, 200, t0), 640), (lerp(0, 200, t1), 640), (lerp(0, 200, t1) + 40, 602), (lerp(0, 200, t0) + 40, 602)]), tulip[k]))
    x = 230
    for i, (w, h, kind, col, lean) in enumerate([(56, 150, "step", "#7a3424", -1.2), (60, 136, "neck", "#5a2e22", 0.8), (50, 160, "bell", "#8a4a30", -0.6),
                                                 (64, 140, "step", "#3a3e34", 1.4), (54, 154, "spout", "#6a3a28", -1.0), (60, 132, "neck", "#9a5a3a", 0.6)]):
        out.append(canal_house(x, 600, w, h, kind, col, 910 + i, lean))
        x += w + 1
    out += [rect(200, 600, 440, 26, lin("canal", [(0, "#3a5a6a"), (1, "#1e3040")])), rect(200, 600, 440, 3, "#9a9a90")]
    out += [path(f"M{n(wx + ww / 2)} 605 q2 4 0 8 q-2 4 0 8", "none", "#ffd27a", 2, 0.45) for wx, wy, ww, wh in LIT["nl"] if wx > 220]
    out += [ink(f"M{n(210 + k * 37)} {n(611 + (k % 3) * 4)} q8 -2 16 0", 0.8, 0.5) for k in range(11)]
    out += [path("M196 606 Q244 590 292 606 L292 616 Q244 602 196 616 Z", "#8a4a32", stroke=INK, w=1), path("M210 626 Q244 606 278 626 Z", "#1a2830"),
            path("M196 600 Q244 584 292 600", "none", "#f2efe6", 1.4)]
    out += [path(f"M{n(200 + k * 9)} {n(604 - 6 * math.sin(math.pi * (k + 0.5) / 10))} v6", "none", "#f2efe6", 0.9) for k in range(10)]
    out += [ell(232, 590, 6, 6, "none", stroke="#1e1612", sw=1.2), ell(254, 590, 6, 6, "none", stroke="#1e1612", sw=1.2),
            path("M232 590 L238 580 L242 590 Z M242 590 L250 580 L238 580 M250 580 L254 590 M236 578 h5 M249 579 l3 -3", "none", "#1e1612", 1.1),
            path("M286 604 V570", "none", "#1e1612", 1.6), rect(282, 562, 8, 9, "#ffd27a", stroke=INK, sw=0.8)]
    LIT["nl"].append((282, 562, 8, 9))
    for tx, ty, s_ in ((600, 594, 28), (628, 600, 24)):
        out += [rect(tx - 2, ty - 6, 4, 14, "#3a2818"), ell(tx, ty - s_, s_, s_ * 0.85, "#2e4228"), ell(tx - s_ * 0.3, ty - s_ * 1.25, s_ * 0.6, s_ * 0.45, "#4e6a38", 0.9),
                ink(f"M{n(tx - s_)} {n(ty - s_)} a{n(s_)} {n(s_ * 0.85)} 0 0 1 {n(2 * s_)} 0", 0.9, 0.5)]
    return group(out, "hand")


def far_ground():
    """Moor under Scotland, huerta under Valencia, polder under the Netherlands."""
    out = []
    moor = ridge(1110, 1580, 8, 606, [(0.01, 4), (0.03, 2)], 51)
    out.append(path(poly(moor + [(1580, 668), (1110, 668)]), lin("moorG", [(0, "#7a5a6a"), (1, "#54404c")], user=(0, 600, 0, 668))))
    r = random.Random(52)
    out += [ell(r.uniform(1120, 1570), r.uniform(608, 660), r.uniform(1.2, 2.2), r.uniform(1, 1.6), r.choice(["#b77cc2", "#9a5aa8", "#c99ad0"]), 0.8) for _ in range(120)]
    huerta = ridge(1550, 2000, 8, 610, [(0.012, 2), (0.03, 1)], 53)
    out.append(path(poly(huerta + [(2000, 668), (1550, 668)]), lin("huertaG", [(0, "#8a9a58"), (1, "#5a6a3a")], user=(0, 604, 0, 668))))
    out += [ink(f"M{n(1560 + k * 44)} 612 L{n(1540 + k * 52)} 668", 0.7, 0.3) for k in range(10)]
    out.append(path("M1552 640 Q1700 632 1840 644 T1998 636", "none", "#c8e0e8", 1.4, 0.5))
    out.append(path(poly([(1980, 611), (2440, 611), (2440, 668), (1980, 668)]), lin("polderG", [(0, "#7a9a58"), (1, "#4a6a3a")], user=(0, 606, 0, 668))))
    out += [path(f"M1985 {n(616 + k * 9)} H2440", "none", "#c8d8e0", 1, 0.45) for k in range(6)]
    return out


def far_homes():
    clip("farClip", f"M0 0 H{W} V{FAR_CLIP_Y} H0 Z")
    homes = [group(far_ground(), "wash"), placed(scottish_castle, "sc", SC_T), placed(valencia, "es", ES_T), placed(netherlands, "nl", NL_T)]
    add_def("farMask", f'<mask id="farMask" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><use href="#far" filter="url(#whiten)"/></mask>')
    haze = lin("farHaze", [(0, "#d8c4d8", 0.22), (1, "#e8d0d0", 0.5)], user=(0, 400, 0, FAR_CLIP_Y))
    return (f'<g id="far" clip-path="url(#farClip)">' + "".join(homes) + "</g>"
            + f'<rect x="0" y="380" width="{W}" height="{FAR_CLIP_Y - 380}" fill="{haze}" mask="url(#farMask)"/>')


# ---------------------------------------------------------------- Bulgaria: the чешма, haystacks and a lavender field

def chesma(x, base):
    """A stone чешма, the village drinking fountain, with a copper jug."""
    w, h = 96, 70
    top = base - h
    out = [group(rubble(x, top, x + w, base, 1201, ["#c9b597", "#b8a284", "#d6c3a2", "#a99377"], row=(8, 12), width=(10, 20)))]
    out += tiles_rows(lambda y: (x - 8 + (top - y) * 0.9, x + w + 8 - (top - y) * 0.9), top - 16, top, 6, 8, 1202, "#a8442a")
    out.append(ink(poly([(x - 8, top), (x + 6, top - 16), (x + w - 6, top - 16), (x + w + 8, top)]), 1.2, 0.85))
    niche = f"M{n(x + 24)} {n(base - 14)} V{n(top + 30)} A24 22 0 0 1 {n(x + 72)} {n(top + 30)} V{n(base - 14)} Z"
    out += [path(niche, lin("niche", [(0, "#5a4a3a"), (1, "#2e241c")])), ink(niche, 1.3, 0.9),
            rect(x + 30, top + 6, 36, 12, "#e2d4b8", stroke=INK, sw=0.8), ink(f"M{n(x + 34)} {n(top + 10)} h28 M{n(x + 34)} {n(top + 14)} h22", 0.7, 0.6),
            path(f"M{n(x + 46)} {n(top + 40)} h10 v4 h-10 Z", "#b8863a", stroke=INK, w=0.6),
            path(f"M{n(x + 55)} {n(top + 43)} Q{n(x + 59)} {n(top + 47)} {n(x + 59)} {n(base - 12)}", "none", "#bfe6f2", 1.8, 0.9),
            rect(x + 14, base - 14, 68, 14, "#a8967e", stroke=INK, sw=1), rect(x + 18, base - 14, 60, 3, "#7ab4c4", op=0.9)]
    jx = x + 84
    out += [path(f"M{n(jx - 6)} {n(base)} Q{n(jx - 9)} {n(base - 10)} {n(jx - 4)} {n(base - 16)} L{n(jx + 4)} {n(base - 16)} Q{n(jx + 9)} {n(base - 10)} {n(jx + 6)} {n(base)} Z",
                 "#b8682e", stroke=INK, w=0.8), path(f"M{n(jx + 4)} {n(base - 14)} q6 2 4 9", "none", "#8a4a20", 1.2),
            rim(f"M{n(jx - 5)} {n(base - 2)} q-3 -8 1 -13", 1.2, 0.7), shade(x, top, w, h, "right", 0.32, "chesmaShade"),
            ink(poly([(x, top), (x + w, top), (x + w, base), (x, base)]), 1.4, 0.95), rim(f"M{n(x + 1)} {n(top + 2)} V{n(base - 2)}", 2, 0.85)]
    out += [ell(x + k * 12 + 6, base - 1, 6, 2.4, "#4e6a30", 0.8) for k in range(8)]
    return group(out, "hand")


def haystack(cx, base, w, h, seed):
    """A копа: hay stacked around a pole, with its shadow falling toward the viewer."""
    r = random.Random(seed)
    shape = (f"M{n(cx - w / 2)} {n(base)} Q{n(cx - w * 0.56)} {n(base - h * 0.55)} {n(cx - w * 0.18)} {n(base - h * 0.92)} "
             f"Q{n(cx)} {n(base - h * 1.02)} {n(cx + w * 0.18)} {n(base - h * 0.92)} Q{n(cx + w * 0.56)} {n(base - h * 0.55)} {n(cx + w / 2)} {n(base)} Z")
    cid = clip(f"hay{seed}", shape)
    straw = [path(f"M{n(cx + r.uniform(-w / 2, w / 2))} {n(base - r.uniform(0, h))} q{n(r.uniform(-4, 4))} {n(r.uniform(4, 9))} {n(r.uniform(-6, 6))} {n(r.uniform(8, 14))}",
                  "none", r.choice(["#f2d080", "#a8782e", "#d8a850", "#8a6024"]), 1.1, 0.8) for _ in range(int(w * 1.6))]
    shadow = poly([(cx - w * 0.45, base), (cx + w * 0.5, base), (cx + w * 1.3, base + h * 0.3), (cx + w * 0.1, base + h * 0.34)])
    out = [group([path(shadow, "#2a1a24", op=0.28)], "wash"),
           path(shape, lin(f"hayG{seed}", [(0, "#ecc878"), (0.55, "#c8963e"), (1, "#7a5424")], 0, 0, 1, 0)), group(straw, clip=cid),
           group([shade(cx - w / 2, base - h * 1.05, w, h * 1.05, "right", 0.35, "hayShade")], clip=cid),
           path(f"M{n(cx - w * 0.36)} {n(base - h * 0.4)} Q{n(cx)} {n(base - h * 0.34)} {n(cx + w * 0.36)} {n(base - h * 0.4)}", "none", "#6a4a24", 1.4, 0.7),
           path(f"M{n(cx)} {n(base - h * 0.98)} L{n(cx + 2)} {n(base - h * 1.22)}", "none", "#5a3a1e", 3.2),
           ink(shape, 1.3, 0.9), rim(f"M{n(cx - w / 2 + 1)} {n(base - 1)} Q{n(cx - w * 0.55)} {n(base - h * 0.55)} {n(cx - w * 0.17)} {n(base - h * 0.91)}", 2, 0.85)]
    return group(out, "hand")


def lavender():
    """A lavender field; its rows run toward the horizon and the distant homes."""
    r = random.Random(1301)
    vp = (1760, 612)
    y_top, y_bot = 666, 772
    t_top = (y_bot - y_top) / (y_bot - vp[1])

    def at_top(xb):
        return xb + (vp[0] - xb) * t_top
    field = [(1150, y_bot), (2440, y_bot), (2440, y_top), (at_top(1150), y_top)]
    rows = [path(poly(field), "#3a3024")]
    xb = 1080
    while xb < 2900:
        x0b, x1b = xb, xb + 80
        q = [(x0b, y_bot), (x1b, y_bot), (at_top(x1b), y_top), (at_top(x0b), y_top)]
        rows.append(path(poly(q), lin("lavRow", [(0, "#8a6ab4"), (1, "#4a2e6a")], user=(0, y_top, 0, y_bot))))
        for _ in range(170):
            s_ = r.random() ** 0.7
            y = lerp(y_top, y_bot, s_)
            xl, xr = lerp(at_top(x0b), x0b, s_), lerp(at_top(x1b), x1b, s_)
            x = r.uniform(xl, xr)
            sz = 0.9 + 3.2 * s_
            lit = (x - xl) / max(1, xr - xl) < 0.5
            rows.append(ell(x, y - sz, sz * 0.55, sz * 1.25, r.choice(["#b892d8", "#a07cc8"] if lit else ["#6a4a90", "#5a3c7e"])))
        rows.append(ink(poly(q), 0.7, 0.35))
        xb += 126
    hedge = [ell(lerp(at_top(1150) - 20, 2440, k / 69) + r.uniform(-6, 6), y_top - 2 + r.uniform(-2, 2), r.uniform(12, 22), r.uniform(5, 9),
                 r.choice(["#2e3a22", "#3a4628", "#26301c"])) for k in range(70)]
    return group([group(rows, clip=clip("lavField", poly(field))), group(hedge, "wash"), ink(f"M1150 {y_bot} L{n(at_top(1150))} {y_top}", 1.2, 0.5)], "hand")


SCENE.append(chesma(1062, 664))
SCENE.append(group(wildflowers(1010, 1460, 680, 750, 1310, 30), "hand"))
SCENE.append(lavender())
SCENE.append(haystack(1330, 690, 58, 76, 1402))
SCENE.append(haystack(1236, 728, 84, 110, 1401))

SCENE.append(rect(-20, 676, W + 40, 90, lin("groundFadeA", [(0, "#1a120c", 0), (1, "#1a120c", 0.7)]), op=1))
SCENE.append(roses(201))


SCENE.insert(FAR_INDEX, far_homes())


# ---------------------------------------------------------------- output

def art_svg():
    sun_shade = rad("duskShade", [(0, "#fff6ee"), (0.28, "#f0dcd0"), (0.6, "#c4a8bc"), (1, "#9a82a4")], SUN[0], SUN[1] - 60, 1500)
    sun_warm = rad("sunWarm", [(0, "#ff9a48", 0.55), (0.5, "#ff9a48", 0.12), (1, "#ff9a48", 0)], SUN[0], SUN[1], 560)
    add_def("paintMask", f'<mask id="paintMask" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><use href="#paint" filter="url(#whiten)"/></mask>')
    final_fade = lin("groundFadeB", [(0, "#1a120c", 0), (1, "#1a120c", 1)], user=(0, 722, 0, 760))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<defs>{"".join(DEFS)}</defs>'
            f'<g id="paint" filter="url(#paper)">{"".join(SCENE)}</g>'
            f'<rect width="{W}" height="{H}" fill="{sun_shade}" mask="url(#paintMask)" style="mix-blend-mode:multiply" opacity="0.62"/>'
            f'<rect width="{W}" height="{H}" fill="{sun_warm}" mask="url(#paintMask)" style="mix-blend-mode:screen"/>'
            f'<rect x="0" y="722" width="{W}" height="38" fill="{final_fade}"/>'
            '</svg>')


def overlay():
    # Halo per lit opening, capped so large openings don't wash the walls out. The glows are static and live in
    # their own layer, so the animated details (sails, smoke, flag) repaint only their own small areas.
    glows = {k: "".join(f'<ellipse cx="{n(x + w / 2)}" cy="{n(y + h / 2)}" rx="{n(min(w * 0.75 + 3, 16))}" ry="{n(min(h * 0.6 + 3, 18))}"/>'
                        for x, y, w, h in v) for k, v in LIT.items()}
    sc = f"translate({n(SC_T[0])} {n(SC_T[1])}) scale({o(SC_T[2])})"
    nl = f"translate({n(NL_T[0])} {n(NL_T[1])}) scale({o(NL_T[2])})"
    arm = 124
    sails = ""
    for k in range(4):
        bars = "".join(f'<path class="lat" d="M3 -{arm - 4 - j_ * 10} H22"/>' for j_ in range(10))
        sails += (f'<g transform="rotate({k * 90})"><path class="whip" d="M0 6 V-{arm}"/><path class="sail" d="M3 -22 H22 V-{arm - 2} H3 Z"/>'
                  f'{bars}<path class="lat" d="M12 -22 V-{arm - 2}"/></g>')
    return f"""      <div class="skyline" aria-hidden="true">
        <svg class="sk-back" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax slice" focusable="false">
          <defs>
            <radialGradient id="sk-sun"><stop offset="0" stop-color="#fff6d2"/><stop offset="0.5" stop-color="#ffd27a"/><stop offset="0.85" stop-color="#ff9a48" stop-opacity="0.95"/><stop offset="1" stop-color="#ff8a3a" stop-opacity="0"/></radialGradient>
            <radialGradient id="sk-sun-glow"><stop offset="0" stop-color="#ffc878" stop-opacity="0.55"/><stop offset="1" stop-color="#ff8a3a" stop-opacity="0"/></radialGradient>
          </defs>
          <circle cx="{SUN[0]}" cy="{SUN[1]}" r="460" fill="url(#sk-sun-glow)"/>
          <circle cx="{SUN[0]}" cy="{SUN[1]}" r="150" fill="url(#sk-sun)"/>
        </svg>
        <img class="sk-art" fetchpriority="high" src="{{{{root}}}}assets/img/skyline-1920.webp" srcset="{{{{root}}}}assets/img/skyline-1280.webp 1280w, {{{{root}}}}assets/img/skyline-1920.webp 1920w, {{{{root}}}}assets/img/skyline-2880.webp 2880w" sizes="(max-width: 640px) 640px, 100vw" width="2880" height="912" alt="" decoding="async">
        <svg class="sk-front" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax slice" focusable="false">
          <g class="sk-glow sk-bg">{glows["bg"]}</g>
          <g class="sk-glow sk-sc">{glows["sc"]}</g>
          <g class="sk-glow sk-es">{glows["es"]}</g>
          <g class="sk-glow sk-nl">{glows["nl"]}</g>
        </svg>
        <svg class="sk-live" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax slice" focusable="false">
          <g transform="{nl}"><g transform="translate(100 388)"><g class="sk-sails">{sails}<circle class="hub" r="6"/>
            <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="30s" repeatCount="indefinite"/></g></g></g>
          <g transform="{sc}">
            <g class="sk-smoke"><circle cx="2088" cy="284" r="6"/><circle cx="2102" cy="284" r="6"/><circle cx="2095" cy="284" r="7"/></g>
            <path class="sk-flag" d="M2151 290 C2160 286 2168 294 2179 289 L2179 307 C2168 312 2160 304 2151 308 Z">
              <animate attributeName="d" dur="2.6s" repeatCount="indefinite" values="M2151 290 C2160 286 2168 294 2179 289 L2179 307 C2168 312 2160 304 2151 308 Z;M2151 290 C2160 294 2168 286 2179 291 L2179 309 C2168 304 2160 312 2151 308 Z;M2151 290 C2160 286 2168 294 2179 289 L2179 307 C2168 312 2160 304 2151 308 Z"/>
            </path>
            <path class="sk-flag-x" d="M2152 291 L2178 307 M2178 290 L2152 307">
              <animate attributeName="d" dur="2.6s" repeatCount="indefinite" values="M2152 291 L2178 307 M2178 290 L2152 307;M2152 293 L2178 307 M2178 292 L2152 307;M2152 291 L2178 307 M2178 290 L2152 307"/>
            </path>
          </g>
        </svg>
        <div class="embers">
          <i style="--x: 8%;  --d: 0s;   --t: 9s"></i>
          <i style="--x: 19%; --d: 3.1s; --t: 7s"></i>
          <i style="--x: 31%; --d: 5.4s; --t: 10s"></i>
          <i style="--x: 39%; --d: 1.2s; --t: 8s"></i>
          <i style="--x: 47%; --d: 6.8s; --t: 9.5s"></i>
          <i style="--x: 58%; --d: 2.5s; --t: 7.5s"></i>
          <i style="--x: 66%; --d: 0.8s; --t: 8.5s"></i>
          <i style="--x: 74%; --d: 5.9s; --t: 9s"></i>
          <i style="--x: 83%; --d: 3.6s; --t: 7s"></i>
          <i style="--x: 92%; --d: 1.9s; --t: 10s"></i>
        </div>
      </div>
"""


if __name__ == "__main__":
    art_path, partial_path = Path(sys.argv[1]), Path(sys.argv[2])
    art_path.write_text(art_svg(), encoding="utf-8")
    partial_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path.write_text(overlay(), encoding="utf-8", newline="\n")
    print(f"art {art_path.stat().st_size // 1024} KB, lit windows: " + ", ".join(f"{k} {len(v)}" for k, v in LIT.items()))
