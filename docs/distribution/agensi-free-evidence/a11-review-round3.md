# A11 Final Recheck (round 3) — Agensi Free Edition Distribution Adapter

> **HISTORICAL reviewer snapshot (round 3).** R-1 and R-2 were resolved after
> this report. Its F-1/F-2 findings were also corrected; see
> `a11-resolution.md` for the current status and `a11-review-round4.md` for the
> next snapshot.

- Repository: `/Users/yonghuang/Codes/mg-animation-skill`
- Branch: `docs/agensi-free-agent-b-20261031`
- Review type: final read-only recheck of R-1 (verifier hidden/duplicate members) and R-2 (A1 snapshot evidence)
- Date: 2026-11-02
- Reviewed state: commit `1e86595` plus the uncommitted/untracked implementation and evidence files
- Method: repository inspection, fresh temporary builds/validation, and read-only tests. No repository file was modified.

## Verdict: NEEDS WORK

R-1 and R-2 are **RESOLVED**. The final ZIP is reproducible at SHA256
`911a841b9c239d5066d8737e74ac44591cfeb354d030fa3504f33beeb2122b84`
(13 files, 67,610 bytes), its manifest matches both the A6 evidence and the
local `dist` manifest, and both A1 Scene JSONs pass the real validator.

No BLOCKER or MAJOR technical defect remains. The verdict is NEEDS WORK because
two MINOR evidence/handoff inconsistencies remain: the primary acceptance and
handoff documents still report the earlier 34-test/225-test state, and the A11
evidence lists an `a11-final.md` file that does not exist in the evidence
directory. These are documentation defects, not package/security failures, but
the acceptance evidence is not yet internally consistent.

## Per-item recheck

### R-1 — RESOLVED

The shared `member_name_issues` function at
`/Users/yonghuang/Codes/mg-animation-skill/scripts/package_agensi_free.py:66-84`
is used by both the builder (`collect_files`, lines 156-159) and the verifier
(`verify_package`, lines 305-307). The verifier also rejects duplicate ZIP
member names (lines 297-298), duplicate manifest paths (lines 327-328), and
manifest count/length mismatches (lines 331-336).

Independent crafted-ZIP checks with matching manifests produced:

```text
hidden_example REJECTED: Invalid ZIP member examples/.notes.md: hidden file
hidden_ref     REJECTED: Invalid ZIP member references/.secret.md: hidden file
dotdot_ref     REJECTED: Invalid ZIP member references/..md: hidden file
duplicate      REJECTED: Duplicate ZIP member names
extra          REJECTED: Invalid ZIP member extra.md: not on the allowlist
nested         REJECTED: Invalid ZIP member nested/SKILL.md: nested SKILL.md
builder hidden REJECTED: Invalid package file examples/.notes.md: hidden file
```

The duplicate case used duplicate `README.md` ZIP entries with a single-entry
manifest and was rejected by the verifier. The 36 Agensi tests pass, including
`test_verify_rejects_extra_and_nested_skill`,
`test_verify_rejects_duplicate_members`, and
`test_builder_rejects_hidden_file`.

### R-2 — RESOLVED

All five files in
`/Users/yonghuang/Codes/mg-animation-skill/docs/distribution/agensi-free-evidence/a1-a5/skill-snapshot/`
are byte-identical to the packaged skill files:

```text
SKILL.md cmp=0
README.md cmp=0
references/scene-contract-lite.md cmp=0
references/safety-and-limitations.md cmp=0
references/output-and-qa.md cmp=0
```

Both A1 outputs pass the real validator with exit code 0:

```text
OK: docs/distribution/agensi-free-evidence/a1-a5/en/scene_en.json | 3 scene(s) | 960x540 | duration 24.0s
OK: docs/distribution/agensi-free-evidence/a1-a5/zh/scene_zh.json | 3 scene(s) | 960x540 | duration 20.0s
```

`a1-a5/README.md:61-66` and `a1-a5/setup.txt:23-26` now state that the snapshot
is byte-identical to the final package and that the final metadata-only and
empty-claims wording was exercised. The stale "differs in two places" caveat is
gone. The outputs themselves contain the final metadata-only and
empty-claims-array disclosures.

## New findings

### F-1 (MINOR) — Acceptance and handoff summaries still carry stale test counts

**Files/lines**

- `/Users/yonghuang/Codes/mg-animation-skill/docs/distribution/agensi-free-evidence/README.md:16`
  says A2 uses "34 tests"; the actual
  `a2-validation.txt:48` says `Ran 36 tests`.
