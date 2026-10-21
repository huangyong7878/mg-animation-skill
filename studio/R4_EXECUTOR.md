# MG Studio R4 controlled execution — dependent on PR #26

This PR adds an explicit visual R4 button to the local MG Studio UI. It reads
the existing approved `work/r4_inbox/pilot001_v3/assignment.json`; Codex
runs in an isolated detached Git worktree at the **exact V2 source commit**
embedded in that assignment. Workspace-write privileges are confined to the
Codex sandbox, and afterwards the runner rejects changes outside
`scripts/primitives/orderflow.py` and `tests/`.

**This is a developer preview and not a hardened OS security boundary.**
Do not use it with untrusted code, secrets accessible to the local shell,
or unreviewed model configuration. No R4 model request is made without
a button click and confirmation checkbox. Model usage may count toward your
Codex plan allowance. The UI does not yet provide a cancellation control.

On the feature branch, run `python3 studio/server.py`, open
`http://127.0.0.1:8765`, and inspect the R4 panel. The approved assignment
must exist locally and its V2 commit must exist in the Git checkout. A successful
run leaves the isolated worktree and changed source for human review.
**Do not treat success as approval or a finished V3 render.** This version
does not create commits, PRs, Stage D video or R5 PASS, and never publishes.
The next milestone is independent diff verification, tests, and Stage D V3.

PR #26 supplies the base dashboard; merge PR #26 before merging this PR.
