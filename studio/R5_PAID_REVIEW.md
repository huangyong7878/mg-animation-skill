# MG Studio: explicit paid DeepSeek sampled-frame R5 review

This increment adds a delivery-bound, single-run UI for DeepSeek, **not**
full-audio/video certification. First choose a verified Stage D delivery,
then click preflight and explicitly confirm the paid API invocation.
The local server must have `DEEPSEEK_API_KEY` set and
`R5_ENABLED=true`. Neither is stored in the browser or GitHub.

The backend creates a new R0 formal workspace from the immutable
delivery's original script, storyboard, cue sheet, WAV, timings and approved
locks. It uses existing `prepare → receive → review-package → review`
gates before calling the API. Any failure blocks submission. One
workspace is created for each paid attempt; it is never overwritten or
silently retried, including on network/API failure. A matching workdir
blocks duplicate paid submissions from this UI.

DeepSeek examines sampled frames, not contiguous motion or audio. Output
remains `pending`, and **never** authorizes R5 full PASS, R7 approval,
merge, publication or automatic R4 rework. The existing R5 history panel
shows resulting observations and source hash bindings.

Developer preview limitations: paid job status is held in memory; server
restart can interrupt a request, but the workdir remains to block naive
retries. No cancellation/price quote or token hard-budget enforcement.
Do not trigger the paid call until testing the preflight locally.
