# A11 Recheck (round 2) — Agensi Free Edition Distribution Adapter

> **HISTORICAL reviewer snapshot (round 2).** This report records the state at
> its own date. Its findings were fixed; see `a11-resolution.md` for the
> current status and `a11-review-round3.md` / `a11-review-round4.md` for later
> snapshots.

- Repository: `/Users/yonghuang/Codes/mg-animation-skill`
- Branch: `docs/agensi-free-agent-b-20261031`
- Review type: independent recheck of the prior 9 findings after implementation changes
- Date: 2026-11-01
- Method: read-only repository inspection plus temporary build/test artifacts; no repository file was modified

## Verdict: NEEDS WORK

The original BLOCKER is fixed: the final package is reproducible from the
current tree, the A6 manifest and the shipped ZIP match, and the stale
11-file/QA-note mismatch is gone. MAJOR-2, MAJOR-3, MAJOR-4 and MINOR-1–3 are
also fixed.

Two original issues remain, and one is still in the same verifier boundary as
MAJOR-1: `verify_package` accepts hidden/dot-prefixed ZIP members and duplicate
members that the builder would reject. MINOR-4 is also not actually fixed: the
A1 caveat still says the snapshot differs in only two places and that reference
text/safety rules are unchanged, while the diff shows changes across all three
references and the SKILL body.

## Finding-by-finding recheck

| Original finding | Status | Recheck result |
|---|---|---|
| BLOCKER-1 — stale A6/A7 evidence and ZIP | **RESOLVED** | Fresh build is 13 files / 67,610 bytes / SHA `911a841b9c239d5066d8737e74ac44591cfeb354d030fa3504f33beeb2122b84`. A6 manifest and shipped dist manifest are byte-identical to the fresh manifest; shipped ZIP SHA matches; A7 scope is now 13 files. |
| MAJOR-1 — `--verify` accepts non-allowlisted/extra files and nested `SKILL.md` | **PARTIALLY RESOLVED** | The named `extra.md`, `nested/SKILL.md` and `examples/tool.py` cases now raise `PackageError`, and the new test passes. However, the verifier still accepts hidden/dot-prefixed members (`examples/.notes.md`, `references/.secret.md`, `references/..md`) and duplicate `README.md` entries; see remaining finding R-1. |
| MAJOR-2 — builder follows symlinks outside root | **RESOLVED** | `collect_files` rejects symlinks and resolved paths outside the root; `test_builder_rejects_symlink_outside_root` passes. A crafted ZIP symlink member with mode `120644` is rejected by `verify_package` with `Symlink ZIP member is not allowed`. |
| MAJOR-3 — fact-checking copy overclaims quote presence | **RESOLVED** | Package wording now consistently says default `validate.py` is metadata-only (status/URL shape/quote length), quote presence requires `factcheck.py --fetch-sources`, and neither mode proves truth. No remaining package occurrence of the old overclaim was found. |
| MAJOR-4 — README falsely says examples are free of unverified factual claims | **RESOLVED** | `README.md:84-86` now says the examples contain no claim objects and assert no `verified` status, and that statements are user-provided/general knowledge. English and Chinese QA examples explicitly say an empty claims array is not verification; the QA checklist and tests were updated. |
| MINOR-1 — `claim_id` existence overstatement | **RESOLVED** | `scene-contract-lite.md:258-259` now limits the existence rule to `claim_id`s listed by `factual: true` scenes. |
| MINOR-2 — integer `columns` omission/crash | **RESOLVED** | `scene-contract-lite.md:173-176` now says the array form is required for tables and explicitly warns that integer `columns` raises `TypeError` in `scripts/validate.py`. |
| MINOR-3 — URL prefix bypass | **RESOLVED** | `is_allowed_url` now parses the URL, requires exact host `github.com` and path `/huangyong7878/mg-animation-skill` (or a path below it), rejects credentials/ports, and the lookalike-domain test passes. |
| MINOR-4 — A1 caveat understates snapshot diff | **UNRESOLVED** | The caveat still claims two differences and says reference text/safety rules are unchanged; see remaining finding R-2. |

### Remaining finding R-1 (MAJOR, residual of MAJOR-1) — verifier still accepts hidden/dot and duplicate ZIP members

**Files/lines**

- `scripts/package_agensi_free.py:36-38` — `ALLOWED_NAME_RE` uses
  `[A-Za-z0-9._-]+`, which accepts leading-dot names such as
  `examples/.notes.md` and `references/.secret.md`.
- `scripts/package_agensi_free.py:141-142` — the builder separately rejects
  hidden files (`any(part.startswith(".") ...)`).
- `scripts/package_agensi_free.py:288-312` — `verify_package` applies only
  `ALLOWED_NAME_RE`; it has no hidden/dot-part check.
- `scripts/package_agensi_free.py:313-319` — manifest file lists are converted
  to a dict, and `file_count`/`total_bytes` use the ZIP names and decompressed
  bytes; duplicate names are not rejected.
- `tests/test_agensi_free.py:124-138` — the new negative test covers
  `extra.md`, `nested/SKILL.md` and `examples/tool.py`, but not hidden/dot or
  duplicate members.

**Concrete failure scenario**

I built crafted ZIPs with matching manifests and ran
`pkg.verify_package(...)`:

```text
hidden_ref_sorted       PASS (unexpected)
hidden_example_sorted   PASS (unexpected)
dotdot_ref_sorted       PASS (unexpected)
duplicate_readme        PASS (unexpected)
```

`examples/.notes.md` and `references/.secret.md` are unrelated files that the
builder rejects:

