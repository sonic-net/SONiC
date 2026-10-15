#!/usr/bin/env python3
"""Generate all §8 Operational IPC flow figures (consistent with Figure 5)."""

import os
import sys

from PIL import Image, ImageDraw

from figure_common import (
    ARROW,
    BG,
    CONSUMER,
    DB,
    HUB_PARTICIPANTS,
    MUTED,
    ORCH,
    PROXY,
    PST,
    TEXT,
    W,
    draw_arrow,
    draw_ladder,
    draw_participants,
    draw_title_block,
    load_font,
    wrap_center,
)

IMG_DIR = os.path.dirname(os.path.abspath(__file__))


def gen_figure5():
    img = draw_ladder(
        918,
        HUB_PARTICIPANTS,
        [
            (0, 1, "1  set() / del()\n     (existing producer API)"),
            (1, 2, "2  Redis write"),
            (1, 3, "3  zmqEnhanced IPC send"),
            (3, 4, "4  Deliver update"),
            (4, 5, "5  pops() drain"),
            (5, 6, "6  Program ASIC"),
        ],
        [88, 72, 72, 72, 72, 72],
        "Steady-State Ladder — Single Operation (Hub-and-Spoke)",
        "Application uses existing ProducerStateTable API; hub-and-spoke delivery to zmqEnhanced consumer",
    )
    img.save(os.path.join(IMG_DIR, "centralized_ipc_flow_steady_state.png"), "PNG")