- `README.md:24` says A10 ran "225 tests"; the actual
  `a10-regression.txt:3` and `a10-full-log.txt:32` say `Ran 227 tests`.
- `/Users/yonghuang/Codes/mg-animation-skill/docs/distribution/agensi-free-evidence/HANDOFF.md:22`
  says "34 offline acceptance tests"; the current suite has 36.
- `HANDOFF.md:43` says "225 tests"; the current branch log has 227. The clean
  `main` baseline has 225 tests, so the handoff conflates the baseline count
  with the branch count.
- `a11-resolution.md:27,30` correctly records the current 36 Agensi tests and
  227 full-suite tests, making the discrepancy an internal contradiction.

**Concrete failure scenario**

An owner following the primary acceptance table or HANDOFF will look for 34
Agensi tests and 225 full-suite tests, while the raw evidence files and current
commands produce 36 and 227. The A2 and A10 PASS evidence therefore does not
describe the same test state as the handoff. This does not change the observed
pass/fail result, but it means the acceptance evidence cannot be treated as a
consistent final record.

**Suggested fix**

Update the handoff and acceptance summaries to 36 Agensi tests and 227
full-suite tests; where the clean `main` baseline is discussed, state
separately that it has 225 tests. Keep the pre-existing failure disclosure and
the clean-main comparison unchanged.

### F-2 (MINOR) — The A11 evidence references an absent `a11-final.md`

**Files/lines**

- `/Users/yonghuang/Codes/mg-animation-skill/docs/distribution/agensi-free-evidence/README.md:25`
  lists `a11-final.md` as part of the A11 evidence set.
- `/Users/yonghuang/Codes/mg-animation-skill/docs/distribution/agensi-free-evidence/HANDOFF.md:44`
  does the same.

The evidence directory currently contains
`a11-independent-review.md`, `a11-recheck.md`, and `a11-resolution.md`, but no
`a11-final.md`. The final report required by this review is at
`/tmp/claude-501/a11-final.md`, outside the repository, so the repository-side
reference is broken unless the owner copies the report in or changes the
reference to identify it as external.

**Concrete failure scenario**

An owner opening the A11 acceptance table or HANDOFF will follow the
`a11-final.md` reference inside the evidence directory and find no file. The
handoff therefore does not actually contain the final independent-review
artifact it advertises.

**Suggested fix**

Copy the final report into the evidence directory (when permitted) or change
both references to state that the final report is external, with its actual
path. Do not claim a repository file exists until it is present.

## A1–A11 status

| Gate | Status | Final justification |
|---|---|---|
| A1 — isolated loading, EN + ZH | PASS (with caveat) | Two simulated isolated runs used the byte-identical final snapshot; both produced text deliverables and both Scene JSONs pass the real validator. Live Agensi loading is still untested. |
| A2 — real v2.1 schema and `validate.py` | PASS | Both packaged examples and both A1 examples exit 0 under `scripts/validate.py`; negative tests exercise syntax, missing-field, illegal-scene, table-shape and unverified-claim failures. The acceptance summary's 34-test count is stale (F-1). |
| A3 — MP4/audio smoke test | PASS (with disclosed substitution) | Prior A3 evidence records a 24 s H.264/AAC MP4. Exact eSpeak path is NOT RUN; the offline `say` adapter substitution is disclosed. Not re-run in this final R-1/R-2 pass. |
| A4 — no-runtime fallback | PASS | A1/A4 evidence shows no terminal, media, or installs; the agents produced the text deliverables and explicitly did not claim a video. |
| A5 — factual-source handling | PASS (with caveat) | The unsourced claim is omitted, `claims` is empty, no `verified` flag was fabricated, and the fail-closed test passes. Default validation is correctly described as metadata-only. |
| A6 — ZIP structure / manifest / reproducibility | PASS | Fresh build is 13 files / 67,610 bytes / SHA `911a841...`; the A6 manifest/sidecar and local `dist` manifest match byte-for-byte; the verifier passes. |
| A7 — permissions/security | PASS | `--scan-only` currently passes; the prior manual review covers secrets, commands, injection, network, paths, and executable content; the final verifier rejects hidden/duplicate members and symlinks. |
| A8 — copyright/license audit | PASS (audit) — distribution BLOCKED | No repository `LICENSE` exists; the audit states default copyright and leaves license/redistribution terms to the owner. No license was added and the package must not be uploaded. |
| A9 — listing accuracy | PASS | Listing copy avoids MP4, auto-install, auto-fact-check and interactive-canvas promises; the free path is text-only and optional-render prerequisites are disclosed. |
| A10 — regression and scope | PASS (1 pre-existing unrelated failure) | 227 tests run: 1 failure, 1 skip. The failure is the existing macOS `/var` vs `/private/var` path-normalization failure, reproduced on clean `main`; no core renderer, schema, R0–R7 gate, studio or PR #38/#39 file was changed. The handoff's 225-test summary is stale (F-1). |
| A11 — independent review / owner gates | PENDING OWNER APPROVAL | Independent recheck is complete and R-1/R-2 are resolved; the evidence/handoff still needs F-1/F-2 corrections, and owner approval remains outstanding. No merge, upload, payment setup or license selection was performed. |

