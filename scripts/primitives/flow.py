"""flow: water flowing horizontally with continuous dashes. Deterministic in t."""
from . import register, hash01


@register('flow')
def draw(draw, box, t, node, style, col, fonts):
    dashes = int(node.get('dashes', 16))
    speed = float(node.get('speed', 170))
    direction = int(node.get('direction', 1))
    color = col('color', '#4A90D9')
    thick = int(node.get('thickness', 3))
    y = box.cy
    for k in range(dashes):
        x = box.x + ((hash01(k, 11) * box.w + direction * speed * t) % box.w)
        ln = 16 + 10 * hash01(k, 12)
        if direction > 0:
            draw.line([(x, y), (x + ln, y)], fill=color, width=thick)
        else:
            draw.line([(x - ln, y), (x, y)], fill=color, width=thick)
