"""legend: bottom legend chips — colored dot + label, horizontal row.

Node params:
    items  list of [color, label], e.g.
           [["#7BA05B", "渗入地下"], ["#4A90D9", "少量径流"]]
           label may contain "→" for chained meanings:
           [["#4A90D9", "地表径流 → 雨水口 → 地下管道"]]
    chip   bool, draw rounded chip background (default True)
"""
from . import register


@register('legend')
def draw(draw, box, t, node, style, col, fonts):
    items = node.get('items') or []
    if not items:
        return
    chip = node.get('chip', True)
    ink = col('color', '$ink')
    font = fonts.get(15)
    x = box.x + 6
    cy = box.cy
    for color, label in items:
        dot_c = col('_tmp', color) if str(color).startswith('#') else col('color', color)
        # resolve color: hex directly or theme key
        if str(color).startswith('#'):
            h = str(color).lstrip('#')
            dot_c = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
        else:
            dot_c = col('color', color)
        # measure text
        bb = draw.textbbox((0, 0), str(label), font=font)
        tw = bb[2] - bb[0]
        chip_w = 14 + 12 + tw + 14  # pad + dot + gap + text + pad
        chip_h = 30
        if chip:
            draw.rounded_rectangle([x, cy - chip_h / 2, x + chip_w, cy + chip_h / 2],
                                   radius=15, fill=(255, 255, 255, 150))
        draw.ellipse([x + 14, cy - 5, x + 24, cy + 5], fill=dot_c)
        draw.text((x + 30, cy - 10), str(label), fill=ink, font=font)
        x += chip_w + 12
