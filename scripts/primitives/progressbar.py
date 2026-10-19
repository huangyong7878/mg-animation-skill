"""progressbar: bottom progress bar for a shot.

Node params:
    t0  scene-local time when the bar starts filling
    t1  scene-local time when the bar is full
"""
from . import register


@register('progressbar')
def draw(draw, box, t, node, style, col, fonts):
    t0 = float(node.get('t0', 0))
    t1 = float(node.get('t1', 1))
    prog = 0.0 if t1 <= t0 else max(0.0, min(1.0, (t - t0) / (t1 - t0)))
    track = col('track', '#D8CFC2')
    fill = col('color', '#4A90D9')
    h = min(6, box.h)
    y = box.cy - h / 2
    draw.rounded_rectangle([box.x, y, box.x + box.w, y + h],
                           radius=h / 2, fill=track)
    if prog > 0.005:
        draw.rounded_rectangle([box.x, y, box.x + box.w * prog, y + h],
                               radius=h / 2, fill=fill)
