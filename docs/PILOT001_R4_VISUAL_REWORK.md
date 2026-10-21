# Pilot 001 — R4 visual rework from DeepSeek sampled-frame observations

Review source: 26 time-sampled image frames of the previously rendered Stage D MP4.
DeepSeek had **not** reviewed continuous motion or audio; observations are not a
formal full R5 PASS. One P1 and four P2 concerns were reported.

## Changed implementation only

- **P1 stock diamond occlusion (4.0–5.5s)**: A/B move to y=180 and
  y=380 when reaching the stock branch (diamond center y=280, half-height 46).
  The cards remain vertically outside the diamond with margin; node text
  remains in front. The 5.8s branch event time remains unchanged.
- **P2 opening identity**: show letter/订单 as soon as each order fades in;
  keep the original renderer appearance event timestamps 1.0s and 1.2s.
  This does not redefine narration “simultaneous”; visually verify opening timing.
- **P2 contrast**: darken muted text and connector lines, slightly enlarge labels.
- **P2 B waiting state**: ramp up earlier and remove opacity pulsing to increase
  legibility, without changing the queue arrival event 8.4s.
- **P2 A status latency**: no shift to approved event timing. A arrives at 10.0s
  and “已发货” appears from 10.4s as before; this requires re-evaluation against
  the real rendered frames rather than assuming a 9.0s model observation is accurate.

## Locked content protection

No edits to narration, storyboard, approved AV cue, Script Lock, Voice Lock,
timings, or voice bytes. A new implementation commit requires a **new** media
render, new manifest/delivery SHA and a fresh independent R5 review. The
old 26-frame DeepSeek assessment is evidence of a prior version, not an
approval of this rework. Do not overwrite immutable Stage D artifact directory.

## Mandatory post-merge checks

1. Run relevant unit tests / CI.
2. Render a new Stage D output to a **new empty directory** using the exact locked
   source and voice assets. Bind delivery to current Git HEAD.
3. Watch continuously at 3.5–6.0s (A/B visibility), 1–2s (opening), and
   8–12s (labels and state). Capture actual evidence.
4. Re-run R0 receive/review-package for the updated implementation commit
   with fresh workspace/attempt as appropriate; re-run independent R5.
5. Keep R7 publishing unapproved.
