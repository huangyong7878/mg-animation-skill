# Process Log — How Wi-Fi Works

## Inputs read, in order

1. `/tmp/claude-501/agensi-a1-final/en/skill/SKILL.md` — loaded first and followed as the active skill.
2. `/tmp/claude-501/agensi-a1-final/en/brief.md` — user brief (not a skill file).
3. `/tmp/claude-501/agensi-a1-final/en/skill/references/scene-contract-lite.md` — requested before drafting the Scene JSON.
4. `/tmp/claude-501/agensi-a1-final/en/skill/references/output-and-qa.md` — requested before finalizing the deliverables.
5. `/tmp/claude-501/agensi-a1-final/en/skill/references/safety-and-limitations.md` — requested for the factual-integrity, permission, and claim-treatment rules.

No examples directory was read or provided. No file outside `/tmp/claude-501/agensi-a1-final/en/` was read or written.

## Outputs written

1. `/tmp/claude-501/agensi-a1-final/en/out/storyboard_en.md`
2. `/tmp/claude-501/agensi-a1-final/en/out/scene_en.json`
3. `/tmp/claude-501/agensi-a1-final/en/out/qa_notes_en.md`
4. `/tmp/claude-501/agensi-a1-final/en/out/process_log.md`

## Handling decisions

- Produced three 8.0-second shots for a 24.0-second, 960 × 540, 24 fps piece.
- Used a `row` flow in `shot_02` and a `table` in `shot_03`, as the brief required.
- Omitted the unsourced “up to 100 meters indoors” claim from the storyboard, narration, and Scene JSON. It is recorded only as an explicit unverified omission in the claims register and QA notes.
- Used `claims: []` and `factual: false` because no verified claims were authored. The QA notes state that the empty array is not evidence of verification and that the default v2.1 claim gate is metadata-only.
- No source, URL, quotation, verified flag, validation result, or render result was fabricated.

## Validation and render status

No MP4, audio, SRT, or rendered frame was generated. No software was installed or downloaded. The Scene JSON is schema-drafted but not validated by the legacy renderer.

No Bash, terminal, Python, FFmpeg, TTS engine, browser, or network access was used. No validator or fact-check command was run, so no command exit code exists.
