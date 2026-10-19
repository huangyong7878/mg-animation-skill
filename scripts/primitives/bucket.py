"""bucket: simple bucket icon (trapezoid + handle).

Node params:
    fill   body fill color (default water blue, translucent)
"""
from . import register


@register('bucket')
def draw(draw, box, t, node, style, col, fonts):
    fill = col('fill', '#4A90D9')
    ink = col('ink', '$ink')
    x0, y0 = box.x, box.y
    w, h = box.w, box.h
    # body: trapezoid (wider at top)
    top_w, bot_w = w * 0.92, w * 0.68
    pts = [(x0 + (w - top_w) / 2, y0 + h * 0.25),
           (x0 + (w + top_w) / 2, y0 + h * 0.25),
           (x0 + (w + bot_w) / 2, y0 + h),
           (x0 + (w - bot_w) / 2, y0 + h)]
    draw.polygon(pts, fill=(fill[0], fill[1], fill[2], 110),
                 outline=(ink[0], ink[1], ink[2], 220), width=2)
    # handle: arc above
    draw.arc([x0 + w * 0.18, y0 - h * 0.05, x0 + w * 0.82, y0 + h * 0.45],
             start=180, end=360, fill=(ink[0], ink[1], ink[2], 220), width=2)
    # water line inside
    draw.line([(x0 + (w - top_w) / 2 + 3, y0 + h * 0.45),
               (x0 + (w + top_w) / 2 - 3, y0 + h * 0.45)],
              fill=(fill[0], fill[1], fill[2], 200), width=2)
