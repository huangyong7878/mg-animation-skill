# R5 findings → R0 structured rework → R4

## Purpose

Close the handoff between **sampled-frame R5 model observations** and **R4
implementation tasks** without changing independent QA or human release gates.

The DeepSeek adapter now asks for a strict JSON object with a `findings` array.
Each finding must specify `id`, `severity` (P0/P1/P2), `shot_id`,
`expected`, `observed`, `fix_request`, `evidence` and optionally
`timestamp_s`. Unparseable text is retained as `observations.md`; it
must **not** be silently converted into approved findings.

Upon a valid nonempty candidate, R0 automatically generates:

- `WORKDIR/r5_deepseek/findings_candidate.json` — structured
  model-suggested issues, bound to `spec_sha256`,
  `implementation_commit` and the actual MP4 SHA256.
- `WORKDIR/r4_rework_draft/rework_task_candidate.json` — ordered
  and validated R4 tasks, with explicit `draft_unverified` status.
- `WORKDIR/r4_rework_draft/rework_task_candidate.md` — human-readable
  instructions for R4, including the source version and mandatory rerender.

The R0 command can also consume a reviewed candidate **without another API call**:

```bash
python workflow/orchestrator.py rework-draft \
  --workdir work/orders_pilot/formal_r4_v2 \
  --findings work/orders_pilot/formal_r4_v2/r5_deepseek/findings_candidate.json \
  --artifact-root work/orders_pilot/stage_d_delivery_v2
```

Existing workdirs with an already created `r4_rework_draft` refuse overwrite.
Use the automatically generated task instead of invoking twice.

## Safety constraints

- The R0 state remains `review_pending`. Draft findings are **not**
  `record-qa --decision rework`, not a full R5 `pass`, and not R7 approval.
- DeepSeek inspected sampled frames only. It has NOT heard audio or verified
  every continuous motion frame; these fields remain false in task metadata.
- A human or independently qualified reviewer must verify reported P0/P1
  evidence and complete full AV QA as appropriate. Existing `record-qa`
  requires a separate complete schema-valid QA report; `release-check`
  still requires independently passed QA and separately authorized R7.
- No automatic code rewrite, GitHub PR creation, payment rerun, or publication.
  R4 receives the task, fixes only confirmed visual problems, creates a NEW
  implementation commit and fresh immutable Stage D delivery, then R5 reassesses.
- Do not change Script Lock, Voice Lock, narration, approved AV cues, or reuse
  old QA for a new implementation commit.

## Existing Pilot 001 V2

The earlier V2 DeepSeek run produced free-form `observations.md`; it cannot
be retroactively assumed to have returned strict JSON. Its identified issues
can be manually transcribed into a candidate JSON *with exact evidence*
and validated by `rework-draft`, without a second paid model call.
