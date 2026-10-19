"""waterlevel: container with animated rising water.

A rect container outline; water fills from bottom to `level` (0-1) with a
gently waving surface. Level can animate over [t0, t1].

Node params:
    level   float 0-1, or [from, to] for animation
    t0, t1  scene-local times for the level animation
    wave    surface wave amplitude px (default 3)
"""
import math
from . import register


@register('waterlevel')
def draw(draw, box, t, node, style, col, fonts):
    lv = node.get('level', 0.5)
    t0 = float(node.get('t0', 0))
    t1 = float(node.get('t1', 1))
    if isinstance(lv, (list, tuple)) and len(lv) == 2:
        if t <= t0:
            level = float(lv[0])
        elif t >= t1:
            level = float(lv[1])
        else:
            f = (t - t0) / (t1 - t0)
            f = f * f * (3 - 2 * f)  # smoothstep
            level = float(lv[0]) + (float(lv[1]) - float(lv[0])) * f
    else:
        level = float(lv)
    level = max(0.0, min(1.0, level))
    wave = float(node.get('wave', 3))
    water = col('color', '#4A90D9')
    ink = col('ink', '$ink')

    x0, y0 = box.x, box.y
    x1, y1 = box.x + box.w, box.y + box.h
    # container: rounded outline
    draw.rounded_rectangle([x0, y0, x1, y1], radius=10,
                           outline=(ink[0], ink[1], ink[2], 200), width=3)
    if level <= 0.001:
        return
    # water fill with wavy top surface
    wy = y1 - level * (y1 - y0 - 8) - 4
    pts = [(x0 + 4, y1 - 4)]
    steps = max(8, int(box.w / 12))
    for s in range(steps + 1):
        px = x0 + 4 + (box.w - 8) * s / steps
        py = wy + math.sin(px * 0.06 + t * 3.0) * wave
        pts.append((px, py))
    pts.append((x1 - 4, y1 - 4))
    draw.polygon(pts, fill=(water[0], water[1], water[2], 150))
    # surface highlight line
    surf = [(x0 + 4 + (box.w - 8) * s / steps,
             wy + math.sin((x0 + 4 + (box.w - 8) * s / steps) * 0.06 + t * 3.0) * wave)
            for s in range(steps + 1)]
    if len(surf) > 1:
        draw.line(surf, fill=(255, 255, 255, 130), width=2)
