# MG Studio Stage D delivery (Pilot 001 only)

This incremental UI feature builds on the approved Pilot 001 offline Stage D
builder. It is not a general-purpose renderer and never manufactures voice
assets or approves R5/R7.

Run `python3 studio/server.py`, open http://127.0.0.1:8765 and click
**检查交付条件**. The preflight verifies presence of the **original** WAV,
timings, script/voice lock and related approved files, source commit cleanliness
and the existing production gate. Only if green, explicitly check the
authorization box to run **生成 Stage D 成片**.

The builder generates a unique never-overwritten
`work/orders_pilot/stage_d_studio_<runid>` directory with the locked voice,
MP4, keyframes, delivery, QA pending template, and media manifest. Source
identity is taken from actual Git HEAD, never from uncommitted Codex patches.

Important: original locked WAV/timings are local and are NOT guaranteed to
exist in detached R4 worktrees. **Missing media blocks building.** Review
and commit R4 changes first, preserving the approved assets, then run preflight.
Stage D success means `ready_for_qa`, not an independent audiovisual R5 PASS,
and does not authorize R7 release or publication.

Limitations: build jobs are in-memory and cannot yet be cancelled; an abrupt
service stop may leave a partial output directory. Never treat partial outputs
as valid deliverables. Rendering is bounded to 15 minutes; existing builder
commands have shorter per-step timeouts. This feature is deliberately
restricted to Pilot 001 until the production builder becomes generic.