## Exact commands and results

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_agensi_free.py'
Ran 36 tests in 1.163s
OK
rc=0

$ PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
Ran 227 tests in 2.066s
FAILED (failures=1, skipped=1)
rc=1
```

The single failure is:

```text
test_valid_contract_passes_caption_timings_to_renderer
AssertionError: '/private/tmp/.../timings.json' != '/tmp/.../timings.json'
```

It matches the pre-existing macOS path-normalization failure in
`test_auto_pipeline_contract.py` and reproduces on clean `main` 10ae8a6.

Packaging:

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/package_agensi_free.py --out-dir /tmp/claude-501/a11-final-build
BUILT /private/tmp/claude-501/a11-final-build/agensi-free-1.0.0.zip
MANIFEST /private/tmp/claude-501/a11-final-build/agensi-free-1.0.0.manifest.json
SHA256 911a841b9c239d5066d8737e74ac44591cfeb354d030fa3504f33beeb2122b84
FILES 13 | BYTES 67610
PASS: deterministic ZIP structure, manifest and safety scan

$ cmp -s fresh.zip distributions/agensi-free/dist/agensi-free-1.0.0.zip
zip_cmp=0
$ cmp -s fresh.manifest.json docs/distribution/agensi-free-evidence/a6-manifest.json
a6_manifest_cmp=0
$ cmp -s fresh.manifest.json distributions/agensi-free/dist/agensi-free-1.0.0.manifest.json
dist_manifest_cmp=0

$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/package_agensi_free.py --scan-only
PASS: package scan (allowlist, secrets, commands, injection, paths, links)
rc=0
```

A1 snapshot and validation:

```text
$ cmp -s distributions/agensi-free/SKILL.md docs/distribution/agensi-free-evidence/a1-a5/skill-snapshot/SKILL.md; echo $?
0
$ cmp -s distributions/agensi-free/README.md docs/distribution/agensi-free-evidence/a1-a5/skill-snapshot/README.md; echo $?
0
$ cmp -s distributions/agensi-free/references/scene-contract-lite.md docs/distribution/agensi-free-evidence/a1-a5/skill-snapshot/references/scene-contract-lite.md; echo $?
0
$ cmp -s distributions/agensi-free/references/safety-and-limitations.md docs/distribution/agensi-free-evidence/a1-a5/skill-snapshot/references/safety-and-limitations.md; echo $?
0
$ cmp -s distributions/agensi-free/references/output-and-qa.md docs/distribution/agensi-free-evidence/a1-a5/skill-snapshot/references/output-and-qa.md; echo $?
0

$ python3 scripts/validate.py distributions/agensi-free/examples/scene_en.json
OK: ... | 3 scene(s) | 960x540 | duration 24.0s
exit=0
$ python3 scripts/validate.py distributions/agensi-free/examples/scene_zh.json
OK: ... | 3 scene(s) | 960x540 | duration 24.0s
exit=0
$ python3 scripts/validate.py docs/distribution/agensi-free-evidence/a1-a5/en/scene_en.json
OK: ... | 3 scene(s) | 960x540 | duration 24.0s
exit=0
$ python3 scripts/validate.py docs/distribution/agensi-free-evidence/a1-a5/zh/scene_zh.json
OK: ... | 3 scene(s) | 960x540 | duration 20.0s
exit=0
```

Scope and working-tree check:

```text
$ git status --porcelain
 M .gitignore
?? distributions/
?? docs/distribution/agensi-free-evidence/
?? docs/distribution/agensi-free-license-audit.md
?? scripts/package_agensi_free.py
?? tests/test_agensi_free.py
```

The only tracked modification is `.gitignore`, which adds
`distributions/agensi-free/dist/`; no core renderer, schema, R0–R7 gate,
private project, or PR #38/#39 file was changed. No repository file was
modified by this review.

## Release decision

Do not treat the A11 handoff as complete until F-1 and F-2 are corrected.
A8 distribution remains BLOCKED pending the owner's license decision, and A11
owner approval remains PENDING. The package itself is reproducible and its
manifest is internally consistent.
