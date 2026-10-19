"""counter: number that counts from A to B over [t0, t1].

Node params:
    from, to  numbers (default 0 -> 100)
    t0, t1    scene-local animation window
    prefix, suffix  strings, e.g. suffix="桶"
    size      font size (default 40)
    decimals  int (default 0)
"""
from . import register


@register('counter')
def draw(draw, box, t, node, style, col, fonts):
    a = float(node.get('from', 0))
    b = float(node.get('to', 100))
    t0 = float(node.get('t0', 0))
    t1 = float(node.get('t1', 1))
    if t <= t0:
        v = a
    elif t >= t1:
        v = b
    else:
        f = (t - t0) / (t1 - t0)
        f = f * f * (3 - 2 * f)
        v = a + (b - a) * f
    dec = int(node.get('decimals', 0))
    num = f"{v:.{dec}f}"
    text = f"{node.get('prefix', '')}{num}{node.get('suffix', '')}"
    color = col('color', '$ink')
    font = fonts.get(int(node.get('size', 40)))
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((box.cx - tw / 2, box.cy - th / 2), text, fill=color, font=font)
