# A11 Independent Technical Review (round 1) — Agensi Free Edition Distribution Adapter

> **HISTORICAL reviewer snapshot (round 1).** This is the reviewer's original
> report on the initial implementation. Its findings were fixed and rechecked;
> see `a11-resolution.md` for the current status and the later round reports.
> The hashes and test counts in this file describe the pre-fix tree only.

- Repository: `/Users/yonghuang/Codes/mg-animation-skill`
- Branch: `docs/agensi-free-agent-b-20261031`
- Reviewed commit state: `1e86595` plus uncommitted/untracked implementation files
- Spec: `docs/distribution/agensi-free-agent-b-spec.md`
- Reviewer: independent review agent (fresh context; did not author the implementation)
- Date: 2026-11-01

## Verdict: NEEDS WORK

The core text-only skill is substantially good: both example Scene JSON files
pass the real `scripts/validate.py`, the negative tests really exercise the
legacy validator, the packaged text is free of secrets/executables, the
optional-render boundary is usually stated honestly, the license audit correctly
finds no `LICENSE`, and A10's disclosed test failure is reproducible.

Release is nevertheless blocked by packaging/evidence defects: the A6/A7
evidence and the local `dist` ZIP are stale relative to the reviewed source,
the shipped ZIP does not contain the QA-note examples that the packaged README
declares, and the verifier can be fooled into passing a package with extra or
nested `SKILL.md` files. There are also concrete overclaims about what the
legacy fact checker verifies.

## Finding counts

- BLOCKER: 1
- MAJOR: 4
- MINOR: 4

## Findings

### BLOCKER-1 — A6/A7 evidence and the distributed ZIP do not match the reviewed source

**Files/lines**

- `docs/distribution/agensi-free-evidence/a6-package-build.txt:1-6` — claims
  `SHA256 a3f271541fda1a6b859bb4cb9cb23588c945e6d9001d40b1d5ace8050a01eba5`,
  `FILES 11 | BYTES 59899`.
- `docs/distribution/agensi-free-evidence/a6-manifest.json:4-6` — same
  `a3f271...` SHA, `file_count: 11`, `total_bytes: 59899`.
- `docs/distribution/agensi-free-evidence/a6-zip.sha256:1` — same `a3f271...`.
- `distributions/agensi-free/dist/agensi-free-1.0.0.manifest.json:4-6` — a
  different SHA (`b47f3c7f578a...`), `file_count: 11`, `total_bytes: 59893`.
- `distributions/agensi-free/dist/agensi-free-1.0.0.zip.sha256` — `b47f3c...`.
- `distributions/agensi-free/README.md:31-41` — declares
  `examples/qa_notes_en.md` and `examples/qa_notes_zh.md` as package files.
- `docs/distribution/agensi-free-evidence/a7-manual-review.md:4,38` — says the
  review scope is "the 11 files ... six examples", which is already stale.

**Concrete failure scenario**

Running the documented packaging command against the reviewed tree produces a
different package from both the evidence and the checked-in local ZIP:

```text
$ python3 scripts/package_agensi_free.py --out-dir <tmp>
SHA256 cb0be05092a2a362d3f3939fe8ae25b60ba84627d694f5ea9d35e04acc02ed24
FILES 13 | BYTES 65133
```

but the local artifact is 11 files / 59,893 bytes / SHA `b47f3c...`, and the
A6 evidence is 11 files / 59,899 bytes / SHA `a3f271...`. `unzip -l` on the
local artifact lists 11 files and omits both `examples/qa_notes_*.md`, so a
consumer who receives that ZIP gets neither the files nor the package layout
that `README.md` promises. Conversely, the committed A6 evidence cannot be
reproduced from the PR because `dist/` is gitignored and the source has moved on
(current source `SKILL.md` is 11,457 bytes and `README.md` 3,865 bytes, versus
11,428 and 3,817 in the A6 evidence, plus two new examples).

**Why this is a BLOCKER**

A6 explicitly requires a reproducible build, a file list and a matching SHA256.
The evidence currently asserts PASS for a build that is not the reviewed build,
and the artifact that does exist contradicts the packaged README. A1/A7 evidence
also references the stale 11-file package. No A6 PASS can be defended until the
artifact and evidence are regenerated from the final tree.

