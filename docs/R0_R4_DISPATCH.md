# R0 → R4 human-approved rework dispatch

After `review` and `rework-draft`, review `r4_rework_draft/rework_task_candidate.md`
and the underlying video evidence. Candidate findings are **not** approved QA.
Approve only the finding IDs you actually want R4 to address.

Run from a checkout with the approved R0 workspace and the unchanged Stage D
artifact root:

```bash
python workflow/orchestrator.py dispatch-rework \
  --workdir work/orders_pilot/formal_r4_v2 \
  --artifact-root work/orders_pilot/stage_d_delivery_v2 \
  --inbox work/r4_inbox/pilot001_v3 \
  --approve-id V2-P1-001 --approve-id V2-P1-002 \
  --approved-by "Project owner" --dry-run
```

Remove `--dry-run` to **explicitly** issue a local R4 assignment. The inbox has
`assignment.json` and `TASK.md` for an R4 execution agent (Muse, Codex,
DeepSeek or another executor). The local assignment does NOT itself execute
R4 code: the executor must be launched in its own context/worktree and given
the inbox path. If GitHub issue dispatch is desired, add
`--repo huangyong7878/mg-animation-skill` to the non-dry-run command;
GitHub issue creation is explicit and requires logged-in `gh`.

Guards: selected IDs must exist in the source-bound R5 candidate, task source
hash and exact video bytes must match, director spec and implementation SHA
must match, and formal locks remain unchanged. No overwrite of prior inbox.
Neither dispatch nor the subsequent R4 task is an R5 PASS, an R0
`record-qa`, or R7 approval. New code means a new render and new R5 audit.
