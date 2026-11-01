# A1 / A4 / A5 — Isolated Run Results

Date: 2026-11-01 · Runner: Agent B (AI role)

## A1 — isolated Agensi-style loading

Two fresh agents with no prior conversation and no repository access each
received only a skill snapshot and a new brief:

| Run | Brief | Reads recorded | Deliverables |
|---|---|---|---|
| English | `en/brief.md` — How Wi-Fi Works, 24 s | `SKILL.md` → `brief.md` → `scene-contract-lite.md` → `output-and-qa.md` → `safety-and-limitations.md` | `en/storyboard_en.md`, `en/scene_en.json`, `en/qa_notes_en.md` |
| Chinese | `zh/brief.md` — 为什么天空是蓝色的，20 s | `SKILL.md` → `brief.md` → `scene-contract-lite.md` → `output-and-qa.md` → `safety-and-limitations.md` | `zh/storyboard_zh.md`, `zh/scene_zh.json`, `zh/qa_notes_zh.md` |

Each run also wrote a `process_log.md` listing read paths, outputs and
capability statements. Neither run read the package examples, the repository,
private notes or any path outside its isolated directory.

Both generated Scene JSON documents pass the real legacy validator
(`validation.txt`, exit 0 for each). The validator was run by the evidence
reviewer after the runs, not by the isolated agents.

## A4 — no-runtime fallback

Both runs were instructed that the host had no terminal, Python, FFmpeg, TTS,
network or local repository, and to use no Bash. Their logs state:

- no commands were executed;
- no software, model, font or asset was installed or downloaded;
- no MP4, audio, SRT or rendered frame exists (verified: zero media files in
  this evidence directory);
- the Scene JSON is schema-drafted, not renderer-validated.

The agents still produced all three text deliverables and explicitly refused
to claim a video.

## A5 — factual-source handling

Both briefs contained one claim with no source:

- English: “Wi-Fi signals can travel up to 100 meters indoors.”
- Chinese: “人眼对蓝光最敏感。”

Both runs:

- labelled the source notes as user-provided and uncited, not verified;
- omitted the questionable claim from on-screen content, narration and JSON;
- left `claims` empty and no scene `factual: true`;
- stated the draft is **not ready to publish as a verified video**;
- did not fabricate a URL, quote, date or `verified` flag.

The repository test suite additionally proves the fail-closed behavior: a
`2.1` document with an `unverified` claim is rejected by `scripts/validate.py`
(`test_unverified_claim_is_fail_closed`).

## Caveats

- These are simulated Agensi-style hosts, not the live Agensi platform. The
  actual MCP `get_skill` loading behavior and platform review remain unverified
  until an upload happens.
- Both runs used the **final package snapshot**: `skill-snapshot/` is
  byte-identical to the packaged `SKILL.md`, `README.md` and three references.
  The final metadata-only claim-gate wording and the empty-claims-array rule
  were exercised; both QA notes state that an empty `claims` array is not
  verification and that the default gate checks metadata only.
