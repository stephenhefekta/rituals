#!/usr/bin/env python3
"""Generate the Rituals app icon (icon.icns): a flat, stylised sunset — a
burnt-orange sun on a horizon line with a ray fan above, on a warm cream tile
(WisprFlow-style: bold, flat, no gradients). Supersampled 2x for clean edges.

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
SUNSET = (224, 85, 46)        # burnt-orange


def build_master() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    w = h = S - 2 * MARGIN
    content = Image.new("RGBA", (w, h), CREAM + (255,))
    d = ImageDraw.Draw(content)

    cx = w // 2
    horizon = int(h * 0.60)
    R = int(w * 0.20)

    # Ray fan over the sun's upper half.
    for ang in range(-155, -24, 18):
        a = math.radians(ang)
        x1, y1 = cx + (R + w * 0.05) * math.cos(a), horizon + (R + w * 0.05) * math.sin(a)
        x2, y2 = cx + (R + w * 0.135) * math.cos(a), horizon + (R + w * 0.135) * math.sin(a)
        d.line([(x1, y1), (x2, y2)], fill=SUNSET + (255,), width=int(w * 0.026))
        for px, py in ((x1, y1), (x2, y2)):  # round the ray caps
            r = int(w * 0.013)
            d.ellipse([px - r, py - r, px + r, py + r], fill=SUNSET + (255,))

    # Sun.
    d.ellipse([cx - R, horizon - R, cx + R, horizon + R], fill=SUNSET + (255,))

    # Horizon line through the sun's middle.
    inset = int(w * 0.05)
    half = int(w * 0.013)
    d.rounded_rectangle([inset, horizon - half, w - inset, horizon + half],
                        radius=half, fill=SUNSET + (255,))

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
