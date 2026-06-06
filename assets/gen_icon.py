#!/usr/bin/env python3
"""Generate the Rituals app icon (icon.icns): a flat, stylised sunrise — an
amber half-sun (dome) rising over a broken horizon line, with a ray fan above,
on a warm cream tile (bold, flat, no gradients). Supersampled 2x for clean
edges. Modelled on ~/Downloads/Sunrise.png but redrawn crisp and watermark-free.

Run from anywhere:  python3 assets/gen_icon.py
Produces:  assets/icon_1024.png  and  icon.icns (project root)
"""
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

SS = 2
S = 1024 * SS
MARGIN = 96 * SS
RADIUS = round((S - 2 * MARGIN) * 0.2237)

CREAM = (243, 240, 226)
AMBER = (255, 182, 0)         # golden amber sampled from Sunrise.png


def build_master() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    w = h = S - 2 * MARGIN
    content = Image.new("RGBA", (w, h), CREAM + (255,))
    d = ImageDraw.Draw(content)

    cx = w // 2
    horizon = int(h * 0.62)       # the line the sun rises from
    R = int(w * 0.21)             # dome radius
    fill = AMBER + (255,)

    # Ray fan over the dome: 5 thick rounded spokes radiating from the sun
    # centre, spanning the upper hemisphere (math degrees, 0=right, 90=up).
    inner = R + w * 0.055
    outer = R + w * 0.165
    ray_w = int(w * 0.05)
    cap = ray_w // 2
    for deg in (18, 54, 90, 126, 162):
        a = math.radians(deg)
        x1, y1 = cx + inner * math.cos(a), horizon - inner * math.sin(a)
        x2, y2 = cx + outer * math.cos(a), horizon - outer * math.sin(a)
        d.line([(x1, y1), (x2, y2)], fill=fill, width=ray_w)
        for px, py in ((x1, y1), (x2, y2)):   # round the spoke caps
            d.ellipse([px - cap, py - cap, px + cap, py + cap], fill=fill)

    # Half-sun: the upper semicircle, flat base resting on the horizon.
    d.pieslice([cx - R, horizon - R, cx + R, horizon + R], 180, 360, fill=fill)

    # Broken horizon line: a base bar beneath the sun, plus a segment to each
    # side, with small gaps — echoing the source.
    t = int(w * 0.05)
    half = t // 2
    gap = int(w * 0.045)
    inset = int(w * 0.045)
    base_x0, base_x1 = cx - int(R * 1.12), cx + int(R * 1.12)
    segments = [
        (base_x0, base_x1),                       # under the sun
        (inset, base_x0 - gap),                   # left of the sun
        (base_x1 + gap, w - inset),               # right of the sun
    ]
    for x0, x1 in segments:
        if x1 - x0 > t:                            # skip degenerate slivers
            d.rounded_rectangle([x0, horizon - half, x1, horizon + half],
                                radius=half, fill=fill)

    # Round the tile corners.
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=RADIUS, fill=255)
    content.putalpha(mask)
    img.alpha_composite(content, (MARGIN, MARGIN))
    return img


def build_icns(master: Image.Image) -> Path:
    master.resize((1024, 1024), Image.LANCZOS).save(ASSETS / "icon_1024.png")
    iconset = ASSETS / "Rituals.iconset"
    iconset.mkdir(exist_ok=True)
    specs = [
        ("icon_16x16.png", 16), ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32), ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128), ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256), ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512), ("icon_512x512@2x.png", 1024),
    ]
    for name, px in specs:
        master.resize((px, px), Image.LANCZOS).save(iconset / name)
    icns = ROOT / "icon.icns"
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns)], check=True)
    return icns


if __name__ == "__main__":
    icns = build_icns(build_master())
    print(f"Wrote assets/icon_1024.png and {icns.relative_to(ROOT)}")
