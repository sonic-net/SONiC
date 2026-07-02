#!/usr/bin/env python3
"""Generate §7.1 Frame Envelope figure — database : table : frame kind : payload."""

import os

from PIL import Image, ImageDraw

from figure_common import BG, MUTED, TEXT, load_font, wrap_center

IMG_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(IMG_DIR, "centralized_ipc_frame_envelope.png")

IMG_W = 1024
IMG_H = 210

C_DB = (66, 133, 244)
C_TABLE = (142, 68, 173)
C_KIND = (230, 126, 34)
C_PAYLOAD = (39, 174, 96)
C_FRAME = (120, 120, 140)


def draw_title_block(draw, title, subtitle, title_font, sub_font, width):
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((width - (bbox[2] - bbox[0])) / 2, 12), title, font=title_font, fill=TEXT)
    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    draw.text(((width - (bbox[2] - bbox[0])) / 2, 38), subtitle, font=sub_font, fill=MUTED)


def segment(draw, x, y, w, h, title, value, color, title_font, value_font):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=10, outline=color, width=2, fill=(255, 255, 255))
    # color accent bar
    draw.rounded_rectangle([x + 2, y + 2, x + w - 2, y + 24], radius=8, fill=color + (48,))
    wrap_center(draw, title, x + w / 2, y + 5, title_font, fill=TEXT)
    wrap_center(draw, value, x + w / 2, y + h // 2 + 6, value_font, fill=TEXT)


def colon(draw, x, y, font):
    bbox = draw.textbbox((0, 0), ":", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x - tw / 2, y - th / 2), ":", font=font, fill=(100, 100, 100))


def main():
    title_font = load_font(22, bold=True)
    sub_font = load_font(13)
    seg_title_font = load_font(12, bold=True)
    value_font = load_font(15, bold=True)
    colon_font = load_font(22, bold=True)

    img = Image.new("RGB", (IMG_W, IMG_H), BG)
    draw = ImageDraw.Draw(img)
    draw_title_block(
        draw,
        "Midplane Frame Envelope",
        "Logical layout of every data frame on the midplane bus",
        title_font,
        sub_font,
        IMG_W,
    )

    margin = 40
    frame_x = margin
    frame_y = 68
    frame_w = IMG_W - 2 * margin
    frame_h = 100
    draw.rounded_rectangle(
        [frame_x, frame_y, frame_x + frame_w, frame_y + frame_h],
        radius=12,
        outline=C_FRAME,
        width=2,
        fill=(250, 251, 253),
    )
    wrap_center(draw, "Midplane data frame", frame_x + frame_w / 2, frame_y + 10, seg_title_font, fill=MUTED)

    inner_y = frame_y + 28
    inner_h = frame_h - 34
    gap = 16
    n_cols = 4
    total_gap = gap * (n_cols - 1) + 28  # colons + padding
    col_w = (frame_w - total_gap) // n_cols
    x = frame_x + 14

    cols = [
        ("Database", "APPL_DB", C_DB),
        ("Table", "ROUTE_TABLE", C_TABLE),
        ("Frame kind", "single | batch", C_KIND),
        ("Payload", "set / delete …", C_PAYLOAD),
    ]

    for i, (title, value, color) in enumerate(cols):
        segment(draw, x, inner_y, col_w, inner_h, title, value, color, seg_title_font, value_font)
        x += col_w
        if i < n_cols - 1:
            colon(draw, x + gap / 2, inner_y + inner_h / 2, colon_font)
            x += gap

    img.save(OUT, "PNG")
    print("Wrote", OUT, f"({IMG_W}x{IMG_H})")


if __name__ == "__main__":
    main()
