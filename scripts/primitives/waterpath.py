"""waterpath: particles following a continuous polyline path.

One unbroken water journey, e.g. road surface -> drain slot -> underground
pipe. Particles are spaced along the path by arc length and loop forever.
Deterministic function of t.

Node params:
    path      list of [fx, fy] waypoints, fractions of box (0-1). Required.
    particles int, default 14
    speed     px/s along path, default 170
    size      droplet radius, default 3.2
    color     water color (via style)
"""
from . import register, hash01, seg_lengths, point_at


@register('waterpath')
def draw(draw, box, t, node, style, col, fonts):
    raw = node.get('path') or []
    if len(raw) < 2:
        return
    pts = [(box.x + fx * box.w, box.y + fy * box.h) for fx, fy in raw]
    ls = seg_lengths(pts)
    total = sum(ls)
    if total < 1:
        return
    n = int(node.get('particles', 14))
    speed = float(node.get('speed', 170))
    r = float(node.get('size', 3.2))
    base = col('color', '#4A90D9')

    for i in range(n):
        d = (hash01(i, 91) * total + speed * t) % total
        x, y, dx, dy = point_at(pts, ls, total, d)
        prog = d / total
        # envelope: fade in at path start, fade out near the end
        if prog < 0.04:
            env = prog / 0.04
        elif prog > 0.92:
            env = max(0.0, (1 - prog) / 0.08)
        else:
            env = 1.0
        a = round(base[3] * env)
        if a < 5:
            continue
        # droplet elongated along direction of travel
        rx, ry = r * (1 + 0.9 * abs(dx)), r * (1 + 0.9 * abs(dy))
        draw.ellipse([x - rx, y - ry, x + rx, y + ry],
                     fill=(base[0], base[1], base[2], a))
