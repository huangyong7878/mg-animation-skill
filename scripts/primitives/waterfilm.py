"""waterfilm: continuous water film on a surface.

Unlike `flow` (discrete dashes), this renders an unbroken translucent
water layer with internal streaks drifting horizontally — the "一层水"
look for road/ground surfaces. Deterministic function of t.

Node params:
    depth      film thickness in px (default 10)
    speed      streak drift px/s (default 120)
    direction  1 (right) or -1 (left), default 1
    streaks    internal highlight streak count (default 12)
"""
from . import register, hash01


@register('waterfilm')
def draw(draw, box, t, node, style, col, fonts):
    depth = float(node.get('depth', 10))
    speed = float(node.get('speed', 120))
    direction = int(node.get('direction', 1))
    n = int(node.get('streaks', 12))
    base = col('color', '#4A90D9')
    y0 = box.y
    y1 = box.y + min(depth, box.h)

    # base film: translucent blue
    draw.rounded_rectangle([box.x, y0, box.x + box.w, y1], radius=depth / 2,
                           fill=(base[0], base[1], base[2], 95))
    # top glint line (water surface)
    draw.line([(box.x + 2, y0 + 1), (box.x + box.w - 2, y0 + 1)],
              fill=(255, 255, 255, 110), width=1)
    # internal streaks drifting
    for k in range(n):
        span = box.w + 40
        x = box.x - 20 + ((hash01(k, 61) * span + direction * speed * t) % span)
        ln = 22 + 26 * hash01(k, 62)
        sy = y0 + 2 + hash01(k, 63) * max(1, (y1 - y0 - 4))
        sa = 60 + int(70 * hash01(k, 64))
        if direction > 0:
            draw.line([(x, sy), (x + ln, sy)],
                      fill=(235, 245, 255, sa), width=2)
        else:
            draw.line([(x - ln, sy), (x, sy)],
                      fill=(235, 245, 255, sa), width=2)
