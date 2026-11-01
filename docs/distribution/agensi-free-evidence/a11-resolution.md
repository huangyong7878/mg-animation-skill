# A11 — Independent Review Resolution

**Current status: this file.** The independent reviewer reports are historical
snapshots of the tree at their own dates:

| Round | Historical report | Snapshot |
|---|---|---|
| 1 | `a11-independent-review.md` | Original review: 1 blocker, 4 major, 4 minor |
| 2 | `a11-recheck.md` | Verified fixes; found R-1/R-2 and the stale round-1 label |
| 3 | `a11-review-round3.md` | Verified R-1/R-2; found F-1/F-2 |
| 4 | `a11-review-round4.md` | Verified F-1; F-2 addressed by historical labeling |

None of the round reports is the current state. Their findings and the fixes
are tracked below; the acceptance `README.md` and `HANDOFF.md` point here for
the current status. Final state date: 2026-11-02.

## Resolution summary

| Finding | Status | Resolution |
|---|---|---|
| BLOCKER-1 — stale A6/A7 evidence and ZIP | RESOLVED | Final package rebuilt from the final tree: 13 files, 67,610 bytes, SHA256 `911a841b9c239d5066d8737e74ac44591cfeb354d030fa3504f33beeb2122b84`. A6 manifest/sidecar and A2/A7/A10 evidence regenerated. New tests `test_evidence_manifest_matches_fresh_build` and `test_readme_layout_matches_zip` fail if evidence or README layout drifts from the source. |
| MAJOR-1 — verifier accepts non-allowlisted/extra/nested members | RESOLVED | One shared `member_name_issues` function now drives both builder and verifier: allowlist, hidden/dot components, path traversal, nested `SKILL.md`, text suffix. The verifier also rejects duplicate ZIP names, duplicate manifest paths, manifest length/count mismatches and enforces MAX_FILES/bytes/chars. Tests cover `extra.md`, `nested/SKILL.md`, `examples/tool.py`, `examples/.notes.md`, `references/.secret.md`, `references/..md` and duplicate `README.md`. |
| MAJOR-2 — builder follows symlinks outside root | RESOLVED | `collect_files` rejects symlinks and any resolved path outside the root; `verify_package` rejects symlink ZIP members. Test `test_builder_rejects_symlink_outside_root` passes. |
| MAJOR-3 — fact-checking copy overclaims quote presence | RESOLVED | All packaged copy now states: default `validate.py` is metadata-only (status, URL shape, quote length); quote presence requires `factcheck.py --fetch-sources`; neither proves truth. Updated in `SKILL.md`, `LISTING.md`, `safety-and-limitations.md`, `scene-contract-lite.md` and `output-and-qa.md`. |
| MAJOR-4 — README says examples are free of unverified claims | RESOLVED | README now says the examples contain no claim objects and assert no `verified` status; statements are user-provided general knowledge. Both QA examples say an empty `claims` array is not verification. The QA checklist and tests were updated. |
| MINOR-1 — claim_id existence overstatement | RESOLVED | Contract now limits the existence rule to `claim_id`s listed by `factual: true` scenes. |
| MINOR-2 — integer `columns` crash undocumented | RESOLVED | Table section now requires the array form and warns that integer `columns` raises `TypeError` in the current table validator. |
| MINOR-3 — URL prefix bypass | RESOLVED | `is_allowed_url` parses the URL and requires exact host `github.com` and path `/huangyong7878/mg-animation-skill` (or below); credentials/ports rejected. Lookalike-domain test added. |
| MINOR-4 / recheck R-2 — A1 snapshot caveat | RESOLVED | A1 was re-run from the final package snapshot; `a1-a5/skill-snapshot/` is byte-identical to the packaged SKILL.md, README.md and three references, and the outputs were replaced. The final metadata-only claim-gate and empty-claims-array wording was exercised. |
| Recheck R-1 — hidden/duplicate verifier members | RESOLVED | Covered by the shared path validator and duplicate-name checks; negative tests added. |
| Evidence issue — stale `a11-independent-review.md` | RESOLVED | Every reviewer report is explicitly marked HISTORICAL as a numbered round; this file is the current state. |
| Recheck F-1 — stale test counts in acceptance/handoff | RESOLVED | Acceptance README and HANDOFF now say 36 Agensi tests and 227 full-suite tests; the clean-main baseline is stated separately as 191 tests (`a10-baseline-main-full.log`). |
| Recheck F-2 — stale reviewer report presented as current | RESOLVED | All reviewer reports are labeled historical snapshots; acceptance README and HANDOFF point to this resolution file as the current state, so no NEEDS WORK report is presented as final. |

## Final local verification

```text
$ python3 -m unittest discover -s tests -p 'test_agensi_free.py' -v
Ran 36 tests ... OK

$ python3 -m unittest discover -s tests
Ran 227 tests ... FAILED (failures=1, skipped=1)
```

The single failure is the pre-existing macOS `/var` vs `/private/var`
path-normalization failure in `test_auto_pipeline_contract.py`; it reproduces
on clean `main` 10ae8a6 (`a10-baseline-main.log`), where the full suite is
`Ran 191 tests ... FAILED (failures=1, skipped=1)`
(`a10-baseline-main-full.log`). It is unrelated to this PR.

## A11 status

**Independent review completed; owner approval remains PENDING.** No merge,
Agensi upload, payment configuration, paid service or license selection was
performed. A8 distribution remains BLOCKED until the owner chooses license and
redistribution terms.
