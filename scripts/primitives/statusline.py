"""statusline: narrative status text that changes per beat.

Node params:
    states  list of [t_end, text], e.g.
            [[14.26, "雨水进入土壤"], [999, "雨水汇向排水口"]]
            shows the first state whose t_end is still in the future.
    align   left/center/right (default right)
"""
from . import register


@register('statusline')
def draw(draw, box, t, node, style, col, fonts):
    states = node.get('states') or []
    text = ''
    for t_end, s in states:
        if t < float(t_end):
            text = str(s)
            break
    if not text:
        return
    align = node.get('align', 'right')
    color = col('color', '$ink')
    font = fonts.get(15)
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    if align == 'center':
        x = box.cx - tw / 2
    elif align == 'right':
        x = box.x + box.w - tw - 4
    else:
        x = box.x + 4
    draw.text((x, box.y), text, fill=color, font=font)
