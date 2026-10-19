"""soak: water infiltrating downward with a physical lifecycle.

Droplets spawn at the top surface, sink with organic meandering paths,
and fade in/out — like real infiltration through soil pores, not a
wrapping conveyor belt. A few droplets branch mid-depth.
Works on any rect; typically overlaid on a soil profile.
"""
import math
from . import register, hash01


@register('soak')
def draw(draw, box, t, node, style, col, fonts):
    drops = int(node.get('drops', 14))
    speed = float(node.get('speed', 42))          # px per second
    base = col('color', '#4A90D9')                # (r,g,b,a)
    depth = box.h
    for j in range(drops):
        travel = depth / speed
        cycle = travel * (1.15 + 0.5 * hash01(j, 71))
        lt = (t + hash01(j, 72) * cycle) % cycle
        if lt > travel:
            continue                              # resting phase, invisible
        prog = lt / travel
        # organic meander: two sines, different frequencies
        x0 = box.x + (j + 0.5) / drops * box.w
        x = (x0
             + math.sin(t * 1.6 + j * 2.1) * 4.0 * prog
             + math.sin(t * 0.7 + j * 5.3) * 2.5 * prog)
        y = box.y + prog * depth
        # envelope: quick fade-in, slow fade-out with depth
        if prog < 0.12:
            env = prog / 0.12
        else:
            env = 1.0 - (prog - 0.12) / 0.88 * 0.55
        a = round(base[3] * max(0.0, env))
        if a < 4:
            continue
        ry = 4 + prog * 4
        draw.ellipse([x - 2.6, y - ry, x + 2.6, y + ry],
                     fill=(base[0], base[1], base[2], a))
        # a few droplets branch mid-depth: short fork trail
        if hash01(j, 74) < 0.28 and 0.35 < prog < 0.75:
            bx = x + 7 * math.sin(j * 3.0)
            by = y + 12
            ba = round(a * 0.55)
            draw.line([(x, y + 2), (bx, by)], fill=(base[0], base[1], base[2], ba),
                      width=2)
            draw.ellipse([bx - 1.8, by - 2.6, bx + 1.8, by + 2.6],
                         fill=(base[0], base[1], base[2], ba))
