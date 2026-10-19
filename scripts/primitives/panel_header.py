"""panel_header: numbered panel header — "01 自然地面" + title + subtitle.

Node params:
    number    "01"
    kicker    "自然地面"  (small, muted, next to number)
    title     "草地·雨水下渗"  (large, ink)
    subtitle  "一部分进入土壤，少量沿地表流走"  (small, muted)
"""
from . import register


@register('panel_header')
def draw(draw, box, t, node, style, col, fonts):
    number = str(node.get('number', ''))
    kicker = str(node.get('kicker', ''))
    title = str(node.get('title', ''))
    subtitle = str(node.get('subtitle', ''))
    ink = col('color', '$ink')
    muted = col('muted', '$muted')
    accent = col('accent', '$red')
    x = box.x + 4
    y = box.y

    # line 1: colored dot + number + kicker
    if number or kicker:
        draw.ellipse([x, y + 4, x + 8, y + 12], fill=accent)
        line1 = f"{number}  {kicker}".strip()
        draw.text((x + 14, y), line1, fill=muted, font=fonts.get(14))
        y += 22
    # line 2: title
    if title:
        draw.text((x, y), title, fill=ink, font=fonts.get(27))
        y += 38
    # line 3: subtitle
    if subtitle:
        draw.text((x, y), subtitle, fill=muted, font=fonts.get(15))
