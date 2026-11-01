# QA Notes — How a Bill Becomes Law

## 1. Assumptions

- The brief was complete enough for a three-shot, 24-second video.
- Canvas defaults: 960 × 540, 16:9, 24 fps.
- Narration is a text plan only; no voice engine was selected.
- No image assets are used, so the JSON has no `image` nodes.
- Speech durations are estimates at roughly 2.5–3 words per second.

## 2. Factual status

- **User-provided / general process:** the description of introduction,
  committee action, floor votes, presidential action and veto override.
- **Independently verified:** none in this example. No source URL, quote or
  human review record is attached.
- **Unverified and omitted:** “Most bills die in committee.” The brief gave no
  source, so it does not appear on screen or in the JSON claims array.
- **JSON representation:** `claims` is empty and no scene is `factual: true`.
  That means no claim objects were registered; it does not mean the statements
  are verified.
- **Publishability:** suitable as an unverified educational draft. Do not label
  it as a fact-checked video without a separate evidence review.

## 3. Timing risks

| Segment | Window (s) | Estimated speech (s) | Risk |
|---|---|---|---|
| n1 | 0.5–7.5 | 6.0 | Fits with about 1.5 s headroom |
| n2 | 8.5–15.5 | 4.8 | Fits comfortably |
| n3 | 16.5–23.5 | 4.8 | Fits comfortably |

- Estimated total speech: about 15.6 s in a 24 s canvas.
- No segment overlap is scheduled.
- Actual TTS durations were not measured for this example and may differ.

## 4. Layout and legibility risks

- The title “How a Bill Becomes Law” fits one line at 42 px on 960 px width.
- Three flow cards and two arrows fit the 88% row width.
- Table cells stay under about eight words; the engine wraps and shrinks but
  does not paginate.
- The closing card is short enough for one or two lines.
- No element relies on a custom font or an external image.

## 5. Validation and rendering status

- JSON syntax: checked while authoring.
- Legacy validator: in the repository acceptance run,
  `python scripts/validate.py distributions/agensi-free/examples/scene_en.json`
  exited `0`. Re-run it in your environment to confirm.
- TTS: not run for this example.
- MP4/WAV/SRT: none generated for this example. The package's separate
  acceptance smoke test rendered a different local artifact and is not part of
  this example.
- Subtitle burn-in was not exercised here.

## 6. Next actions

1. Re-run `python scripts/validate.py examples/scene_en.json` after any edit.
2. Choose a TTS engine and re-time narration from real audio if audio is
   required.
3. Add real evidence to the claims register before publishing any statistic.
4. Run the optional render path only with the user's approval and an existing
   installation.