**Suggested fix**

1. Rebuild `dist/agensi-free-1.0.0.zip`, its manifest and sidecar from the final
   source and replace the `a6-*` evidence with the new hashes/file list.
2. Re-run the A7 review against the 13-file package (including the QA-note
   examples) and update its scope statement.
3. Add a regression test that builds the package and asserts that the build
   SHA/file list matches the evidence and the README package layout. The current
   tests only compare two fresh builds to each other; they never compare against
   `dist/` or the evidence, so the stale artifact passes.
4. If the local ZIP is intentionally not part of the PR, delete it from the
   review tree and mark A6 NOT RUN rather than presenting stale evidence.

### MAJOR-1 — `--verify` accepts non-allowlisted files and a second nested `SKILL.md`

**Files/lines**

- `scripts/package_agensi_free.py:26-32` — the real allowlist (`SKILL.md`,
  `README.md`, `references/*.md`, `examples/*.md`, `examples/*.json`).
- `scripts/package_agensi_free.py:228-278` — `verify_package` checks manifest
  hashes and path traversal, but never applies `ALLOWED_PATTERNS`.
- `scripts/package_agensi_free.py:249-250` — only counts exact `"SKILL.md"`
  names, so `nested/SKILL.md` is invisible to the check.
- `scripts/package_agensi_free.py:34-35` — `MAX_FILES` / `MAX_TOTAL_BYTES`
  are enforced for builds but not for verification.

**Concrete failure scenario**

I built two hand-crafted ZIPs with matching manifests:

1. Root `SKILL.md` plus `extra.md`; `python3 scripts/package_agensi_free.py
   --verify <zip>` printed
   `PASS: ... | 2 files`, exit 0.
2. Root `SKILL.md` plus `nested/SKILL.md`; the verifier also printed
   `PASS: ... | 2 files`, exit 0.

This directly contradicts A6's requirements ("only one SKILL.md", allowlisted
contents). A verifier that is supposed to attest package integrity can be
tricked into attesting to a package the builder would never produce.

**Suggested fix**

- Reject any ZIP member that does not match the allowlist patterns.
- Reject any member whose basename is `SKILL.md` unless the member is exactly
  `SKILL.md`.
- Enforce `MAX_FILES`, `MAX_TOTAL_BYTES` and (optionally) `MAX_TOTAL_CHARS` in
  `verify_package`.
- Add negative tests that craft a ZIP with an extra allowlisted-looking file and
  with `nested/SKILL.md` and assert `PackageError`.

### MAJOR-2 — The builder follows symlinks out of the package root

**Files/lines**

- `scripts/package_agensi_free.py:99-114` — `collect_files` uses
  `path.is_file()` (which follows symlinks) and only validates the lexical
  relative path.

**Concrete failure scenario**

I created a temporary package root with a valid `SKILL.md` and a symlink
`examples/leak.md -> $TMPDIR/secret.md`. Running:

```text
python3 scripts/package_agensi_free.py --package-root <pkg> --out-dir <out>
```

produced a ZIP containing `examples/leak.md` whose contents were the external
file's contents (`OUTSIDE_SECRET_TEXT`), and the safety scan still printed
`PASS`. A committed or planted symlink would therefore let the builder silently
package arbitrary readable local text. The current package has no symlinks, but
the tool is a supply-chain boundary and should fail closed.

**Suggested fix**

- Reject `path.is_symlink()` in `collect_files`, or require
  `path.resolve().is_relative_to(package_root.resolve())`.
- Add a regression test with a symlink pointing outside the package root.

### MAJOR-3 — Fact-checking copy overclaims quote presence

**Files/lines**

- `distributions/agensi-free/SKILL.md:164-165` — "The legacy `factcheck.py`
  checks provenance and quote presence."
- `distributions/agensi-free/SKILL.md:125-127` — claims must be "`verified`
  with real evidence before the legacy validator accepts it."
- `distributions/agensi-free/LISTING.md:125-126` — "The legacy `factcheck.py`
  checks provenance and quote presence, not truth."
- `distributions/agensi-free/references/safety-and-limitations.md:75-80` —
  "The legacy fetch check only proves that a quote appears on a page" and "the
  legacy validator rejects any claim that is not `verified` with real evidence."