```text
builder REJECTED: Hidden file is not allowed: examples/.notes.md
```

so the verifier currently attests to a package the builder would never produce.
The duplicate `README.md` case is a malformed file list that is also not
rejected. This is the same verifier-integrity class as the original MAJOR-1.

**Suggested fix**

- Reject any ZIP member with a path component beginning with `.`.
- Reject duplicate `namelist()` entries, and require the manifest file-list
  length to equal `file_count` and the number of unique ZIP names.
- Add negative tests for `examples/.notes.md`, `references/..md` and a
  duplicate `README.md`.
- Optionally share one path-validation function between `collect_files` and
  `verify_package` so builder and verifier cannot drift.

### Remaining finding R-2 (MINOR, original MINOR-4) — A1 caveat is still inaccurate

**Files/lines**

- `docs/distribution/agensi-free-evidence/a1-a5/README.md:61-66` — says the
  snapshot differs from the final package "in two places" and that
  "workflow, reference text and safety rules are unchanged."
- `docs/distribution/agensi-free-evidence/a1-a5/skill-snapshot/SKILL.md` vs
  `distributions/agensi-free/SKILL.md` — the diff includes the description,
  an added "Use this skill when..." paragraph, and changes in the claim gate,
  self-check and factual-integrity sections.
- `skill-snapshot/references/scene-contract-lite.md` vs
  final `references/scene-contract-lite.md` — integer `columns` warning,
  `claim_id` scope and metadata-gate paragraph changed.
- `skill-snapshot/references/safety-and-limitations.md` vs final — default
  metadata gate and "real evidence" wording changed.
- `skill-snapshot/references/output-and-qa.md` vs final — Facts/provenance
  checklist changed.
- `skill-snapshot/README.md` vs final `README.md` — QA-note filenames and the
  examples paragraph changed.

**Concrete failure scenario**

The caveat says only two differences exist and explicitly denies reference-text
and safety-rule changes. `diff -u` on the five snapshot files shows changes in
all three reference documents and in the SKILL body, not just the description
and README file list. The A1 evidence is therefore historical rather than a
run of the delivered wording; the caveat should say so accurately.

**Suggested fix**

Regenerate the A1 snapshot from the final package and re-run the isolated
checks, or update the caveat to enumerate the changed files/sections and state
that the final reference wording (including the metadata-only claim wording) was
not exercised in A1.

### Additional evidence issue (MINOR, not one of the original 9) — A11 evidence artifact is the pre-fix review

`docs/distribution/agensi-free-evidence/a11-independent-review.md:10` still says
`NEEDS WORK`; lines 387, 394-396 cite the stale `b47f3c...`/`a3f271...` ZIPs;
line 351 says 218 tests. If this file is intended as the current A11 evidence,
it is stale and contradicts the current `911a841...`/225-test state. Either
replace it with this recheck or clearly label it as historical.

## Commands run and results

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_agensi_free.py -q
34 passed in 1.22s

$ PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
Ran 225 tests in 2.223s
FAILED (failures=1, skipped=1)
FAIL: test_valid_contract_passes_caption_timings_to_renderer
AssertionError: '/private/tmp/.../timings.json' != '/tmp/.../timings.json'
(matches the pre-existing macOS path-normalization failure)

$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/package_agensi_free.py --out-dir /tmp/claude-501/a11-recheck-pkg/out
SHA256 911a841b9c239d5066d8737e74ac44591cfeb354d030fa3504f33beeb2122b84
FILES 13 | BYTES 67610
PASS: deterministic ZIP structure, manifest and safety scan

$ cmp -s fresh.manifest.json docs/distribution/agensi-free-evidence/a6-manifest.json
a6_manifest_cmp=0
$ cmp -s fresh.manifest.json distributions/agensi-free/dist/agensi-free-1.0.0.manifest.json
dist_manifest_cmp=0

$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/package_agensi_free.py --verify distributions/agensi-free/dist/agensi-free-1.0.0.zip
PASS: ... | sha256 911a841b9c239d5066d8737e74ac44591cfeb354d030fa3504f33beeb2122b84 | 13 files
exit=0

$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/package_agensi_free.py --scan-only
PASS: package scan (allowlist, secrets, commands, injection, paths, links)
exit=0

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

$ crafted ZIP verifier cases:
hidden_ref_sorted       PASS (unexpected)
hidden_example_sorted   PASS (unexpected)
dotdot_ref_sorted       PASS (unexpected)
duplicate_readme        PASS (unexpected)
symlink_nonexec         REJECTED: Symlink ZIP member is not allowed: examples/link.md

$ builder with examples/.notes.md
builder REJECTED: Hidden file is not allowed: examples/.notes.md

$ diff -u A1 snapshot vs final package
changes in SKILL.md, README.md, references/scene-contract-lite.md,
references/safety-and-limitations.md and references/output-and-qa.md
```

## Gate impact

- A1: PASS for the run artifacts; caveat remains inaccurate (R-2).
- A2: PASS — examples and 34 Agensi tests pass.
- A3/A4/A5: no regression found in this recheck; earlier PASS evidence remains.
- A6: PASS for the artifact/manifest/reproducibility; verifier residual R-1
  remains.
- A7: PASS for the package scan and 13-file manual-review scope.
- A8: PASS; license audit unchanged and still marks distribution BLOCKED.
- A9: PASS; listing fact-check wording is now corrected.
- A10: PASS; 225 tests with the same documented path-normalization failure.
- A11: PENDING owner approval; the repository-side A11 evidence file is stale
  and should be replaced or labelled historical.

No repository file was modified during this recheck.
