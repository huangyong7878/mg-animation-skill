"""layer_label: small muted label for a cross-section layer.

Node params:
    text  "松软土壤"
    align left/center/right (default left)
"""
from . import register


@register('layer_label')
def draw(draw, box, t, node, style, col, fonts):
    text = str(node.get('text', ''))
    if not text:
        return
    align = node.get('align', 'left')
    color = col('color', '#8A7F72')  # warm muted, readable on soil
    font = fonts.get(14)
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    if align == 'center':
        x = box.cx - tw / 2
    elif align == 'right':
        x = box.x + box.w - tw - 4
    else:
        x = box.x + 4
    draw.text((x, box.y), text, fill=color, font=font)
