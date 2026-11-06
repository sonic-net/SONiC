#!/usr/bin/env python3
"""Generate Figure 5 — convergence time vs route count (Redis-only vs Zmq + Redis)."""

import os
from PIL import Image, ImageDraw, ImageFont

IMG_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(IMG_DIR, "zmq_redis_convergence_timing.png")

routes = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

redis_single = [1.5, 2.0, 2.5, 2.5, 4.0, 5.0, 5.5, 7.0, 7.5, 7.5]
redis_multi = [3.5, 5.0, 15.0, 10.0, 13.0, 15.5, 19.0, 20.0, 25.0, 26.5]

zmq_measured_ks = {60: 4.37, 90: 8.67, 100: 9.64}
rate_early = 60000 / 4.365


def zmq_single_at(k):
    n = k * 1000
    if n <= 60000:
        return round(n / rate_early, 1)
    if n <= 90000:
        return round(
            zmq_measured_ks[60]
            + (zmq_measured_ks[90] - zmq_measured_ks[60]) * (n - 60000) / 30000,
            1,
        )
    return round(
        zmq_measured_ks[90]
        + (zmq_measured_ks[100] - zmq_measured_ks[90]) * (n - 90000) / 10000,
        1,
    )


zmq_single = [zmq_single_at(k) for k in routes]
fanout_ratio = 30.85 / 32.29
zmq_multi = [round(v * fanout_ratio, 1) for v in zmq_single]


def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    w, h = 1680, 880
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    title_f = load_font(30, bold=True)
    banner_f = load_font(22, bold=True)
    sub_f = load_font(14)
    axis_f = load_font(14)
    val_f = load_font(12, bold=True)
    tick_f = load_font(12)
    note_f = load_font(11)

    banner_h = 68
    draw.rectangle([0, 0, w, banner_h], fill=(0, 48, 87))
    draw.text(
        (w // 2, banner_h // 2),
        "Convergence Time vs Route Count — Redis-Only vs Zmq + Redis",
        fill=(255, 255, 255),
        font=title_f,
        anchor="mm",
    )

    panel_gap = 36
    pad = 48
    panel_w = (w - 2 * pad - panel_gap) // 2
    top = banner_h + 28
    bottom = h - 48
    left_x = pad
    right_x = pad + panel_w + panel_gap

    blue = (66, 133, 244)
    green = (39, 174, 96)
    grid = (230, 230, 230)
    text = (30, 30, 30)
    muted = (100, 100, 100)
    ymax = 30

    subtitle = "Single subscriber vs median across 15 line-card subscribers"
    legend_multi = "Median (15 subscribers)"

    def draw_panel(x0, title, series_a, series_b):
        x1 = x0 + panel_w
        draw.text((x0 + panel_w // 2, top - 6), title, fill=text, font=banner_f, anchor="mm")
        draw.text((x0 + panel_w // 2, top + 22), subtitle, fill=muted, font=sub_f, anchor="mm")

        ml, mr, mt, mb = 62, 18, 58, 58
        px0, py0 = x0 + ml, top + mt
        px1, py1 = x1 - mr, bottom - mb
        pw, ph = px1 - px0, py1 - py0

        def xpos(i):
            return px0 + i / (len(routes) - 1) * pw

        def ypos(sec):
            return py1 - sec / ymax * ph

        for y in range(0, ymax + 1, 5):
            yy = ypos(y)
            draw.line([(px0, yy), (px1, yy)], fill=grid, width=1)
            draw.text((px0 - 8, yy), str(y), fill=muted, font=tick_f, anchor="rm")

        for i, k in enumerate(routes):
            xx = xpos(i)
            draw.line([(xx, py1), (xx, py1 + 5)], fill=muted, width=1)
            draw.text((xx, py1 + 8), f"{k}k", fill=muted, font=tick_f, anchor="mt")

        draw.text((px0 + pw // 2, py1 + 34), "Routes inserted into APPL_DB", fill=text, font=axis_f, anchor="mm")

        ylab = "Convergence time (s)"
        for i, ch in enumerate(ylab):
            draw.text((x0 + 14, py0 + i * 10), ch, fill=text, font=tick_f)

        bar_w = pw / len(routes) * 0.34
        colors = [blue, green]
        labels = ["Single subscriber", legend_multi]

        for si, (vals, label) in enumerate(zip([series_a, series_b], labels)):
            for i, v in enumerate(vals):
                cx = xpos(i)
                bx0 = cx - bar_w + si * bar_w * 1.05
                bx1 = bx0 + bar_w
                y1 = ypos(v)
                draw.rounded_rectangle([bx0, y1, bx1, py1], radius=3, fill=colors[si])
                draw.text(((bx0 + bx1) / 2, y1 - 5), f"{v:.1f}", fill=text, font=val_f, anchor="mb")

        lx, ly = px0 + 8, py0 + 6
        for si, label in enumerate(labels):
            draw.rounded_rectangle([lx, ly + si * 24, lx + 18, ly + 14 + si * 24], radius=2, fill=colors[si])
            draw.text((lx + 24, ly + 1 + si * 24), label, fill=text, font=tick_f)

    draw_panel(left_x, "Redis-Only Approach", redis_single, redis_multi)
    draw_panel(right_x, "Zmq + Redis Approach", zmq_single, zmq_multi)

    divx = left_x + panel_w + panel_gap // 2
    draw.line([(divx, top + 40), (divx, bottom - 20)], fill=(200, 200, 200), width=2)

    callout_y = bottom - 8
    draw.text(
        (left_x + panel_w // 2, callout_y),
        "100k routes:  7.5 s single  |  26.5 s median (15 LC)",
        fill=(180, 60, 60),
        font=note_f,
        anchor="mm",
    )
    draw.text(
        (right_x + panel_w // 2, callout_y),
        "100k routes:  9.6 s single  |  9.2 s median (15 LC)  — fan-out stays flat",
        fill=(30, 120, 70),
        font=note_f,
        anchor="mm",
    )

    img.save(OUT, "PNG")
    print(f"Wrote {OUT} ({w}x{h})")


if __name__ == "__main__":
    main()
