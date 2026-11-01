# MG Animation Scene v2.1 — Compact Contract

This is a distilled, human-readable copy of the real contract used by the
legacy MG Animation Skill. It is sufficient for authoring Scene JSON without
the renderer installed. The machine schema is `references/scene.schema.json`
in the legacy repository; the semantic checks below come from
`scripts/validate.py` and `scripts/factcheck.py`.

> Text-only use: you can write a schema-faithful document without running
> anything. It is **not** renderer-validated until `scripts/validate.py` has
> actually run and exited 0.

## 1. Top-level object

Only these root keys are allowed (`additionalProperties: false`):

```json
{
  "version": "2.1",
  "canvas": {
    "width": 960,
    "height": 540,
    "fps": 24,
    "duration": 24.0,
    "grain_seed": 41,
    "default_transition": {"type": "crossfade", "duration": 0.6}
  },
  "theme": {
    "paper": "#EAE2D6",
    "ink": "#2F3B40",
    "red": "#B44B43",
    "cream": "#F7F1E7",
    "muted": "#766C63"
  },
  "scenes": [],
  "narration": {"segments": []},
  "claims": []
}
```

| Root key | Required | Rules |
|---|---|---|
| `version` | Yes | `"2.0"` or `"2.1"`. Use `"2.1"` for new documents. |
| `canvas` | Yes | Object; `width` 160–4096, `height` 120–4096, `duration` > 0 and ≤ 600. `fps` 1–60. |
| `theme` | No | Object whose values are color strings. `$name` in a style resolves through the theme. |
| `scenes` | Yes | Non-empty array of scene objects. |
| `narration` | No | `{"segments": [...]}`. |
| `claims` | No | Array of claim objects. |

`canvas.default_transition` and each `scenes[n].transition_in` accept only:

```json
{"type": "crossfade", "duration": 0.6}
```

`type` ∈ `crossfade` | `wipe_left` | `slide_left` | `cut`; `duration` ≥ 0.
A transition object may not contain other keys.

## 2. Scene object

```json
{
  "id": "shot_01",
  "start": 0,
  "duration": 8.0,
  "transition_in": {"type": "wipe_left", "duration": 0.8},
  "factual": false,
  "claim_ids": [],
  "elements": []
}
```

| Key | Required | Rules |
|---|---|---|
| `id` | No | String. Keep IDs unique when practical. |
| `start` | No | Number ≥ 0; defaults to 0. |
| `duration` | Yes | Number > 0. |
| `elements` | Yes | Array of node objects. |
| `transition_in` | No | Transition object. |
| `factual` | No | Boolean. |
| `claim_ids` | No | Array of claim ID strings. |

**Hard timing rule:** `start + duration` must not exceed
`canvas.duration` (validator tolerance 0.001 s). Animations and narration
offsets are relative to the start of their scene.

## 3. Node object

Every node requires `type`. These fields may be used:

`id`, `type`, `rect`, `text`, `symbol`, `style`, `animations`, `children`,
`columns`, `rows`, `items`, `weights`, `column_weights`, `row_weights`,
`padding`, `gap`, `header_ratio`, `grid_start`, `grid_duration`,
`cells_start`, `cell_duration`, `stagger`, `order`, `line_start`,
`line_duration`, `items_start`, `asset`.

### 3.1 Containers

- `absolute` — children positioned by their own `rect` inside the container.
- `row` — children laid out left to right; `gap` in pixels; optional
  `weights` (one positive number per child).
- `column` — children laid out top to bottom; same `gap`/`weights` rules.
- `grid` — requires an **integer** `columns`; rows are computed. Optional
  `column_weights`, `row_weights`, `gap`, `padding`.

Children of `row`/`column`/`grid` get their size from the layout engine;
their own `rect` does not re-layout them. Use `absolute` when exact positions
are needed.

### 3.2 Drawable nodes

| Type | Required content | Notes |
|---|---|---|
| `text` | `text` | `style.size`, `min_size`, `max_lines`, `color`, `align`. |
| `card` | `text` (optional) | `style.fill`, `stroke`, `stroke_width`, `radius`, `size`, `max_lines`. |
| `icon` | `symbol` | `circle`, `diamond`, `triangle`, `square`, `bars`, `star`. |
| `image` | `asset` | Local relative file next to the JSON; never a URL. Not usable in the text-only path unless the user supplies the asset. |
| `line` | — | `rect.x/y` is the start point; `rect.x+w/y+h` is the end point. |
| `arrow` | — | Horizontal arrow in the current box; useful inside a `row`. |
| `table` | `columns`, `rows` | See §4. |
| `timeline` | `items` (non-empty) | See §5. |

The legacy engine additionally exposes low-level primitives (`flow`,
`progressbar`, `counter`, `legend`, `statusline` and others). They depend on
the exact installed engine version. Do **not** use them in generic Agensi
output; stick to the eight documented types above.

### 3.3 Geometry

`rect` is `{x, y, w, h}`. Each value is either:

- a number in canvas pixels (relative to the parent), or
- a percentage string matching `^-?[0-9]+(?:\.[0-9]+)?%$`, e.g. `"15%"`.

Example: `{"x": "10%", "y": "7%", "w": "80%", "h": "15%"}`.

### 3.4 Animation

```json
{"type": "fade", "start": 0.2, "duration": 0.5, "easing": "out_cubic"}
```

`type` ∈ `fade` | `slide` | `pop` | `draw` | `move`; `start` ≥ 0;
`duration` > 0; `easing` ∈ `linear` | `out_cubic` | `in_out` | `out_back`.
Optional `from_scale` (> 0), `from_x`, `from_y`, `to_x`, `to_y`.