- `scripts/validate.py:51-52` — the actual default call is
  `check_claims(data, fetch=False)`.
- `scripts/factcheck.py:39-53` — with `fetch=False` the check only verifies
  status, non-empty evidence, URL shape (`^https?://...`) and a quote of at
  least 8 characters. The quote-presence/network branch starts only at line 54
  (`if fetch and ...`).

**Concrete failure scenario**

A fabricated claim with `status: "verified"`, URL `https://example.org/source`
and an arbitrary 8-character quote passes `scripts/validate.py`. This is
exactly what `tests/test_agensi_free.py:301-318`
(`test_verified_claim_with_evidence_passes`) demonstrates. The package tells a
user that the legacy checker verifies quote presence and that "real evidence"
is required by the validator; in the default path it verifies neither. A user
could therefore treat a validated JSON as having had its source quotes checked.

**Suggested fix**

Qualify every statement: the default gate checks provenance metadata only
(status, URL shape, quote length); quote presence requires
`--fetch-sources`; neither mode proves truth. Update `SKILL.md`, `LISTING.md`,
`safety-and-limitations.md` and the QA checklist accordingly, and consider
adding `--fetch-sources` guidance for users who actually want quote presence.

### MAJOR-4 — README says the examples are free of unverified factual claims; they are not claim-registered

**Files/lines**

- `distributions/agensi-free/README.md:82-84` — "Both JSON documents are
  written against the real v2.1 contract and are kept free of unverified
  factual claims."
- `distributions/agensi-free/examples/scene_en.json:80` — on-screen text
  "A member sponsors the bill and introduces it in one chamber."
- `distributions/agensi-free/examples/scene_en.json:161` — "A veto override
  requires two-thirds in both chambers."
- `distributions/agensi-free/examples/scene_en.json:191` — `"claims": []`;
  scenes are not `factual: true`.
- `distributions/agensi-free/examples/scene_zh.json:80,160,174-186,190` —
  factual photosynthesis statements and narration with `"claims": []`.
- `distributions/agensi-free/references/output-and-qa.md:161` — checklist says
  "Every factual on-screen statement is in the claims register."
- `scripts/factcheck.py:66-71` — the claim gate only inspects scenes with
  `factual: true`; an empty `claims` array is accepted.

**Concrete failure scenario**

The examples contain factual on-screen statements but bypass the fail-closed
claim gate by using `claims: []` and omitting `factual: true`. The validator
passes, so an agent can copy the pattern and emit unverified factual statements
without claim objects. The packaged README's statement that the documents are
"kept free of unverified factual claims" is false in the ordinary reading. The
example QA notes do say the content is user-provided/unverified, which mitigates
the problem, but the README and the checklist still overstate what the JSON
represents.

**Suggested fix**

- Change the README to "contain no claim objects and assert no `verified`
  status" rather than "free of unverified factual claims."
- Add an explicit skill rule: any on-screen factual statement must be either
  represented in `claims` (and therefore fail 2.1 validation while unverified)
  or explicitly labelled in QA as user-provided/general knowledge.
- Update the example QA notes/claims registers to match the rule, and add a test
  that checks examples do not silently mix factual text with an empty claims
  array (or document the intended exception).

### MINOR-1 — `scene-contract-lite.md` overstates the `claim_id` existence check

**Files/lines**

- `distributions/agensi-free/references/scene-contract-lite.md:255-256` —
  "every listed `claim_id` must exist."
- `scripts/factcheck.py:66-71` — only scenes with `factual: true` are checked;
  a non-factual scene with `claim_ids: ["missing"]` passes.

**Concrete failure scenario**

A writer puts a dangling `claim_id` on a non-factual scene; the legacy validator
accepts it even though the compact contract says every listed claim_id must
exist. This is a documentation/validator mismatch.

**Suggested fix**

Say "every `claim_id` listed by a `factual: true` scene must exist", or add a
validator check for all claim_ids (core change requires owner approval).

### MINOR-2 — Lite contract omits the schema-legal integer `columns` form; the validator crashes on it

**Files/lines**

- `distributions/agensi-free/references/scene-contract-lite.md:173-181` — says
  `columns` is an array and its length is the column count.
