"""orderflow: two orders, two paths — warehouse fulfillment flow.

Implements director spec orders_shot_001 (Pilot 001):
  Order A (green): placed -> stock_check -> pick -> pack -> ship
  Order B (orange): placed -> stock_check -> restock_queue

Both cards keep identity (color + letter) for the whole shot.
All motion is continuous (piecewise eased interpolation between
waypoints); nothing teleports. Deterministic function of t.

Style: vintage paper, muted infographic, restrained motion.
"""
import math

from . import register

# Timeline markers shared with the Stage C narration validation.
# These are real order-card motion waypoint times, not arbitrary TTS estimates.
PILOT_EVENT_SECONDS = {
    "order_a_appears": 1.0,
    "order_b_appears": 1.2,
    "branch_split": 5.8,
    "order_b_queue_arrival": 8.4,
    "order_a_ship_arrival": 10.0,
}


# ---- palette (muted, low saturation) ----
_PAPER = (231, 222, 212, 255)
_INK = (53, 60, 62, 255)
_MUTED = (79, 76, 71, 255)
_GREEN = (110, 143, 105, 255)      # order A
_GREEN_DK = (84, 115, 80, 255)
_ORANGE = (192, 138, 77, 255)      # order B
_ORANGE_DK = (160, 112, 58, 255)
_LINE = (125, 117, 108, 255)
_WHITE = (255, 255, 255, 255)


def _smooth(u):
    """smoothstep easing 0->1"""
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def _lerp(a, b, u):
    return a + (b - a) * u


def _travel(keys, t):
    """keys: list of (time, x, y). Returns eased (x, y) at time t."""
    if t <= keys[0][0]:
        return keys[0][1], keys[0][2]
    for i in range(len(keys) - 1):
        t0, x0, y0 = keys[i]
        t1, x1, y1 = keys[i + 1]
        if t0 <= t <= t1:
            u = _smooth((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            return _lerp(x0, x1, u), _lerp(y0, y1, u)
    return keys[-1][1], keys[-1][2]


def _fade(t, t0, t1):
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return (t - t0) / (t1 - t0)


def _rr(draw, xy, r, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def _diamond(draw, cx, cy, s, fill, outline):
    draw.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)],
                 fill=fill, outline=outline)