Animations on the same node combine. Times are scene-relative. Do not use an
animation type outside the five listed: the validator rejects it.

## 4. Table

```json
{
  "type": "table",
  "rect": {"x": "8%", "y": "24%", "w": "84%", "h": "58%"},
  "columns": ["Stage", "What happens"],
  "rows": [
    ["Committee", "Hearings, amendments and a markup vote."],
    ["Floor", "Debate and a majority vote."]
  ],
  "column_weights": [1, 2.6],
  "header_ratio": 0.7,
  "grid_start": 0.3,
  "grid_duration": 0.5,
  "cells_start": 0.9,
  "stagger": 0.22,
  "cell_duration": 0.35,
  "order": "row",
  "style": {"stroke": "$red", "stroke_width": 2, "font_size": 22}
}
```

- `columns` is an array; its length is the column count `c`. Use the array
  form for tables. The generic schema also permits an integer `columns` for
  some node types, but the current table path calls `len()` on it and raises a
  `TypeError` in `scripts/validate.py`. Do not write `"columns": 2` on a table.
- Every row in `rows` must have **exactly `c` cells**. The validator rejects
  mismatches.
- There is no fixed 2×3 limit; any practical row/column count works.
- A cell is a string, a number, or an object:
  `{"type":"text","text":"..."}`,
  `{"type":"badge","text":"...","style":{...}}`,
  `{"type":"icon","symbol":"star","style":{...}}`,
  `{"type":"image","asset":"local.png"}`.
- `column_weights` must have length `c`. `order` is `row` (default) or
  `column`.

## 5. Timeline

```json
{
  "type": "timeline",
  "rect": {"x": "7%", "y": "28%", "w": "86%", "h": "34%"},
  "items": [
    {"label": "Step 1", "detail": "Start"},
    {"label": "Step 2", "detail": "Change"},
    {"label": "Step 3", "detail": "Result"}
  ],
  "line_start": 0.3,
  "line_duration": 0.7,
  "items_start": 0.8,
  "stagger": 0.28
}
```

`items` must be non-empty. Items are evenly spaced. `label` and `detail` are
rendered as two levels of text.

## 6. Narration

```json
{
  "narration": {
    "segments": [
      {"id": "n1", "scene_index": 0, "offset": 0.5, "text": "First line."},
      {"id": "n2", "scene_index": 1, "offset": 0.5, "text": "Second line.", "pause_after": 0.3}
    ]
  }
}
```

Each segment requires non-empty `text`. Timing may be:

- `scene_index` (≥ 0) plus optional `offset` (≥ 0), or
- absolute `start` (≥ 0).

`pause_after` (≥ 0) adds silence after the segment.

The legacy narration tool synthesizes each segment, measures the **real audio
duration**, inserts silence for gaps, and writes timings/SRT. Speech segments
must not overlap, and total narration must not exceed `canvas.duration`; the
tool raises an error instead of trimming. In the text-only path, treat these
durations as estimates, not measured values.

## 7. Claims and evidence

```json
{
  "claims": [
    {
      "id": "claim_001",
      "statement": "A precisely worded factual statement.",
      "status": "unverified",
      "evidence": []
    }
  ]
}
```

`status` ∈ `verified` | `unverified` | `disputed`. Evidence entries require
`url` and `quote`.

For `version: "2.1"`, the validator runs the fail-closed claim gate:

- every claim must have status `verified`;
- every claim needs at least one `http(s)` evidence URL and a verbatim quote
  of at least 8 characters;
- every scene with `factual: true` must list at least one `claim_id`;
- every `claim_id` listed by a `factual: true` scene must exist.

The default `scripts/validate.py` gate is **metadata only**. It checks status,
URL shape and quote length; it does not fetch the URL or confirm that the quote
appears there. `scripts/factcheck.py --fetch-sources` adds a live
quote-presence check. Neither mode proves that a claim is true.

Consequences:

- Do **not** set `verified` unless a real source was checked and a human or
  research agent confirmed the meaning. A matching quote does not prove truth.
- If evidence is missing, keep `unverified` and warn that the document will
  fail validation. That is the intended fail-closed behavior, not a bug.
- A `2.0` document skips this gate for backward compatibility. Do not use
  `2.0` to hide unverified claims from a user who asked for `2.1`.

## 8. Semantic checks performed by `scripts/validate.py`

Beyond JSON Schema, the validator also rejects:

- duplicate node IDs;
- unknown node types;
- `grid` without an integer `columns`;
- a table with zero columns, a row with the wrong cell count, or
  `column_weights` with the wrong length;
- an `image` node without `asset`;
- a `timeline` without `items`;
- unsupported animation types or non-positive animation durations;
- a scene that exceeds `canvas.duration`;
- layout errors such as non-positive sizes or unsupported percentages.

## 9. Transitions and shot boundaries

- Adjacent scenes share the boundary; the transition is centered on it.
- Explicitly overlapping scenes use the overlap interval for the transition.
- Gaps between scenes show the paper background; do not assume a transition
  is created across a gap.
- Avoid three overlapping scenes at one boundary; the renderer supports
  pairwise junctions, not complex multi-layer compositing.

## 10. Text-only output status

When no validator was run, include this sentence in the QA notes:

> Schema-drafted against the MG Animation v2.1 contract; not validated by the
> legacy renderer.

When the validator was run, record the exact command and exit code instead.
