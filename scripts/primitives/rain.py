"""rain: continuous rainfall particles. Deterministic function of t."""
from . import register, hash01


@register('rain')
def draw(draw, box, t, node, style, col, fonts):
    drops = int(node.get('drops', 40))
    speed = float(node.get('speed', 320))
    color = col('color', '#4A90D9')
    span = box.h + 24
    for i in range(drops):
        x = box.x + hash01(i, 1) * box.w
        v = speed * (0.7 + 0.6 * hash01(i, 2))
        ln = 9 + 11 * hash01(i, 3)
        y = box.y - 12 + ((hash01(i, 4) * span + v * t) % span)
        draw.line([(x, y), (x, y + ln)], fill=color, width=2)
