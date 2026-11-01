# Storyboard — How a Bill Becomes Law

## Direction

- **Audience:** High-school civics students
- **Language:** English
- **Canvas:** 960 × 540 (16:9), 24 fps
- **Total duration:** 24 s
- **Narration:** Text plan only; no audio generated
- **Tone and palette:** Neutral civics explainer; warm paper, ink text, muted
  red/blue/gold accents
- **Assumptions:** Three 8-second shots; no image assets; conservative speech
  pace for narration estimates.

## Shot table

| ID | Time (s) | Narrative goal | On-screen content | Animation / transition | Narration | Fact status |
|---|---|---|---|---|---|---|
| s1 | 0–8 | Show where a bill starts | Title + three cards: idea → draft → introduce, with arrows | fade/slide title; staggered pop cards; arrow draw; crossfade out | A bill begins as an idea. A member of Congress drafts it and introduces it in one chamber. | No factual claim beyond the general process |
| s2 | 8–16 | Explain committee and floor action | Two-column table with three rows | wipe_left in; grid and cell stagger | Committees hold hearings and vote. Then the full chamber debates and votes. | General process, no statistics |
| s3 | 16–24 | Show the final step | Three-item timeline + closing card | slide_left in; line draw and item stagger | If both chambers pass the same text, the president may sign or veto it. | General process; veto override mentioned on screen, not narrated |

## Shot details

### s1 — An idea becomes a bill

- **Visual elements:** Title at the top; a five-part flow row containing
  three cards and two arrows.
- **Animation order:** Title fades and slides in at 0.05 s; cards pop at
  0.50 s, 1.35 s and 2.20 s; arrows draw between them; footnote fades at
  3.00 s.
- **Transition out:** Default `crossfade` (0.6 s) centered on 8 s.
- **Narration window:** 0.5–7.5 s, estimated 5.5–6.5 s.
- **Risks:** The title is long; keep it to one line at 42 px.
- **Fact status:** Process description only; no numeric claim.

### s2 — Committee and floor action

- **Visual elements:** Two-column table: “Stage” and “What happens”; three
  data rows plus a header.
- **Animation order:** Grid draws at 0.30 s; cells stagger by 0.22 s from
  0.90 s.
- **Transition in/out:** `wipe_left` (0.8 s) in; default crossfade out.
- **Narration window:** 8.5–15.5 s, estimated 4.5–5.5 s.
- **Risks:** Keep each table cell under about eight words; the engine wraps
  but does not paginate.
- **Fact status:** General process; no statistics.

### s3 — President and override

- **Visual elements:** Three-item timeline (pass both → present → sign or
  veto) and a closing card about the two-thirds override.
- **Animation order:** Line draws at 0.30 s; items appear from 0.80 s with
  0.28 s stagger; closing card fades at 3.2 s.
- **Transition in:** `slide_left` (0.8 s) in.
- **Narration window:** 16.5–23.5 s, estimated 4.5–5.5 s.
- **Risks:** “Two-thirds” must not look like a verified statistic about
  current politics; it is a procedural rule stated generically.
- **Fact status:** Procedural description; no numeric evidence claim.

## Narration and timing plan

| Segment | Scene | Offset (s) | Text | Estimated speech (s) | Risk |
|---|---|---|---|---|---|
| n1 | s1 (index 0) | 0.5 | A bill begins as an idea. A member of Congress drafts it and introduces it in one chamber. | 6.0 | Fits 8 s with headroom |
| n2 | s2 (index 1) | 0.5 | Committees hold hearings and vote. Then the full chamber debates and votes. | 4.8 | Fits 8 s |
| n3 | s3 (index 2) | 0.5 | If both chambers pass the same text, the president may sign or veto it. | 4.8 | Fits 8 s |

Estimates assume about 2.5–3 words per second. Actual TTS durations are not
measured in this text-only example.

## Claims register

| ID | Statement | Status | Evidence | Used on screen? |
|---|---|---|---|---|
| c1 | “Most bills die in committee.” | Unverified — no source supplied | None | No — omitted from storyboard and JSON |

## QA summary

- JSON is schema-drafted against the v2.1 contract; the legacy validator was
  not run as part of this example authoring step.
- No MP4, WAV or SRT was generated.
- All three shots fit the 24-second canvas.
- Table cells and timeline labels are short enough for the planned boxes.
