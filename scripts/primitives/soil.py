"""soil: grass + soil cross-section. Enhanced visuals, retro infographic style."""
from . import register, hash01


def _lerp(c1, c2, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))


def _hex(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@register('soil')
def draw(draw, box, t, node, style, col, fonts):
    gh = box.h * 0.14           # grass strip
    th = box.h * 0.32           # topsoil band
    y_grass = box.y
    y_top = box.y + gh
    y_sub = y_top + th
    y_bot = box.y + box.h

    # --- grass: two blade layers for depth ---
    draw.rectangle([box.x, y_grass, box.x + box.w, y_top], fill='#7BA05B')
    bw = max(5, box.w / 70)
    n = int(box.w / bw)
    for i in range(n):  # back row, darker
        bx = box.x + (i + 0.5) * bw
        bh = 7 + 9 * hash01(i, 21)
        draw.polygon([(bx - 2.2, y_top), (bx + 2.2, y_top),
                      (bx + 1, y_top - bh)], fill='#5F8547')
    for i in range(n):  # front row, lighter
        bx = box.x + (i + 0.25) * bw + 2
        bh = 4 + 6 * hash01(i, 22)
        draw.polygon([(bx - 2, y_top), (bx + 2, y_top),
                      (bx - 1, y_top - bh)], fill='#8FAE6B')
    # soil line under grass
    draw.line([(box.x, y_top), (box.x + box.w, y_top)], fill='#4E6B3A', width=2)

    # --- topsoil with gradient transition ---
    c_top = _hex('#8B6F4E'); c_sub = _hex('#6F5B40')
    draw.rectangle([box.x, y_top, box.x + box.w, y_sub], fill='#8B6F4E')
    # 6px gradient band into subsoil
    for g in range(6):
        cc = _lerp(c_top, c_sub, (g + 1) / 7)
        draw.line([(box.x, y_sub - 6 + g), (box.x + box.w, y_sub - 6 + g)],
                  fill='#%02x%02x%02x' % cc)
    draw.rectangle([box.x, y_sub, box.x + box.w, y_bot], fill='#6F5B40')
    # subtle strata lines
    for sy, salt in ((y_top + th * 0.5, 51), (y_sub + (y_bot - y_sub) * 0.4, 52)):
        for i in range(8):
            sx = box.x + hash01(i, salt) * box.w * 0.8
            ln = 20 + 40 * hash01(i, salt + 1)
            draw.line([(sx, sy), (sx + ln, sy)], fill=(0, 0, 0, 22), width=1)
    # speckles: organic matter (top) / mineral (sub)
    for band_y, band_h, cnt, salt, alpha in (
            (y_top, th, 52, 31, 42), (y_sub, y_bot - y_sub, 64, 32, 34)):
        for i in range(cnt):
            sx = box.x + hash01(i, salt) * box.w
            sy = band_y + hash01(i, salt + 1) * band_h
            r = 1.1 + 1.7 * hash01(i, salt + 2)
            draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(0, 0, 0, alpha))
    # a few tiny roots in topsoil
    for i in range(7):
        rx = box.x + hash01(i, 61) * box.w
        ry = y_top + 4 + hash01(i, 62) * th * 0.5
        rl = 8 + 10 * hash01(i, 63)
        draw.line([(rx, ry), (rx + 3, ry + rl)], fill=(62, 52, 36, 90), width=1)
