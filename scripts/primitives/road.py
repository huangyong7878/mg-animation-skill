"""road: asphalt road cross-section with storm drain. Enhanced visuals."""
from . import register, hash01


@register('road')
def draw(draw, box, t, node, style, col, fonts):
    ah = box.h * 0.20          # asphalt
    bh = box.h * 0.26          # base course
    y_as = box.y
    y_base = box.y + ah
    y_sub = y_base + bh
    y_bot = box.y + box.h

    # --- asphalt: dark, fine aggregate texture ---
    draw.rectangle([box.x, y_as, box.x + box.w, y_base], fill='#3A3A3A')
    # worn surface highlight
    draw.line([(box.x, y_as + 1), (box.x + box.w, y_as + 1)],
              fill=(255, 255, 255, 30), width=2)
    for i in range(90):
        sx = box.x + hash01(i, 41) * box.w
        sy = y_as + hash01(i, 42) * ah
        r = 0.8 + 1.2 * hash01(i, 43)
        v = 140 + int(60 * hash01(i, 44))
        draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(v, v, v, 40))
    draw.line([(box.x, y_base), (box.x + box.w, y_base)], fill='#222222', width=2)

    # --- base: crushed stone, angular speckles ---
    draw.rectangle([box.x, y_base, box.x + box.w, y_sub], fill='#8A8A8A')
    for i in range(46):
        sx = box.x + hash01(i, 45) * box.w
        sy = y_base + hash01(i, 46) * bh
        s = 2 + 2.5 * hash01(i, 47)
        shade = 110 + int(50 * hash01(i, 48))
        draw.polygon([(sx, sy - s), (sx + s, sy), (sx, sy + s), (sx - s, sy)],
                     fill=(shade, shade, shade, 70))
    draw.line([(box.x, y_sub), (box.x + box.w, y_sub)], fill='#5A5A5A', width=2)

    # --- subgrade: earth ---
    draw.rectangle([box.x, y_sub, box.x + box.w, y_bot], fill='#6F5B40')
    for i in range(40):
        sx = box.x + hash01(i, 49) * box.w
        sy = y_sub + hash01(i, 50) * (y_bot - y_sub)
        r = 1 + 1.6 * hash01(i, 51)
        draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(0, 0, 0, 34))

    # --- storm drain: metal frame + vertical grate bars ---
    # slot_full=True extends the slot through subgrade to box bottom,
    # giving a visible channel for waterpath particles to follow down.
    if node.get('drain', True):
        dw = max(26, box.w * 0.075)
        dx0 = box.x + box.w - dw - 10
        slot_bot = y_bot if node.get('slot_full', False) else y_sub
        # dark opening from surface down
        draw.rectangle([dx0, y_as, dx0 + dw, slot_bot], fill='#161616')
        # metal frame
        draw.rectangle([dx0, y_as, dx0 + dw, slot_bot], outline='#2E2E2E', width=3)
        # vertical grate bars (only over the asphalt section)
        nb = 4
        for b in range(nb):
            bx = dx0 + (b + 0.5) / nb * dw
            draw.line([(bx, y_as + 4), (bx, y_base - 2)], fill='#9A9A9A', width=3)
            draw.line([(bx - 1, y_as + 4), (bx - 1, y_base - 2)],
                      fill=(255, 255, 255, 50), width=1)
        # water glint at the opening (animated shimmer)
        import math
        glint = 0.5 + 0.5 * math.sin(t * 3.0)
        gw = dw * 0.5 * glint
        draw.rectangle([dx0 + dw / 2 - gw / 2, y_as + 2,
                        dx0 + dw / 2 + gw / 2, y_as + 7],
                       fill=(140, 180, 220, 110))
