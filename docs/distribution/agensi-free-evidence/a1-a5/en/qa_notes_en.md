# QA Notes — How Wi-Fi Works

**Delivery status:** Text-only draft. No validator, TTS engine, audio, video, subtitles, or rendered frames were produced. The Scene JSON is schema-drafted against the v2.1 contract and is not validated by the legacy renderer. This draft is **not ready to publish as a verified video**.

## 1. Assumptions
- Defaults used: English, 960 × 540 (16:9), 24 fps, 24.0 s total, three 8.0 s shots, and a 0.6 s crossfade from `canvas.default_transition`.
- Narration is text timing only. No TTS engine was selected or run, so no audio duration was measured.
- The source notes in the brief are treated as user-provided, uncited explanation. No external source was read, fetched, or independently checked.
- No image, font, music, or voice asset was supplied. The Scene JSON contains no image nodes and references no external files.
- The final shot holds on its takeaway; no end card or call to action was requested or added.

## 2. Factual status
- **User-provided facts:** The brief says Wi-Fi uses radio waves to carry data; a router connects to the internet and broadcasts a radio signal; a device with a Wi-Fi adapter picks up that signal and exchanges data with the router; and 2.4 GHz generally travels farther and is more crowded while 5 GHz generally offers more speed at shorter range. These statements are paraphrased on screen and in narration.
- **Independently verified:** None. No URL, quotation, source document, reviewer, or review date was supplied or checked.
- **Unverified / omitted:** “Wi-Fi signals can travel up to 100 meters indoors.” The brief supplied no source. This statement was omitted from the storyboard visuals, narration, and Scene JSON. It appears in these notes and in the claims register only as an explicit omission.
- **Empty claims array:** The Scene JSON contains `claims: []`. That is **not** a statement that the content is verified. It means no claim entries were authored; the explanatory content remains user-provided/general knowledge and requires human source review. No evidence, URL, or verified flag was fabricated.
- **`factual: false`:** All three scenes use `factual: false` because no verified claim IDs are attached. This flag is not a truth rating and does not turn user-provided statements into verified facts.
- **Default claim gate:** For v2.1, `scripts/validate.py` checks claim status, http(s) URL shape, and a quote length of at least 8 characters. That check is **metadata only**; it does not fetch the URL or confirm the quote appears there. `scripts/factcheck.py --fetch-sources` would add a live quote-presence check, but neither mode proves that a claim is true or that a source is reliable. Neither command was run here.
- **Publishability:** Not ready to publish as a verified video. It is usable as a pre-production draft subject to human factual and design review.

## 3. Timing risks
- Estimated total speech: 44 words, or 14.7–17.6 s at 2.5–3.0 English words per second, against a 24.0 s canvas.
- Planned narration windows at the slowest estimate: 0.4–6.0 s, 8.4–14.4 s, and 16.4–22.4 s. The segments do not overlap and all finish inside 24.0 s.
- Per-shot headroom at the slowest estimate: 2.0 s in shot_01 (25%), 1.6 s in shot_02 (20%), and 1.6 s in shot_03 (20%).
- Tight scenes: none by estimate, but actual TTS may lengthen “Wi-Fi,” “2.4 GHz,” and “5 GHz.” No measured durations exist.
- Overlap check: scene-index anchors are 0.0, 8.0, and 16.0 s. The planned offsets and estimated speech ends leave no overlap. A future TTS run must replace these estimates with measured durations and revise the plan if needed.

## 4. Layout and legibility risks
- Text density is moderate in shot_01: one 56 px title, one 24 px subtitle, two cards, and a footer. The 8% side margins are intact.
- Shot_02 uses a five-child row. At 960 px, the two arrows are roughly 51 px wide and the outer cards roughly 213 px wide. Three-line caps and 20 px text should fit, but the renderer’s actual font metrics are unknown.
- Shot_03 uses a three-column, two-row table at 20 px plus a two-line takeaway card. “Generally shorter” may wrap under a wide font; the table still has room within its 42% height.
- No intentional occlusion or canvas overflow is planned. Card text uses short phrases rather than paragraphs.
- Asset dependency: none. Fonts and a TTS voice would come from a local legacy installation and were not supplied. No Chinese/English mixing is intended.

## 5. Validation and rendering status
- **JSON syntax:** Hand-checked against the v2.1 contract and inspected for balanced braces, commas, required fields, unique IDs, table row widths, scene timing, and narration anchors. No JSON parser or schema tool was run.
- **Legacy validator:** Not run. No terminal or repository was available, so there is no command and no exit code.
- **Claim gate:** Not run. The default gate is metadata-only as described above; `--fetch-sources` was not used.
- **TTS:** Not run. No audio, timing file, or SRT was produced.
- **MP4 / audio / SRT / frames:** None generated.
- **Manual timing check:** 8.0 + 8.0 + 8.0 = 24.0 s; every scene ends at or before `canvas.duration`.
- **Table check:** Three columns; each of the two rows has exactly three cells.
- **Asset check:** No image nodes, network URLs, data URLs, or absolute paths.

**Status:** Schema-drafted against the MG Animation v2.1 contract; not validated by the legacy renderer.

## 6. Next actions
1. Conduct a human source review of the four source-note statements. If the 100 m figure must appear, supply a real source with a URL and exact quotation, verify its meaning, and add a properly evidenced claim; otherwise keep it omitted.
2. If a local legacy checkout is available, run `python scripts/validate.py path/to/scene_en.json` and record the exact exit code. Do not edit the validator to force a pass.
3. If a rendered video is explicitly requested, first confirm the local repository, Python 3.10+, Pillow, numpy, jsonschema, FFmpeg, `ffprobe`, and a configured TTS engine. Then run the unmodified pipeline only with approval, and verify outputs with `ffprobe`.
4. Review the storyboard at 960 × 540 with the intended font and adjust card line breaks or font sizes if the actual renderer overflows.
5. Decide whether the 2.4 GHz / 5 GHz comparison needs a named source; retain the “generally” qualifiers until then.
