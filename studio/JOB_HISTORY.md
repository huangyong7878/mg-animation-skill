# MG Studio task journal (stacked on PR #28)

The local R4 executor now records each run into SQLite under
`work/mg_studio/jobs.sqlite3` and exposes `GET /api/r4/history`.
The browser can inspect recent job IDs, status, and task IDs.

A job that was `running` when MG Studio stopped is marked `interrupted`
when the service starts next time. It is **not automatically retried**,
preventing silent additional Codex usage. The stored result only includes
worktree path, changed file names, base commit and exit status; raw model
transcripts and credentials are not stored in SQLite.

Scope: this is **not** a durable worker, scheduling service, live cancellation
or production-ready recovery mechanism. An interrupted subprocess or orphan
worktree may still need manual cleanup. A successful status does not authorize
commit, full-media R5 pass, or R7 publishing.

Tests:
```
python3 -m unittest discover -s tests -p test_mg_studio_jobs.py -v
```