- `references/scene.schema.json:304-318` — `columns` is `oneOf` an integer
  `>= 1` or an array of cells.
- `scripts/engine.py:90-92` — `table_dimensions` calls
  `len(node.get('columns', []))`.
- `scripts/validate.py:31` — calls `table_dimensions` for every table.

**Concrete failure scenario**

A schema-reading user writes `"columns": 2` (schema-legal). Running
`python3 scripts/validate.py` produces an uncaught
`TypeError: object of type 'int' has no len()` traceback, exit 1, rather than a
clean validation error. The compact contract never warns that the integer form
is unsupported by the current validator.

**Suggested fix**

Document that only the array form is supported, and/or add a defensive guard in
`table_dimensions`/`validate.py` (owner approval required for core changes).
Add a regression test if the validator is fixed.

### MINOR-3 — URL allowlist uses a bare prefix match

**Files/lines**

- `scripts/package_agensi_free.py:38-40` — `ALLOWED_URL_PREFIXES =
  ("https://github.com/huangyong7878/mg-animation-skill",)`.
- `scripts/package_agensi_free.py:160-162` — checks
  `url.startswith(ALLOWED_URL_PREFIXES)`.

**Concrete failure scenario**

`https://github.com/huangyong7878/mg-animation-skill.evil.com` starts with the
allowed prefix and is not reported as a non-allowlisted external URL. The scan
would therefore pass a package containing a lookalike domain. The current
package has no such URL, but the scan claims to enforce a URL allowlist and does
not enforce host boundaries.

**Suggested fix**

Parse URLs and require the exact host `github.com` plus a path of
`/huangyong7878/mg-animation-skill` followed by `/` or end-of-string.

### MINOR-4 — A1 isolation evidence is against a stale snapshot and the caveat understates the diff

**Files/lines**

- `docs/distribution/agensi-free-evidence/a1-a5/README.md:61-63` — says the
  snapshot "predates two non-behavioral wording edits to the frontmatter
  description."
- `docs/distribution/agensi-free-evidence/a1-a5/skill-snapshot/SKILL.md:4` vs
  `distributions/agensi-free/SKILL.md:4` — description changed from "a valid MG
  Animation Scene JSON v2.1 document" to "an MG Animation Scene JSON v2.1
  document written against the real contract."
- `docs/distribution/agensi-free-evidence/a1-a5/skill-snapshot/README.md` vs
  `distributions/agensi-free/README.md` — the final README lists two additional
  QA-note example files (which are also absent from the snapshot's example
  inventory).

**Concrete failure scenario**

A1 is evidence for an earlier skill snapshot, not the delivered package. The
outputs still appear sound, and the caveat discloses that the snapshot predates
edits, but the number/nature of edits is inaccurate: it is one description
change plus README package-list changes, not "two ... frontmatter description"
edits. The final description (the honesty-improved wording) was never the one
exercised in A1.

**Suggested fix**

Regenerate the snapshot from the final package and re-run the isolated checks,
or update the caveat to enumerate the actual differences and state that final
SKILL.md/README wording was not exercised in A1. (A7's stale "11 files" scope is
covered in BLOCKER-1.)

## A1–A11 status

