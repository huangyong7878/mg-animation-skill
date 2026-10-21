# MG Studio generic R4 tasks

This change builds on PR #27 and makes R4 execution **assignment-driven**.
No project name, six Pilot defect IDs, or fixed source path is embedded in
the runner. R0 now requires `--allow-file` on `dispatch-rework` and stores a
bounded execution policy in `assignment.json`.

Example for **future newly approved** tasks:
```bash
python workflow/orchestrator.py dispatch-rework \
  --workdir work/orders_pilot/formal_r4_v2 \
  --artifact-root work/orders_pilot/stage_d_delivery_v2 \
  --inbox work/r4_inbox/pilot001_v3_new \
  --approve-id V2-P1-001 --approve-id V2-P1-002 \
  --approved-by "Project owner" \
  --allow-file scripts/primitives/orderflow.py \
  --allow-file tests/test_pilot001_visual_fix.py --dry-run
```

R0 writes `execution_policy.allowed_files` and
`execution_policy.max_runtime_seconds`. The UI lists only schema-valid tasks
under `work/r4_inbox/<job>/assignment.json`; clients submit a task ID, not
an arbitrary filesystem path. The runner starts a detached worktree at the
assignment's pinned commit, checks changed paths and leaves a result for review.

**Existing Pilot 001 V3 assignment is old format** without
`execution_policy`. It is intentionally not executable using this new runner.
Do not hand-edit the old approved assignment; issue a new R0-approved task
using the updated contract after verifying its source evidence.

This is a **developer preview**. Post-run Git diff checks do not constitute
a hardened OS sandbox, and Codex can run tools inside the sandbox. No commits,
GitHub pushes, renders, R5 passes or R7 release are automated. Need robust
persistent job queue, trust-boundary sandbox hardening and cancellation before
production deployment.