@register('orderflow')
def draw(draw, box, t, node, style, col, fonts):
    W, H = box.w, box.h
    sx = W / 960.0
    sy = H / 540.0

    def X(v):
        return box.x + v * sx

    def Y(v):
        return box.y + v * sy

    def S(v):
        return v * (sx + sy) / 2

    # ---- background ----
    draw.rectangle([box.x, box.y, box.x + W, box.y + H], fill=_PAPER)

    scene_a = _fade(t, 0.0, 1.0)  # whole-scene fade in

    def alpha(base, a):
        return (base[0], base[1], base[2], round(base[3] * a))

    # ---- title ----
    if scene_a > 0:
        draw.text((X(480), Y(40)), "两张订单，两条路径",
                  fill=alpha(_INK, scene_a), font=fonts.get(int(S(34))),
                  anchor="mm")
        draw.text((X(480), Y(74)), "同样下单，库存充足和库存不足会走向不同处理路径。",
                  fill=alpha(_MUTED, scene_a), font=fonts.get(int(S(17))),
                  anchor="mm")

    # ---- stations (static layout) ----
    # waypoints
    placed_ax, placed_ay = 100, 200
    placed_bx, placed_by = 100, 360
    check_cx, check_cy = 340, 280
    pick_x, pick_y = 520, 175
    pack_x, pack_y = 670, 175
    ship_x, ship_y = 820, 175
    queue_x, queue_y = 640, 400  # restock queue center

    # faint path lines
    if scene_a > 0:
        lc = alpha(_LINE, scene_a)
        # A path
        for (x0, y0, x1, y1) in [
            (placed_ax, placed_ay, check_cx, check_cy),
            (check_cx, check_cy, pick_x, pick_y),
            (pick_x, pick_y, pack_x, pack_y),
            (pack_x, pack_y, ship_x, ship_y),
        ]:
            draw.line([X(x0), Y(y0), X(x1), Y(y1)], fill=lc, width=max(1, int(S(2))))
        # B path
        for (x0, y0, x1, y1) in [
            (placed_bx, placed_by, check_cx, check_cy),
            (check_cx, check_cy, queue_x, queue_y),
        ]:
            draw.line([X(x0), Y(y0), X(x1), Y(y1)], fill=lc, width=max(1, int(S(2))))

    # station labels (QA-P2-002: larger for readability)
    def label(x, y, text, color=_MUTED, size=18):
        if scene_a <= 0:
            return
        draw.text((X(x), Y(y)), text, fill=alpha(color, scene_a),
                  font=fonts.get(int(S(size))), anchor="mm")

    label(placed_ax, 268, "下单")
    label(placed_bx, 428, "下单")
    label(pick_x, pick_y - 52, "拣货")
    label(pack_x, pack_y - 52, "打包")
    label(ship_x, ship_y - 52, "发货")

    # Keep the stock decision legible AND keep A/B identity clear: card
    # trajectories pass well outside the diamond instead of under its fill.
    def draw_stock_diamond():
        if scene_a <= 0:
            return
        ds = S(46)
        if 4.8 <= t <= 6.2:
            pulse = 1.0 + 0.06 * _smooth((t - 4.8) / 1.0) * (1 - _smooth((t - 5.8) / 0.4))
        else:
            pulse = 1.0
        _diamond(draw, X(check_cx), Y(check_cy), ds * pulse,
                 fill=alpha(_PAPER, scene_a), outline=alpha(_INK, scene_a))
        draw.text((X(check_cx), Y(check_cy) - S(8)), "库存",
                  fill=alpha(_INK, scene_a), font=fonts.get(int(S(18))), anchor="mm")
        draw.text((X(check_cx), Y(check_cy) + S(12)), "检查",
                  fill=alpha(_INK, scene_a), font=fonts.get(int(S(18))), anchor="mm")

    # restock queue zone (dashed box)
    if scene_a > 0:
        qx0, qy0, qx1, qy1 = X(520), Y(340), X(780), Y(470)
        # dashed rect
        dash = int(S(8))
        x = qx0
        while x < qx1:
            draw.line([x, qy0, min(x + dash, qx1), qy0], fill=alpha(_ORANGE_DK, 0.7 * scene_a), width=max(1, int(S(2))))
            draw.line([x, qy1, min(x + dash, qx1), qy1], fill=alpha(_ORANGE_DK, 0.7 * scene_a), width=max(1, int(S(2))))
            x += dash * 2
        y = qy0
        while y < qy1:
            draw.line([qx0, y, qx0, min(y + dash, qy1)], fill=alpha(_ORANGE_DK, 0.7 * scene_a), width=max(1, int(S(2))))
            draw.line([qx1, y, qx1, min(y + dash, qy1)], fill=alpha(_ORANGE_DK, 0.7 * scene_a), width=max(1, int(S(2))))
            y += dash * 2
        draw.text((X(650), Y(356)), "待补货队列",
                  fill=alpha(_ORANGE_DK, scene_a), font=fonts.get(int(S(17))), anchor="mm")

    # ---- branch labels at decision moment ----
    dec_a = _fade(t, 4.9, 5.6)
    if dec_a > 0:
        draw.text((X(440), Y(196)), "有货 ✓",
                  fill=alpha(_GREEN_DK, dec_a), font=fonts.get(int(S(17))), anchor="mm")
        draw.text((X(452), Y(352)), "缺货",
                  fill=alpha(_ORANGE_DK, dec_a), font=fonts.get(int(S(17))), anchor="mm")

    # ---- order cards ----
    def card(cx, cy, letter, color, dark, appear_t, scale_extra=1.0):
        """Draw an order card centered at (cx, cy) in design coords."""
        pop = _fade(t, appear_t, appear_t + 0.6)
        if pop <= 0:
            return
        sc = (0.6 + 0.4 * _smooth(pop)) * scale_extra
        w, h = S(96) * sc, S(64) * sc
        x0, y0 = X(cx) - w / 2, Y(cy) - h / 2
        # shadow
        _rr(draw, [x0 + S(3), y0 + S(3), x0 + w + S(3), y0 + h + S(3)],
            int(S(10)), fill=(0, 0, 0, round(40 * pop)))
        _rr(draw, [x0, y0, x0 + w, y0 + h], int(S(10)),
            fill=alpha(color, pop), outline=alpha(dark, pop), width=max(1, int(S(2))))
        if pop > 0:
            a = pop
            draw.text((X(cx), Y(cy) - S(8)), letter,
                      fill=alpha(_WHITE, a), font=fonts.get(max(16, int(S(26) * sc))), anchor="mm")
            draw.text((X(cx), Y(cy) + S(16)), "订单",
                      fill=alpha(_WHITE, a), font=fonts.get(int(S(13) * sc)), anchor="mm")

    # A keyframes: placed -> check -> pick -> pack -> ship
    # (100px separation above/below decision to avoid overlapping diamond)
    a_keys = [
        (1.8, placed_ax, placed_ay),
        (4.8, check_cx, check_cy - 100),
        (PILOT_EVENT_SECONDS["branch_split"], check_cx, check_cy - 100),
        (7.2, pick_x, pick_y),
        (8.6, pack_x, pack_y),
        (PILOT_EVENT_SECONDS["order_a_ship_arrival"], ship_x, ship_y),
        (13.0, ship_x, ship_y),
    ]
    # B keyframes: placed -> check -> restock queue
    b_keys = [
        (1.8, placed_bx, placed_by),
        (4.8, check_cx, check_cy + 100),
        (PILOT_EVENT_SECONDS["branch_split"], check_cx, check_cy + 100),
        (PILOT_EVENT_SECONDS["order_b_queue_arrival"], queue_x, queue_y),
        (13.0, queue_x, queue_y),
    ]
    ax, ay = _travel(a_keys, t)
    bx, by = _travel(b_keys, t)

    # draw B first (under), then A
    card(bx, by, "B", _ORANGE, _ORANGE_DK, PILOT_EVENT_SECONDS["order_b_appears"])
    card(ax, ay, "A", _GREEN, _GREEN_DK, PILOT_EVENT_SECONDS["order_a_appears"])

    # Diamond stays unobstructed because order cards stop outside its silhouette.
    draw_stock_diamond()

    # ---- end-state badges ----
    ship_a = _fade(t, 10.4, 11.2)
    if ship_a > 0:
        bx0, by0 = X(ship_x) - S(52), Y(ship_y) + S(44)
        _rr(draw, [bx0, by0, bx0 + S(104), by0 + S(30)], int(S(15)),
            fill=alpha(_GREEN_DK, ship_a))
        draw.text((bx0 + S(52), by0 + S(15)), "✓ 已发货",
                  fill=alpha(_WHITE, ship_a), font=fonts.get(int(S(14))), anchor="mm")

    wait_a = _fade(t, 8.6, 9.1)
    if wait_a > 0:
        # gentle pulse on the waiting badge
        pulse_a = 1.0  # steady opaque fill improves small-screen legibility
        wx0, wy0 = X(queue_x) - S(52), Y(queue_y) + S(44)
        _rr(draw, [wx0, wy0, wx0 + S(104), wy0 + S(30)], int(S(15)),
            fill=(alpha(_ORANGE_DK, wait_a * pulse_a)))
        draw.text((wx0 + S(52), wy0 + S(15)), "…等待补货",
                  fill=alpha(_WHITE, wait_a), font=fonts.get(int(S(16))), anchor="mm")