| Gate | Status | Justification |
|---|---|---|
| A1 | PASS (with caveat) | Two simulated isolated runs, briefs, process logs, storyboards, JSON, and QA notes are present; both A1 JSONs pass `scripts/validate.py` (24 s and 20 s). Caveat: snapshot predates final description/README edits and live Agensi loading was not tested. |
| A2 | PASS | Both packaged examples validate with the real `scripts/validate.py` (exit 0; recorded below). Negative tests genuinely fail on syntax errors, missing fields, illegal node type/scene duration, and table row mismatch; 27/27 Agensi tests pass. |
| A3 | PASS (with caveat) | Real `pipeline.py` output is 24.0 s, 960x540 H.264 video + AAC audio; ffprobe and SRT/timings match. Caveat: exact eSpeak path is NOT RUN; the evidence uses a temporary macOS `say` shim named `espeak`, which the A3 evidence discloses. |
| A4 | PASS | Isolated runs had no terminal/Python/FFmpeg/TTS/repo, produced all three text deliverables, and explicitly state no MP4/audio/SRT exists; zero media files in the A1/A4/A5 evidence directory. |
| A5 | PASS (with caveat) | Both briefs' uncited claims are labelled, omitted from on-screen/narration/JSON, and no URL/quote/`verified` flag was fabricated; claims arrays are empty. Caveat: the package's fact-checking wording overclaims quote-presence checking (MAJOR-3). |
| A6 | FAIL | A6 evidence/artifact is stale: fresh build is 13 files/65,133 bytes/SHA `cb0be050...`, local ZIP is 11/59,893/`b47f3c...`, A6 evidence is 11/59,899/`a3f271...`. The verifier also accepts non-allowlisted files and a nested `SKILL.md`, and the builder follows symlinks outside the package root. |
| A7 | PASS (with caveat) | The packaged text scan is clean and the manual review covers secrets, injection, network, command and executable-content boundaries. Caveat: the review scope is the stale 11-file package (current build has 13 files), and the URL-prefix allowlist has a bypass (MINOR-3). |
| A8 | PASS | `git ls-tree` confirms no `LICENSE`/`LICENSE.md` at HEAD; the audit records options without selecting a license, states default copyright, and marks distribution BLOCKED pending owner approval. |
| A9 | PASS (with caveat) | Listing copy avoids default-MP4, real-TTS, auto-install, interactive-canvas, automatic-fact-check and approval guarantees, and discloses local-render prerequisites. Caveat: packaged README/example claims are inaccurate (MAJOR-4); listing's "claim gate" wording should be qualified alongside MAJOR-3. |
| A10 | PASS | Full suite independently reproduced: 218 tests, 1 failure, 1 skip; the failure is the existing `/tmp` vs `/private/tmp` path-normalization issue in `test_auto_pipeline_contract.py:74`, matching the A10 baseline note. `git status --porcelain` shows no core renderer, R0–R7, schema, private-project or PR #38/#39 file modified. |
| A11 | PENDING | Independent technical review is completed by this report, but owner approval of license, merge, upload and release remains outstanding; the PR must stay Draft. No repository-side HANDOFF/A1–A11 status table was found, so the status table in this report is reconstructed from evidence rather than from the author's handoff. |

## Commands run and exact results

All commands were run read-only against the repository, except for temporary
output directories under `$TMPDIR`. No repository file was modified.

