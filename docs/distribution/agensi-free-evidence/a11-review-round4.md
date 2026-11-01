# A11 Final Recheck 2 (round 4) — F-1 and F-2

> **HISTORICAL reviewer snapshot (round 4).** F-1 was confirmed resolved. The
> F-2 concern (a stale reviewer report presented as current) is addressed by
> labelling every reviewer report in this directory as historical and keeping
> the current status in `a11-resolution.md`. This file is itself historical for
> the same reason.

- Repository: `/Users/yonghuang/Codes/mg-animation-skill`
- Branch: `docs/agensi-free-agent-b-20261031`
- Scope: read-only verification of F-1 (stale test counts) and F-2 (missing `a11-final.md`) only
- Date: 2026-11-02
- No repository file was modified.

## Verdict: NEEDS WORK

F-1 is corrected in the primary acceptance and handoff documents. F-2 is only
partially corrected: the referenced `a11-final.md` now exists and the links
resolve, but the copied file is byte-identical to the previous NEEDS WORK
report and still says F-1/F-2 are unresolved and that the clean-main baseline
has 225 tests. As evidence, it now contradicts the corrected acceptance
documents and `a11-resolution.md`.

## F-1 — RESOLVED

The primary summaries now carry the correct counts:

- `docs/distribution/agensi-free-evidence/README.md:16` says 36 Agensi tests.
- `HANDOFF.md:22` says 36 offline acceptance tests.
- `README.md:24` and `HANDOFF.md:43` say 227 tests on this branch and 191 on
  clean `main` 10ae8a6.
- `a11-resolution.md:22,29,32,38` records 36 Agensi tests, 227 full-suite
  tests, and the 191-test clean-main baseline.

The current commands confirm the counts:

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_agensi_free.py'
Ran 36 tests in 1.109s
OK
rc=0

$ PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
Ran 227 tests in 2.377s
FAILED (failures=1, skipped=1)
rc=1
```

The baseline full log contains the stated result:

```text
docs/distribution/agensi-free-evidence/a10-baseline-main-full.log:32:
Ran 191 tests in 1.453s
FAILED (failures=1, skipped=1)
```

The clean-main failure is the same macOS path-normalization failure. No
remaining F-1 issue was found in the corrected acceptance/handoff documents.

## F-2 — PARTIALLY RESOLVED; one remaining finding

The reference target now exists:

```text
docs/distribution/agensi-free-evidence/a11-final.md
```

so the links in `README.md:25` and `HANDOFF.md:44` resolve. However, the file
was copied unchanged from the previous external report:

```text
$ shasum -a 256 docs/distribution/agensi-free-evidence/a11-final.md /tmp/claude-501/a11-final.md
fccf3f18a585afbef633bc42f22820f4f17ad9fa5c1b559fe8d6358c5e7d73f0  docs/distribution/agensi-free-evidence/a11-final.md
fccf3f18a585afbef633bc42f22820f4f17ad9fa5c1b559fe8d6358c5e7d73f0  /tmp/claude-501/a11-final.md
cmp=0
```

That copied report is not a final report for the corrected tree. It still
contains:

- `a11-final.md:10` — `## Verdict: NEEDS WORK`.
- `a11-final.md:17-21` — says the acceptance/handoff documents still report the
  earlier 34/225 state and that `a11-final.md` does not exist.
- `a11-final.md:86-113` — the stale F-1 finding and the incorrect suggestion
  that the clean-main baseline has 225 tests.
- `a11-final.md:115-136` — says `a11-final.md` is absent and the final report is
  only at `/tmp/claude-501/a11-final.md`.
- `a11-final.md:149,157,158` — still refers to the 34-test and 225-test
  summaries and says the handoff needs F-1/F-2 corrections.

This is now a concrete evidence contradiction: `README.md:16,24`,
`HANDOFF.md:22,43`, and `a11-resolution.md:22-23` say the counts are corrected
and F-1/F-2 are resolved, while the newly added `a11-final.md` says the
opposite. An owner following the A11 evidence set will encounter two mutually
exclusive final states.

**Suggested fix**

Replace `docs/distribution/agensi-free-evidence/a11-final.md` with the corrected
final report (this `a11-final2.md` once the remaining finding is addressed), or
explicitly mark the copied file as historical and point the A11 table/handoff
to the current resolution. Do not present the pre-fix NEEDS WORK report as the
current final evidence.

## Remaining finding

F-2 residual (MINOR): the `a11-final.md` link resolves, but the artifact is the
stale pre-correction report and contradicts the corrected 36/227/191 counts
and the resolution record. Until it is replaced or marked historical, the A11
evidence set is not internally consistent.

## Final verdict

**NEEDS WORK** — F-1 is resolved; F-2's link is resolved but its evidence
content is not. No unrelated area was re-reviewed.
