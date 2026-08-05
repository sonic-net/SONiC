#!/usr/bin/env python3
"""Figure 6 — queues sit beside the vertical connector (socket on the wire)."""

import os

from PIL import Image, ImageDraw

from figure_common import BG, MUTED, TEXT, W, draw_title_block, load_font, wrap_center

IMG_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(IMG_DIR, "centralized_ipc_queueing_stack.png")

C_PST = (142, 68, 173)
C_PROXY = (230, 126, 34)
C_CONSUMER = (39, 174, 96)
C_ORCH = (52, 152, 219)
C_ARROW = (60, 60, 60)
Q_ZMQ = (230, 126, 34)
Q_INPROC = (142, 68, 173)
C_SAT_BG = (241, 245, 249)
C_SAT_BORDER = (203, 213, 225)
C_SAT_TEXT = (71, 85, 105)


def fig1_box(draw, x, y, w, h, title, color, font):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=10, outline=color, width=2, fill=color + (40,))
    bbox = draw.textbbox((0, 0), title, font=font)
    th = bbox[3] - bbox[1]
    draw.text((x + (w - (bbox[2] - bbox[0])) / 2, y + (h - th) / 2 - 1), title, font=font, fill=TEXT)


def sat_badge(draw, x, y, num, font):
    label = str(num)
    tw = draw.textbbox((0, 0), label, font=font)[2]
    r = 11
    draw.ellipse([x - r, y - r, x + r, y + r], fill=C_SAT_BG, outline=C_SAT_BORDER, width=1)
    draw.text((x - tw / 2, y - 6), label, font=font, fill=C_SAT_TEXT)


def draw_socket_queue(draw, x, y, w, h, color, n_slabs=5, sat=None, sat_f=None):
    """Vertical queue stack — sits beside the connector arrow."""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=6, outline=color, width=2, fill=(252, 253, 255))
    pad = 4
    slab_h = max(4, (h - pad * 2 - (n_slabs - 1) * 2) // n_slabs)
    sy = y + h - pad - slab_h
    for i in range(n_slabs):
        t = 45 + i * 22
        fill = tuple(min(255, int(c * (1 - t / 255) + 255 * (t / 255))) for c in color)
        draw.rounded_rectangle([x + pad, sy, x + w - pad, sy + slab_h], radius=2, outline=color, width=1, fill=fill)
        sy -= slab_h + 2
    if sat is not None:
        sat_badge(draw, x + w + 2, y + 4, sat, sat_f)


def arrow_v(draw, x, y0, y1):
    draw.line([(x, y0 + 2), (x, y1 - 10)], fill=C_ARROW, width=2)
    draw.polygon([(x, y1 - 4), (x - 5, y1 - 12), (x + 5, y1 - 12)], fill=C_ARROW)


def connector_with_queue(draw, lane_x, y, conn_h, color, sat, sat_f, q_w=54, q_h=48):
    """Vertical arrow with single queue beside it — socket on the wire."""
    y1 = y + conn_h
    arrow_v(draw, lane_x, y, y1)
    qx = lane_x + 20
    qy = y + (conn_h - q_h) // 2
    draw_socket_queue(draw, qx, qy, q_w, q_h, color, n_slabs=5, sat=sat, sat_f=sat_f)
    return y1


def connector_with_fanout_queues(draw, lane_x, y, conn_h, color, sat, sat_f, label_f):
    """XPUB fan-out — queue1, queue2, …, queue-n beside the connector."""
    y1 = y + conn_h
    arrow_v(draw, lane_x, y, y1)

    q_w, q_h = 42, 38
    gap = 6
    ell_w = 14
    labels = ["queue1", "queue2", "queue-n"]
    n_queues = 3
    group_w = n_queues * q_w + (n_queues - 1) * gap + ell_w + gap
    qx = lane_x + 20
    qy = y + 6

    sat_badge(draw, qx + group_w - 2, qy - 2, sat, sat_f)

    x = qx
    for i, lbl in enumerate(labels):
        if i == 2:
            draw.text((x + 2, qy + q_h // 2 - 6), "…", font=label_f, fill=MUTED)
            x += ell_w + gap
        draw_socket_queue(draw, x, qy, q_w, q_h, color, n_slabs=4)
        tw = draw.textbbox((0, 0), lbl, font=label_f)[2]
        draw.text((x + (q_w - tw) / 2, qy + q_h + 3), lbl, font=label_f, fill=MUTED)
        x += q_w + gap

    return y1


def main():
    lane_x = W // 2
    box_w = 380
    box_h = 56
    box_x = lane_x - box_w // 2
    conn = 62
    q_w, q_h = 54, 48

    title_f = load_font(26, bold=True)
    sub_f = load_font(14)
    box_f = load_font(14, bold=True)
    cap_f = load_font(12)
    sat_f = load_font(10, bold=True)
    q_label_f = load_font(9)

    img = Image.new("RGB", (W, 580), BG)
    draw = ImageDraw.Draw(img)

    draw_title_block(draw, "Queueing Across the IPC Stack",
                     "Saturation points on the steady-state path", title_f, sub_f)

    y = 92

    fig1_box(draw, box_x, y, box_w, box_h, "ProducerStateTable", C_PST, box_f)
    y += box_h
    y = connector_with_queue(draw, lane_x, y, conn, Q_ZMQ, 1, sat_f, q_w, q_h)

    fig1_box(draw, box_x, y, box_w, box_h, "Midplane message proxy", C_PROXY, box_f)
    y += box_h
    y = connector_with_fanout_queues(draw, lane_x, y, conn, Q_ZMQ, 2, sat_f, q_label_f)

    fig1_box(draw, box_x, y, box_w, box_h, "zmqEnhanced consumer", C_CONSUMER, box_f)
    y += box_h
    y = connector_with_queue(draw, lane_x, y, conn, Q_INPROC, 3, sat_f, q_w, q_h)

    fig1_box(draw, box_x, y, box_w, box_h, "orchagent", C_ORCH, box_f)
    y += box_h + 24

    wrap_center(draw, "Figure — Saturation queues ① PUB  ② XPUB  ③ received-op",
                lane_x, y, cap_f, fill=MUTED)

    img = img.crop((0, 0, W, y + 24))
    img.save(OUT, "PNG")
    print(f"Wrote {OUT} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
