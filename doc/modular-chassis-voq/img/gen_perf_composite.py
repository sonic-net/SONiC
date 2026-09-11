#!/usr/bin/env python3
"""Generate side-by-side performance composite (slide 4 style) for local review."""

import os
from PIL import Image, ImageDraw, ImageFont

IMG_DIR = os.path.dirname(os.path.abspath(__file__))
LEFT_SRC = os.path.join(IMG_DIR, "centralized_ipc_perf_redis_convergence.png")
RIGHT_SRC = os.path.join(IMG_DIR, "centralized_ipc_perf_hybrid_throughput.png")
OUT = os.path.join(IMG_DIR, "centralized_ipc_perf_analysis_composite.png")

BG = (255, 255, 255)
TITLE_BG = (0, 48, 87)  # slide-like banner
TITLE_FG = (255, 255, 255)
SUBTITLE_FG = (30, 30, 30)
RULE = (200, 200, 200)
PAD = 32
GAP = 24
BANNER_H = 72
SUBTITLE_H = 44


def load_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_width(img: Image.Image, target_w: int) -> Image.Image:
    w, h = img.size
    scale = target_w / w
    return img.resize((target_w, int(h * scale)), Image.Resampling.LANCZOS)


def main():
    left = Image.open(LEFT_SRC).convert("RGBA")
    right = Image.open(RIGHT_SRC).convert("RGBA")

    canvas_w = 1600
    panel_w = (canvas_w - 2 * PAD - GAP) // 2
    left_fit = fit_width(left, panel_w)
    right_fit = fit_width(right, panel_w)
    chart_h = max(left_fit.height, right_fit.height)

    canvas_h = PAD + BANNER_H + SUBTITLE_H + chart_h + PAD
    canvas = Image.new("RGB", (canvas_w, canvas_h), BG)
    draw = ImageDraw.Draw(canvas)

    title_font = load_font(28, bold=True)
    subtitle_font = load_font(20, bold=True)

    draw.rectangle((0, PAD, canvas_w, PAD + BANNER_H), fill=TITLE_BG)
    title = "Zmq + Redis Performance Analysis"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((canvas_w - tw) / 2, PAD + (BANNER_H - th) / 2), title, font=title_font, fill=TITLE_FG)

    y_sub = PAD + BANNER_H
    left_x = PAD
    right_x = PAD + panel_w + GAP

    for x, label in ((left_x, "Redis-Only Approach"), (right_x, "Zmq + Redis Based Approach")):
        bbox = draw.textbbox((0, 0), label, font=subtitle_font)
        lw = bbox[2] - bbox[0]
        draw.text((x + (panel_w - lw) / 2, y_sub + 10), label, font=subtitle_font, fill=SUBTITLE_FG)

    y_chart = y_sub + SUBTITLE_H
    canvas.paste(left_fit, (left_x, y_chart), left_fit)
    canvas.paste(right_fit, (right_x, y_chart), right_fit)

    draw.line((left_x + panel_w + GAP / 2, y_chart, left_x + panel_w + GAP / 2, y_chart + chart_h), fill=RULE, width=2)

    canvas.save(OUT, "PNG")
    print(f"Wrote {OUT} ({canvas.size[0]}x{canvas.size[1]})")


if __name__ == "__main__":
    main()
