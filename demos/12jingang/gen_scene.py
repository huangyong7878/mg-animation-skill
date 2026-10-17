"""Generate 12-Jinguang scene JSON: row counting -> reverse -> circle morph -> title rise."""
import json, math

W, H = 960, 540
N = 12

# Row geometry
row_cx = [80 + i * (800 / 11) for i in range(N)]
row_x = [c - 32 for c in row_cx]
row_y = 190
FW, FH = 64, 90

# Circle geometry
CCX, CCY, R = 480, 310, 165
circ = []
for i in range(N):
    ang = math.radians(-90 + i * 30)
    cx = CCX + R * math.cos(ang)
    cy = CCY + R * math.sin(ang)
    circ.append((cx - 32, cy - 45))

def anim(t, start, duration, **kw):
    a = {"type": t, "start": start, "duration": duration}
    a.update(kw)
    return a

# ---------- Scene 1: row + counting ----------
s1_elements = []

# 12 warrior figures, pop in staggered
for i in range(N):
    s1_elements.append({
        "id": f"fig{i}",
        "type": "image",
        "asset": "assets/warrior.png",
        "rect": {"x": row_x[i], "y": row_y, "w": FW, "h": FH},
        "animations": [
            anim("pop", 0.3 + i * 0.1, 0.5, easing="out_back"),
            # forward count pulse (don't hide before start)
            anim("pop", 1.8 + i * 0.4, 0.4, easing="out_back", from_scale=0.8,
                 hide_before=False),
            # reverse count pulse
            anim("pop", 6.6 + (N - 1 - i) * 0.4, 0.4, easing="out_back",
                 from_scale=0.8, hide_before=False),
        ],
    })

# Counter: 23 stacked cards (1-12 forward, 11-1 reverse)
counter_seq = list(range(1, 13)) + list(range(11, 0, -1))
for idx, num in enumerate(counter_seq):
    if idx < 12:
        t = 1.8 + idx * 0.4
    else:
        t = 6.6 + (idx - 12) * 0.4
    s1_elements.append({
        "id": f"cnt{idx}",
        "type": "card",
        "text": str(num),
        "rect": {"x": 430, "y": 24, "w": 100, "h": 72},
        "style": {"fill": "$cream", "stroke": "$red", "stroke_width": 3,
                  "color": "$red", "size": 44},
        "animations": [anim("pop", t, 0.35, easing="out_back", from_scale=0.7)],
    })

scene1 = {"id": "counting", "start": 0, "duration": 11.4, "elements": s1_elements}

# ---------- Scene 2: circle morph + title ----------
s2_elements = []
for i in range(N):
    cx, cy = circ[i]
    s2_elements.append({
        "id": f"cfig{i}",
        "type": "image",
        "asset": "assets/warrior.png",
        "rect": {"x": cx, "y": cy, "w": FW, "h": FH},
        "animations": [
            anim("move", 0.0, 1.6, easing="in_out",
                 from_x=row_x[i] - cx, from_y=row_y - cy, to_x=0, to_y=0),
        ],
    })

# "12金刚" rises in center
s2_elements.append({
    "id": "title",
    "type": "text",
    "text": "12金刚",
    "rect": {"x": 280, "y": 250, "w": 400, "h": 120},
    "style": {"color": "$red", "size": 84},
    "animations": [
        anim("slide", 1.9, 0.9, easing="out_cubic", from_y=60),
        anim("fade", 1.9, 0.9, easing="out_cubic"),
    ],
})

scene2 = {"id": "circle", "start": 11.4, "duration": 4.1, "elements": s2_elements}

scene = {
    "version": "2.0",
    "canvas": {"width": W, "height": H, "fps": 24, "duration": 15.5},
    "scenes": [scene1, scene2],
}

with open("/home/hatch/workspace/mg-12jingang/12jingang.json", "w", encoding="utf-8") as f:
    json.dump(scene, f, ensure_ascii=False, indent=1)
print("scene JSON written:", len(s1_elements), "+", len(s2_elements), "elements")
