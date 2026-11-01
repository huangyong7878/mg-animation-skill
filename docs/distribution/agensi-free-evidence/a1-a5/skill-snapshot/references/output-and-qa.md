# Output Formats and QA Checklist

Use this reference before finalizing a response. Three artifacts are expected
together: storyboard, Scene JSON and QA notes. Keep names, durations and
wording consistent across all three.

## 1. Storyboard template

```markdown
# Storyboard — <title>

## Direction
- Audience: ...
- Language: ...
- Canvas: 960 × 540 (16:9), 24 fps
- Total duration: ... s
- Narration: text plan only / audio requested
- Tone and palette: ...

## Assumptions and open questions
- ...

## Shot table
| ID | Time (s) | Narrative goal | On-screen content | Animation / transition | Narration | Fact status |
|---|---|---|---|---|---|---|
| s1 | 0–8 | Introduce the question | Title + three cards | fade, pop, arrow draw | ... | No factual claims |
| s2 | 8–16 | Explain the mechanism | Two-column table | wipe_left, staggered rows | ... | One unverified claim omitted |
| s3 | 16–24 | Close with the outcome | Timeline + summary card | slide_left, staggered items | ... | No factual claims |

## Shot details

### s1 — <name>
- **Visual elements:** ...
- **Animation order:** ...
- **Transition out:** ...
- **Narration window:** ...
- **Risks:** ...
- **Fact status:** ...

## Narration and timing plan
| Segment | Scene | Offset (s) | Text | Estimated speech (s) | Risk |
|---|---|---|---|---|---|

## Claims register
| ID | Statement | Status | Evidence | Used on screen? |
|---|---|---|---|---|

## Production notes
- Assets still required: ...
- Decisions for the user: ...
```

### Timing estimates (label them as estimates)

There is no audio in the text path. Estimate speech as roughly:

- English: about 2.5–3.0 words per second at a relaxed narration pace.
- Chinese: about 3.5–5 characters per second at a relaxed pace.

Leave at least 20–30% headroom per shot. Never present an estimate as a
measured duration. If actual TTS later runs, its measured duration wins and
the storyboard must be revised.

## 2. Scene JSON output

- Output exactly one JSON object in a fenced `json` block.
- Use the field names and types from `scene-contract-lite.md`.
- Prefer three to five scenes for a 20–30 second piece.
- Use `version: "2.1"`, `claims: []` and `factual: false` when there are no
  verified claims.
- If a claim is unverified, either leave it out of the JSON and flag it in QA,
  or include it with `status: "unverified"` and state that the legacy gate will
  reject the document until evidence is supplied.
- Do not add fields that do not exist in the contract, even when they seem
  useful (for example `background`, `speaker`, `subtitle`, `music`).
- Do not include base64 data, data URLs, remote assets or absolute file paths.
- Keep every scene's `start + duration` inside `canvas.duration`.
- Close the document with an explicit status line outside the JSON block:

```text
Status: schema-drafted; not validated by the legacy renderer.
```

or, if validation actually ran:

```text
Status: validated with `python scripts/validate.py <file>` — exit 0.
```

## 3. QA notes template

```markdown
# QA Notes — <title>

## 1. Assumptions
- Defaults used: ...
- Information not supplied: ...

## 2. Factual status
- User-provided facts: ...
- Independently verified: ... (source and date, or "none")
- Unverified / omitted: ...
- Publishability: not ready as a verified video / ready subject to human review

## 3. Timing risks
- Estimated total speech: ... s vs. canvas ... s
- Tight scenes: ...
- Overlap check: ...

## 4. Layout and legibility risks
- Text density: ...
- Potential overflow or occlusion: ...
- Asset dependencies: ...

## 5. Validation and rendering status
- JSON syntax: checked manually / tool
- Legacy validator: not run / command + exit code
- TTS: not run / engine + command + result
- MP4: none generated / path + ffprobe evidence

## 6. Next actions
1. ...
2. ...
```

## 4. QA checklist

### Structure

- [ ] Storyboard shot IDs and times match the JSON scenes.
- [ ] Every scene has at least one visible element.
- [ ] Tables have consistent row lengths; timelines have items.
- [ ] No container nests more deeply than needed.
- [ ] Total duration is realistic for the amount of text.

### Legibility

- [ ] A title is readable at the planned canvas size.
- [ ] Cards and table cells contain short phrases, not paragraphs.
- [ ] Text boxes leave margin from each other and from the canvas edge.
- [ ] No element depends on a font or image the user did not supply.
- [ ] Chinese and English text are not mixed unintentionally.

### Motion

- [ ] Entry animations are staggered rather than simultaneous.
- [ ] Animation durations are plausible (roughly 0.3–0.8 s).
- [ ] Transitions are pairwise; no three-scene pile-up at one boundary.
- [ ] Nothing important animates after its scene ends.

### Narration

- [ ] Each segment has a clear scene anchor and offset.
- [ ] Estimated speech plus pauses fits the scene.
- [ ] No two segments are scheduled to overlap.
- [ ] Total narration fits `canvas.duration`.
- [ ] Estimates are labelled as estimates.

### Facts and provenance

- [ ] Every factual on-screen statement is either in the claims register or
      explicitly labelled in QA as user-provided/general knowledge.
- [ ] An empty `claims` array is not presented as evidence that statements
      were verified.
- [ ] No URL, quote or `verified` flag is fabricated.
- [ ] Default validation is described as metadata-only; quote presence is not
      claimed unless `--fetch-sources` actually ran, and neither mode is
      presented as truth verification.
- [ ] Unverified material is explicitly marked as not publishable.

### Honesty

- [ ] No claim that an MP4, WAV or SRT exists unless it was produced and
      verified.
- [ ] No claim that the JSON passed the renderer unless the validator ran.
- [ ] No claim that Agensi review passed.
- [ ] No claim that software was installed automatically.

## 5. Response assembly

A complete free-edition answer has this order:

1. One-paragraph summary and declared defaults.
2. Storyboard.
3. Scene JSON.
4. QA notes.
5. One short question or next step for the user.

Do not bury the limitations at the end; state them before or beside the JSON
when they affect publishability.
