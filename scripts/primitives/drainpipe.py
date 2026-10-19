"""drainpipe: vertical drainage pipe, optional L-shaped elbow.

Place below a road drain slot (x-aligned) to show water entering the
underground pipe network.

Node params:
    elbow      None (straight, default), "left" or "right"
    elbow_len  horizontal run length in px (default 90)
    water      bool, internal water dashes (default True).
               Set False when a waterpath drives the flow instead.
    dashes     water dash count (default 9)
    speed      water speed px/s (default 150)
"""
from . import register, hash01, seg_lengths, point_at


@register('drainpipe')
def draw(draw, box, t, node, style, col, fonts):
    pw = box.w
    px0 = box.x
    cx = px0 + pw / 2
    elbow = node.get('elbow')          # None | "left" | "right"
    elbow_len = float(node.get('elbow_len', 90))
    edir = -1 if elbow == 'left' else 1

    # --- pipe body: dark cylinder with edge highlights ---
    draw.rectangle([px0, box.y, px0 + pw, box.y + box.h], fill='#242424')
    draw.line([(px0 + 2, box.y), (px0 + 2, box.y + box.h)],
              fill=(255, 255, 255, 36), width=2)
    draw.line([(px0 + pw - 3, box.y), (px0 + pw - 3, box.y + box.h)],
              fill=(0, 0, 0, 80), width=2)
    # coupling rings
    for r in range(1, 3):
        ry = box.y + box.h * r / 3
        draw.line([(px0, ry), (px0 + pw, ry)], fill='#3A3A3A', width=3)
        draw.line([(px0, ry - 2), (px0 + pw, ry - 2)],
                  fill=(255, 255, 255, 24), width=1)

    # --- elbow: horizontal run with rounded corner joint ---
    ex0 = ex1 = None
    if elbow:
        ey = box.y + box.h - pw / 2   # elbow centerline
        ex0 = cx
        ex1 = cx + edir * elbow_len
        x_lo, x_hi = (ex1, ex0) if edir < 0 else (ex0, ex1)
        draw.rectangle([x_lo - pw / 2, ey - pw / 2, x_hi + pw / 2, ey + pw / 2],
                       fill='#242424')
        # corner joint: circle to smooth the turn
        draw.ellipse([cx - pw / 2, ey - pw / 2, cx + pw / 2, ey + pw / 2],
                     fill='#242424')
        draw.ellipse([cx - pw / 2, ey - pw / 2, cx + pw / 2, ey + pw / 2],
                     outline=(255, 255, 255, 30), width=2)
        # highlight along horizontal run
        draw.line([(x_lo, ey - pw / 2 + 2), (x_hi, ey - pw / 2 + 2)],
                  fill=(255, 255, 255, 30), width=2)

    # --- water: path-following dashes (vertical, then elbow if present) ---
    if not node.get('water', True):
        return
    import math
    water = col('color', '#4A90D9')
    dashes = int(node.get('dashes', 9))
    speed = float(node.get('speed', 150))
    pts = [(cx, box.y - 8), (cx, box.y + box.h)]
    if elbow:
        ey = box.y + box.h - pw / 2
        pts.append((cx + edir * elbow_len, ey))
    ls = seg_lengths(pts)
    total = sum(ls)
    if total < 1:
        return
    for k in range(dashes):
        d = (hash01(k, 81) * total + speed * t) % total
        x, y, dx, dy = point_at(pts, ls, total, d)
        prog = d / total
        env = 1.0 if prog > 0.05 else prog / 0.05
        a = round(water[3] * env)
        if a < 5:
            continue
        ln = 10 + 8 * hash01(k, 82)
        # dash elongated along travel direction
        x2 = x + dx * ln
        y2 = y + dy * ln
        draw.line([(x, y), (x2, y2)], fill=(water[0], water[1], water[2], a),
                  width=4)