def gen_figure6():
    """Per-key coalescing — three-step flow: accumulate → flush → outcomes."""
    title_font = load_font(26, bold=True)
    sub_font = load_font(15)
    phase_font = load_font(15, bold=True)
    label_font = load_font(14, bold=True)
    small_font = load_font(12)
    mono_font = load_font(13)

    y0 = 100
    acc_x, acc_y, acc_w, acc_h = 56, y0 + 32, 380, 252
    acc_cy = acc_y + acc_h / 2

    flush_x, flush_w, flush_h = 500, 160, 100
    flush_y = acc_cy - flush_h / 2

    out_x, out_w = 820, 660
    mid_h = 132
    out_y = acc_cy - mid_h / 2
    panel_bottom = out_y + mid_h
    content_bottom = max(acc_y + acc_h, panel_bottom)
    caption_y = content_bottom + 28

    arrow_y = acc_cy

    H = caption_y + 24
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_title_block(
        draw,
        "Per-Key Coalescing — One Flush Window",
        "Same route key: six buffered calls collapse on the pending midplane map",
        title_font,
        sub_font,
    )

    def rbox(x, y, w, h, text, color, sub=None, fill_alpha=35):
        draw.rounded_rectangle([x, y, x + w, y + h], radius=10, outline=color, width=2, fill=color + (fill_alpha,))
        wrap_center(draw, text, x + w / 2, y + 14, label_font, fill=TEXT)
        if sub:
            wrap_center(draw, sub, x + w / 2, y + 42, small_font, fill=MUTED)

    def arrow_h(x1, x2, y):
        draw.line([(x1, y), (x2, y)], fill=ARROW, width=2)
        draw.polygon([(x2, y), (x2 - 10, y - 5), (x2 - 10, y + 5)], fill=ARROW)

    # Step labels
    for x, label in [(100, "① Accumulate"), (520, "② flush()"), (980, "③ Outcome")]:
        draw.text((x, y0), label, font=phase_font, fill=TEXT)

    # ① Accumulate
    draw.rounded_rectangle([acc_x, acc_y, acc_x + acc_w, acc_y + acc_h], radius=12, outline=(66, 133, 244), width=2, fill=(66, 133, 244, 20))
    wrap_center(draw, "Route key: 10.0.0.0/24", acc_x + acc_w / 2, acc_y + 14, label_font, fill=TEXT)
    wrap_center(draw, "buffered set() / del() × 6", acc_x + acc_w / 2, acc_y + 36, small_font, fill=MUTED)
    ops = [
        ("1.", "set(nexthop=A)", (39, 174, 96)),
        ("2.", "set(nexthop=B)", (39, 174, 96)),
        ("3.", "set(nexthop=C)", (39, 174, 96)),
        ("4.", "delete", (231, 76, 60)),
        ("5.", "set(nexthop=D)", (39, 174, 96)),
        ("6.", "set(nexthop=E)", (39, 174, 96)),
    ]
    oy = acc_y + 60
    for num, op, col in ops:
        draw.rounded_rectangle([acc_x + 24, oy, acc_x + acc_w - 24, oy + 26], radius=6, outline=col, width=1, fill=col + (30,))
        draw.text((acc_x + 36, oy + 5), num, font=mono_font, fill=TEXT)
        draw.text((acc_x + 64, oy + 5), op, font=mono_font, fill=TEXT)
        oy += 30

    # ② flush
    arrow_h(acc_x + acc_w, flush_x, arrow_y)
    rbox(flush_x, flush_y, flush_w, flush_h, "ProducerStateTable", (142, 68, 173), "flush()")

    # ③ Outcome — midplane only
    arrow_h(flush_x + flush_w, out_x, arrow_y)

    draw.rounded_rectangle([out_x, out_y, out_x + out_w, out_y + mid_h], radius=12, outline=(39, 174, 96), width=2, fill=(39, 174, 96, 18))
    draw.text((out_x + 16, out_y + 10), "Midplane — coalesced", font=label_font, fill=(39, 120, 70))
    draw.text((out_x + 16, out_y + 32), "Pending map → 2 entries in one frame", font=small_font, fill=MUTED)
    rbox(out_x + 40, out_y + 52, 260, 50, "DELETE 10.0.0.0/24", (231, 76, 60))
    rbox(out_x + 340, out_y + 52, 260, 50, "SET nh=E", (39, 174, 96))
    wrap_center(draw, "zmqEnhanced IPC send → consumer pops()", out_x + out_w // 2, out_y + 108, small_font, fill=MUTED)

    wrap_center(
        draw,
        "Coalescing applies to the midplane map only — each key is independent",
        W / 2,
        caption_y,
        small_font,
        fill=MUTED,
    )

    img.save(os.path.join(IMG_DIR, "centralized_ipc_per_key_coalescing.png"), "PNG")


def gen_figure7():
    """Full database sync — ladder: join → snapshot + PST local queue → send after complete → drain."""
    title_font = load_font(26, bold=True)
    sub_font = load_font(15)
    step_font = load_font(13)
    phase_font = load_font(13, bold=True)
    small_font = load_font(12)
    pst_color = (142, 68, 173)

    def draw_step_arrow(draw, xs, y, src, dst, label, dashed=False, label_y_offset=-30):
        x0, x1 = xs[src], xs[dst]
        if dashed:
            for x in range(int(min(x0, x1)), int(max(x0, x1)), 14):
                x_end = min(x + 8, max(x0, x1))
                draw.line([(x, y), (x_end, y)], fill=ARROW, width=2)
        else:
            draw.line([(x0, y), (x1, y)], fill=ARROW, width=2)
        if x1 > x0:
            draw.polygon([(x1, y), (x1 - 10, y - 5), (x1 - 10, y + 5)], fill=ARROW)
        else:
            draw.polygon([(x1, y), (x1 + 10, y - 5), (x1 + 10, y + 5)], fill=ARROW)
        wrap_center(draw, label, (x0 + x1) / 2, y + label_y_offset, step_font, fill=TEXT)

    def draw_pst_local_queue(draw, lifeline_x, y):
        """Step 4 — live update flows down PST lifeline into a local queue stack."""
        stack_w, stack_h, layers = 100, 20, 3
        stack_x = lifeline_x - stack_w // 2
        stack_y = y + 10
        pad = 8
        bx = stack_x - pad
        by = stack_y - pad
        bw = stack_w + layers * 4 + pad * 2
        bh = stack_h + layers * 4 + pad * 2 + 22
        draw.rounded_rectangle(
            [bx - 4, by - 4, bx + bw + 4, by + bh + 4],
            radius=10,
            fill=(255, 255, 255),
            outline=(220, 220, 220),
            width=1,
        )
        for layer in range(layers - 1, -1, -1):
            ox, oy = layer * 5, layer * 5
            fill = (252, 246, 252) if layer == 0 else (244, 236, 248)
            draw.rounded_rectangle(
                [stack_x + ox, stack_y + oy, stack_x + ox + stack_w, stack_y + oy + stack_h],
                radius=5,
                outline=pst_color,
                width=2 if layer == 0 else 1,
                fill=fill,
            )
        wrap_center(draw, "PST local queue", lifeline_x, stack_y + stack_h + layers * 5 + 10, step_font, fill=TEXT)

        draw.line([(lifeline_x, y - 24), (lifeline_x, stack_y - 2)], fill=ARROW, width=2)
        draw.polygon([(lifeline_x, stack_y - 2), (lifeline_x - 5, stack_y - 12), (lifeline_x + 5, stack_y - 12)], fill=ARROW)
        wrap_center(draw, "4  live update", lifeline_x + 58, y - 8, small_font, fill=TEXT)

    pst_hub = ("ProducerStateTable", pst_color, "(zmqEnhanced PST)")
    db_hub = ("Central Application\nDatabase", (231, 76, 60), "(hub snapshot)")
    participants = [pst_hub, db_hub, PROXY, CONSUMER, ORCH]

    gaps = [58, 54, 68, 92, 54, 58, 54, 58, 54]
    steps = [
        {"kind": "arrow", "src": 3, "dst": 2, "label": "1  Connect to proxy backend", "dashed": False, "label_off": -30},
        {"kind": "arrow", "src": 2, "dst": 3, "label": "2  Subscription ready", "dashed": True, "label_off": -30},
        {"kind": "arrow", "src": 3, "dst": 1, "label": "3  Read full hub table", "dashed": False, "label_off": 14},
        {"kind": "pst_queue"},
        {"kind": "arrow", "src": 1, "dst": 3, "label": "5  Snapshot complete", "dashed": True, "label_off": -30},
        {"kind": "arrow", "src": 3, "dst": 4, "label": "6  pops() — snapshot batch", "dashed": False, "label_off": -30},
        {"kind": "arrow", "src": 0, "dst": 2, "label": "7  zmqEnhanced IPC send\n     (queued PST updates)", "dashed": False, "label_off": -34},
        {"kind": "arrow", "src": 2, "dst": 3, "label": "8  Deliver queued deltas", "dashed": False, "label_off": -30},
        {"kind": "arrow", "src": 3, "dst": 4, "label": "9  pops() — queued live deltas", "dashed": False, "label_off": -30},
    ]

    top_y, header_h = 100, 88
    margin_x = 48
    lifeline_top = top_y + header_h + 8
    y_start = lifeline_top + 42
    content_bottom = y_start + sum(gaps)
    H = content_bottom + 44

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_title_block(
        draw,
        "Full Database Sync Ladder — Slow-Joiner Mitigation",
        "PST holds live updates locally during snapshot; midplane send only after snapshot complete",
        title_font,
        sub_font,
    )

    n = len(participants)
    col_w = (W - 2 * margin_x) / n
    hub_x0 = margin_x + 2
    hub_x1 = margin_x + 2 * col_w - 2
    draw.rounded_rectangle(
        [hub_x0, top_y - 6, hub_x1, top_y + header_h + 6],
        radius=10,
        outline=(160, 160, 180),
        width=1,
        fill=(248, 248, 252),
    )
    wrap_center(draw, "Supervisor hub", (hub_x0 + hub_x1) / 2, top_y - 4, small_font, fill=MUTED)

    xs, lifeline_top = draw_participants(draw, participants, top_y=top_y, header_h=header_h, img_h=H)

    y = y_start
    step_ys = []
    for _ in steps:
        step_ys.append(y)
        y += gaps[len(step_ys) - 1]

    band_top = step_ys[2] - 26
    band_bottom = step_ys[4] - 20
    draw.rounded_rectangle(
        [200, band_top, W - 48, band_bottom],
        radius=10,
        outline=(220, 180, 90),
        width=1,
        fill=(255, 248, 225),
    )
    wrap_center(
        draw,
        "Snapshot in progress — no midplane send until snapshot complete",
        (200 + W - 48) / 2,
        band_top + 8,
        small_font,
        fill=(140, 100, 30),
    )

    draw.text((52, step_ys[0] - 10), "① Join", font=phase_font, fill=TEXT)
    draw.text((52, step_ys[2] + 4), "② Snapshot\n   + PST hold", font=phase_font, fill=TEXT)
    draw.text((52, step_ys[6] - 6), "③ Send queue\n   + drain", font=phase_font, fill=TEXT)

    y = y_start
    for idx, step in enumerate(steps):
        if step["kind"] == "pst_queue":
            draw_pst_local_queue(draw, xs[0], y)
        else:
            draw_step_arrow(
                draw,
                xs,
                y,
                step["src"],
                step["dst"],
                step["label"],
                dashed=step["dashed"],
                label_y_offset=step["label_off"],
            )
        y += gaps[idx]

    wrap_center(
        draw,
        "After snapshot complete: pops() snapshot batch; PST flushes local queue to midplane; pops() queued deltas",
        W / 2,
        content_bottom + 20,
        small_font,
        fill=MUTED,
    )

    img.save(os.path.join(IMG_DIR, "centralized_ipc_flow_cold_start.png"), "PNG")


def main():
    gen_figure5()
    gen_figure6()
    gen_figure7()
    print("Generated §8 figures in", IMG_DIR)


if __name__ == "__main__":
    main()
