"""Extensible primitive registry for the MG animation engine.

A primitive is a drawable node type beyond the built-in ones
(text/card/icon/line/arrow/table/timeline/image).

To add a new primitive:
  1. Create ``scripts/primitives/<name>.py``
  2. Implement ``draw(draw, box, t, node, style, col)`` and decorate with ``@register('<name>')``
  3. Import the module at the bottom of this file

``draw`` signature:
    draw   - PIL ImageDraw (RGBA mode)
    box    - Box, already transformed by timeline animations
    t      - scene-local time in seconds (float)
    node   - the full node dict (read params like node.get('drops', 40))
    style  - effective style dict after timeline overrides
    col    - color resolver: col(name, default) -> (r,g,b,a) tuple
    fonts  - FontCache, fonts.get(size) -> PIL font (CJK-capable)

Primitives must be deterministic functions of t (same t -> same pixels).
"""

PRIMITIVES = {}


def register(name):
    """Decorator: register a primitive draw function under ``name``."""
    def deco(fn):
        if name in PRIMITIVES:
            raise ValueError(f"primitive {name!r} already registered")
        PRIMITIVES[name] = fn
        return fn
    return deco


def hash01(i: int, salt: int = 0) -> float:
    """Deterministic pseudo-random in [0,1). Pure function of (i, salt)."""
    x = (int(i) * 2654435761 + int(salt) * 40503) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 2246822519) & 0xFFFFFFFF
    x ^= x >> 13
    return x / 2**32


def seg_lengths(pts):
    """Arc lengths of polyline segments. pts: list of (x, y)."""
    import math
    return [math.hypot(x1 - x0, y1 - y0)
            for (x0, y0), (x1, y1) in zip(pts, pts[1:])]


def point_at(pts, ls, total, d):
    """Point at arc-length d along polyline. Deterministic."""
    d = d % total
    acc = 0.0
    for (x0, y0), (x1, y1), L in zip(pts, pts[1:], ls):
        if d <= acc + L or L == 0:
            f = 0 if L == 0 else (d - acc) / L
            return (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f,
                    (x1 - x0) / L if L else 1.0, (y1 - y0) / L if L else 0.0)
        acc += L
    x0, y0 = pts[-2]; x1, y1 = pts[-1]
    L = ls[-1] if ls else 1
    return (x1, y1, (x1 - x0) / L if L else 1.0, (y1 - y0) / L if L else 0.0)


# Import all built-in primitives so they self-register.
from . import rain, soil, soak, road, flow, drainpipe, waterpath, \
    panel_header, legend, layer_label, statusline, progressbar, \
    waterfilm, waterlevel, counter, bucket  # noqa: E402,F401
