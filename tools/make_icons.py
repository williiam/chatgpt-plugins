#!/usr/bin/env python3
"""Draw the Billsmith listing icons (needs Pillow; run only when the art changes).

    python3 tools/make_icons.py
"""

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'plugins', 'billsmith', 'assets')
SCALE = 4  # supersampling factor for smooth edges
TOP, BOTTOM = (46, 107, 235), (24, 60, 160)
ACCENT, LINE = (31, 79, 191), (198, 205, 220)


def draw(size, inset):
    """size: output pixels. inset: transparent margin as a fraction of the canvas."""
    big = size * SCALE
    pad = int(big * inset)
    side = big - 2 * pad

    gradient = Image.new('RGB', (1, big))
    for y in range(big):
        t = y / (big - 1)
        gradient.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM)))
    gradient = gradient.resize((big, big))
    mask = Image.new('L', (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((pad, pad, big - pad - 1, big - pad - 1), int(side * 0.225), fill=255)
    art = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    art.paste(gradient, (0, 0), mask)
    d = ImageDraw.Draw(art)

    def box(x0, y0, x1, y1):
        return (pad + side * x0, pad + side * y0, pad + side * x1, pad + side * y1)

    d.rounded_rectangle(box(0.25, 0.16, 0.75, 0.84), side * 0.055, fill=(255, 255, 255, 255))
    d.rounded_rectangle(box(0.32, 0.245, 0.52, 0.295), side * 0.025, fill=ACCENT)
    for row in range(3):
        y = 0.385 + row * 0.085
        d.rounded_rectangle(box(0.32, y, 0.54, y + 0.034), side * 0.017, fill=LINE)
        d.rounded_rectangle(box(0.60, y, 0.68, y + 0.034), side * 0.017, fill=LINE)
    d.rounded_rectangle(box(0.47, 0.675, 0.68, 0.755), side * 0.03, fill=ACCENT)
    return art.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(ASSETS, exist_ok=True)
    draw(512, 0.06).save(os.path.join(ASSETS, 'logo.png'), optimize=True)
    draw(256, 0.0).save(os.path.join(ASSETS, 'icon.png'), optimize=True)
    for skill in ('create-invoice', 'create-quote', 'create-receipt'):
        folder = os.path.join(ROOT, 'plugins', 'billsmith', 'skills', skill, 'assets')
        os.makedirs(folder, exist_ok=True)
        draw(128, 0.0).save(os.path.join(folder, 'icon.png'), optimize=True)


if __name__ == '__main__':
    main()
