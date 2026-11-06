"""Shared drawing helpers for §8 Operational IPC flow figures."""

from PIL import Image, ImageDraw, ImageFont

W = 1536
BG = (255, 255, 255)
GRID = (220, 220, 220)
TEXT = (30, 30, 30)
MUTED = (90, 90, 90)
ARROW = (60, 60, 60)

# Figure 5 reference participants (hub → spoke)
HUB_PARTICIPANTS = [
    ("Application\ndaemon", (66, 133, 244)),
    ("ProducerStateTable", (142, 68, 173), "(zmqEnhanced path for IPC-carried tables)"),
    ("Central Application\nDatabase", (231, 76, 60)),
    ("Midplane message\nproxy", (230, 126, 34)),
    ("zmqEnhanced\nconsumer", (39, 174, 96), "(one per IPC-carried table)"),
    ("orchagent", (52, 152, 219), "(host consumer)"),
    ("ASIC", (127, 140, 141)),
]

PST = ("ProducerStateTable", (142, 68, 173), "(zmqEnhanced path)")
DB = ("Central Application\nDatabase", (231, 76, 60))
PROXY = ("Midplane message\nproxy", (230, 126, 34))
CONSUMER = ("zmqEnhanced\nconsumer", (39, 174, 96), "(one per IPC-carried table)")
ORCH = ("orchagent", (52, 152, 219), "(host consumer)")


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


def wrap_center(draw, text, cx, y, font, fill=TEXT, line_gap=4):
    lines = text.split("\n")
    cy = y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((cx - w / 2, cy), line, font=font, fill=fill)
        cy += h + line_gap
    return cy - y


def draw_title_block(draw, title, subtitle, title_font, sub_font):
    bbox = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((W - (bbox[2] - bbox[0])) / 2, 24), title, font=title_font, fill=TEXT)
    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    draw.text(((W - (bbox[2] - bbox[0])) / 2, 62), subtitle, font=sub_font, fill=MUTED)


def draw_participants(draw, participants, margin_x=48, top_y=110, header_h=92, width=W, img_h=918):
    n = len(participants)
    col_w = (width - 2 * margin_x) / n
    xs = [margin_x + col_w * (i + 0.5) for i in range(n)]
    head_font = load_font(15, bold=True)
    subhead_font = load_font(12)
    for i, p in enumerate(participants):
        color = p[1]
        x0 = margin_x + col_w * i + 6
        x1 = margin_x + col_w * (i + 1) - 6
        draw.rounded_rectangle([x0, top_y, x1, top_y + header_h], radius=10, fill=color + (40,), outline=color, width=2)
        wrap_center(draw, p[0], xs[i], top_y + 14, head_font, fill=TEXT)
        if len(p) > 2:
            wrap_center(draw, p[2], xs[i], top_y + 52, subhead_font, fill=MUTED)
    lifeline_top = top_y + header_h + 8
    lane_bottom = img_h - 36
    for x in xs:
        for y in range(lifeline_top, lane_bottom, 10):
            draw.line([(x, y), (x, min(y + 5, lane_bottom))], fill=GRID, width=2)
    return xs, lifeline_top


def draw_arrow(draw, xs, y, src, dst, label, step_font, dashed=False):
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
    wrap_center(draw, label, (x0 + x1) / 2, y - 28, step_font, fill=TEXT)


def draw_ladder(img_h, participants, steps, gaps, title, subtitle):
    img = Image.new("RGB", (W, img_h), BG)
    draw = ImageDraw.Draw(img)
    title_font = load_font(28, bold=True)
    sub_font = load_font(16)
    step_font = load_font(14)
    draw_title_block(draw, title, subtitle, title_font, sub_font)
    xs, lifeline_top = draw_participants(draw, participants, top_y=110, header_h=92, img_h=img_h)
    y = lifeline_top + 55
    for idx, step in enumerate(steps):
        src, dst, label = step[0], step[1], step[2]
        dashed = len(step) > 3 and step[3]
        draw_arrow(draw, xs, y, src, dst, label, step_font, dashed=dashed)
        y += gaps[idx]
    return img