```text
$ git status --porcelain
 M .gitignore
?? distributions/
?? docs/distribution/agensi-free-evidence/
?? docs/distribution/agensi-free-license-audit.md
?? scripts/package_agensi_free.py
?? tests/test_agensi_free.py

$ python3 scripts/validate.py distributions/agensi-free/examples/scene_en.json
OK: ... | 3 scene(s) | 960x540 | duration 24.0s
exit=0
$ python3 scripts/validate.py distributions/agensi-free/examples/scene_zh.json
OK: ... | 3 scene(s) | 960x540 | duration 24.0s
exit=0

$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_agensi_free.py -q
27 passed in 1.46s

$ python3 scripts/package_agensi_free.py --out-dir <fresh-temp>
BUILT .../agensi-free-1.0.0.zip
SHA256 cb0be05092a2a362d3f3939fe8ae25b60ba84627d694f5ea9d35e04acc02ed24
FILES 13 | BYTES 65133
PASS: deterministic ZIP structure, manifest and safety scan
exit=0

$ unzip -l distributions/agensi-free/dist/agensi-free-1.0.0.zip
11 files; no examples/qa_notes_en.md or examples/qa_notes_zh.md
SHA256 of that ZIP: b47f3c7f578a12d8ea0851f037c671c6190fbc97948dd4a45c6c35130c66125e

$ python3 scripts/package_agensi_free.py --verify distributions/agensi-free/dist/agensi-free-1.0.0.zip
PASS: ... | sha256 b47f3c... | 11 files
exit=0

$ A6 evidence a6-manifest.json sha256
a3f271541fda1a6b859bb4cb9cb23588c945e6d9001d40b1d5ace8050a01eba5
actual shipped ZIP sha256
b47f3c7f578a12d8ea0851f037c671c6190fbc97948dd4a45c6c35130c66125e
=> evidence does not match the local artifact

$ crafted ZIP: SKILL.md + extra.md with matching manifest
python3 scripts/package_agensi_free.py --verify <zip>
PASS: ... | 2 files
exit=0

$ crafted ZIP: SKILL.md + nested/SKILL.md with matching manifest
python3 scripts/package_agensi_free.py --verify <zip>
PASS: ... | 2 files
exit=0

$ symlink test: examples/leak.md -> $TMPDIR/secret.md
python3 scripts/package_agensi_free.py --package-root <tmp-pkg> --out-dir <tmp-out>
BUILT ...
PASS: deterministic ZIP structure, manifest and safety scan
unzip -p ... examples/leak.md
OUTSIDE_SECRET_TEXT

$ python3 scripts/validate.py docs/distribution/agensi-free-evidence/a1-a5/en/scene_en.json
OK: ... | 3 scene(s) | 960x540 | duration 24.0s
exit=0
$ python3 scripts/validate.py docs/distribution/agensi-free-evidence/a1-a5/zh/scene_zh.json
OK: ... | 3 scene(s) | 960x540 | duration 20.0s
exit=0
$ find docs/distribution/agensi-free-evidence/a1-a5 -type f \
    \( -name '*.mp4' -o -name '*.wav' -o -name '*.srt' -o -name '*.png' \) | wc -l
0

$ ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,duration \
    -show_entries format=duration,size -of json \
    distributions/agensi-free/dist/render-en/scene_en.mp4
video h264 960x540 duration 24.000000
audio aac duration 24.000000
format duration 24.000000, size 790937
(shasum matches evidence: 3ba2a50051f8f8bb1880920be6f9a85f4eeea4450646b15ab9b41d1e1ef82075)

$ python3 -m unittest discover -s tests
Ran 218 tests in 3.102s
FAILED (failures=1, skipped=1)
Failure: test_valid_contract_passes_caption_timings_to_renderer
(assertion `/private/tmp/...` != `/tmp/...`), matching A10 evidence.

$ git ls-tree -r HEAD --name-only | grep -iE '(^|/)licen[cs]e'
(no output; exit 1)

$ python3 scripts/validate.py <scene with "columns": 2>
Traceback ... TypeError: object of type 'int' has no len()
exit=1

$ Appendix A skeleton extracted from SKILL.md and validated
OK: ... | 2 scene(s) | 960x540 | duration 12.0s
exit=0
```

## Scope check

`git status --porcelain` shows only `.gitignore` modified and new untracked
distribution/evidence/tooling files. No core renderer (`scripts/engine.py`,
`scripts/pipeline.py`, `scripts/render.py`, `scripts/narrate.py`), R0–R7 gate,
`references/scene.schema.json`, private-project file, PR #38/#39 file, or
production artifact was modified. The `.gitignore` addition correctly excludes
`distributions/agensi-free/dist/` so the ZIP and render artifacts are not
committed; however, that also means the A3/A6 artifacts cited by evidence are
not present in the PR, which is a caveat on independent verification.

## Items checked and found correct

- Both packaged example JSONs pass the real legacy validator; no invented fields
  were found in the examples or in Appendix A.
- The compact contract's core field list, timing rule, animation/transition
  enums, geometry percent syntax, narration anchors, and claim-gate description
  match the schema/validator, apart from the MINOR items above.
- The negative tests actually invoke `scripts/validate.py` and detect syntax
  errors, missing required fields, illegal scene/type/duration, table row
  mismatch, and an unverified 2.1 claim.
- The ZIP from a fresh build is text-only, has a root `SKILL.md`, one skill,
  deterministic timestamp/permissions, no executable bits, no nested ZIP or
  binary, and per-file SHA256 values.
- The packaged text scan finds no secrets, dangerous commands, injection
  patterns, absolute paths, or hidden/bidi characters in the current source.
- The license audit's no-`LICENSE` finding is correct and it explicitly avoids
  choosing a license.
- The A1/A4/A5 evidence files support the claimed statuses, with the caveats
  noted above.

## Release decision

Do not mark A6 PASS or submit/upload the package. Regenerate the package and
A6/A7 evidence from the final tree, fix the verifier and symlink handling, and
correct the fact-checking and example-claim wording. A11 remains a pending owner
decision.
