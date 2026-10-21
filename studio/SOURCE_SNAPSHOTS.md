# MG Studio source snapshots: first migration step

After a successful approved R4 job, MG Studio saves only the changed,
permitted source files under `work/mg_studio/snapshots/<sha256>/`.
A canonical manifest binds the base Git commit, approved finding IDs,
file paths, sizes and SHA256 hashes. Reusing a snapshot is permitted only
when verification succeeds. Editing a snapshot makes verification fail.

This is a **preproduction audit artifact**, not a complete project archive
or a formal Stage D delivery. No Git commit, push or publication is created
by this module. The existing formal Stage D builder still requires a
real Git SHA and full script/voice lock verification. Do not substitute
snapshot digest for `implementation_commit` until a separate production
contract migration and independent R5 provenance validation are implemented.

The macOS detached worktree continues to exist for human inspection.
A snapshot does not imply visual correctness, that tests passed, or R5 PASS.
The goal is to preserve Codex changes against temporary worktree cleanup
without manually committing Git each time.
