# Agensi Free Edition — A1–A11 Acceptance and Handoff

Status date: 2026-11-01 · Implementer: Agent B (AI role)
Issue: #40 · Draft PR: #41 · Branch: `docs/agensi-free-agent-b-20261031`
Implementation commit: `a3495512d8f05576bd1ebab11a8e539cfc7cad82`
Evidence commit: the branch-tip commit containing this file
Package: `agensi-free-1.0.0.zip` · SHA256
`911a841b9c239d5066d8737e74ac44591cfeb354d030fa3504f33beeb2122b84` ·
13 files · 67,610 bytes

## Acceptance table

| Gate | Status | Evidence |
|---|---|---|
| A1 — isolated agent loading, EN + ZH | PASS (with caveat) | `a1-a5/README.md`, `a1-a5/en/`, `a1-a5/zh/`, `a1-a5/setup.txt`. Two fresh agents with only the final skill snapshot + a new brief produced storyboard, JSON and QA notes; read paths recorded; both JSONs pass the real validator (`a1-a5/validation.txt`). Caveat: simulated Agensi host, not the live platform. |
| A2 — real v2.1 schema / validate.py | PASS | `a2-validation.txt`: both packaged examples exit 0 under `scripts/validate.py`; 36 tests include JSON syntax, missing-field, illegal-scene, table-shape and unverified-claim failures. |
| A3 — actual MP4 + audio smoke test | PASS (substituted offline TTS; eSpeak path NOT RUN) | `a3-render.txt`, `a3-timings.json`, `a3-captions.srt`: 24 s 960×540 H.264 + AAC MP4, verified by `ffprobe`; narration 0.50–20.78 s inside the 24 s canvas. eSpeak is not installed, so an evidence-only adapter backed by offline macOS `say` was used through the unmodified `pipeline.py`/`narrate.py`/`render.py`. |
| A4 — no-runtime fallback | PASS | `a1-a5/en/qa_notes_en.md`, `a1-a5/zh/qa_notes_zh.md`, process logs: no terminal, MP4, audio or SRT; no installs; text deliverables still produced. |
| A5 — fact/source handling | PASS (with caveat) | Both isolated runs omitted the unsourced claim, left `claims: []`, never used `verified`, and marked the draft not publishable as verified. `test_unverified_claim_is_fail_closed` proves the validator rejects unverified 2.1 claims. Caveat: default validation is metadata-only; the package now states that explicitly. |
| A6 — ZIP structure / manifest / SHA256 / reproducibility | PASS | `a6-package-build.txt`, `a6-manifest.json`, `a6-zip.sha256`: allowlist only, root `SKILL.md`, 13 text files, identical SHA on two builds, per-file hashes, no binaries/traversal/nesting/symlinks. `test_evidence_manifest_matches_fresh_build` and `test_readme_layout_matches_zip` guard against stale evidence. |
| A7 — permissions and security | PASS | `a7-security-scan.txt`, `a7-manual-review.md`: automated secret/command/injection/network/path/invisible-character scan, exact-host URL allowlist, symlink rejection and manual review; text path needs no shell; optional render needs approval. |
| A8 — copyright / license audit | PASS (audit) — distribution BLOCKED | `../agensi-free-license-audit.md`: no LICENSE in the repository; no third-party assets packaged; owner must choose terms before upload. No license was added. |
| A9 — listing accuracy | PASS | `../../distributions/agensi-free/LISTING.md`, `a9-listing-review.md`: FREE; text-only default; no MP4/auto-install/auto-fact-check/interactive-canvas promise; metadata-only claim gate; optional-render prerequisites disclosed. |
| A10 — regression and scope | PASS (1 pre-existing unrelated failure) | `a10-regression.txt`, `a10-full-log.txt`: 227 tests on this branch; clean `main` 10ae8a6 has 191 tests and the same single macOS `/var` symlink failure (`a10-baseline-main-full.log`); no core renderer, schema, R0–R7 gate, studio or PR #38/#39 file changed. |
| A11 — independent review / owner gates | PENDING OWNER APPROVAL | Current status: `a11-resolution.md`. Historical reviewer snapshots: `a11-independent-review.md` (round 1), `a11-recheck.md` (round 2), `a11-review-round3.md` (round 3), `a11-review-round4.md` (round 4). No merge, Agensi upload, payment setup or license selection was performed. |

## Reproduce

```bash
python3 scripts/package_agensi_free.py
python3 scripts/package_agensi_free.py --verify distributions/agensi-free/dist/agensi-free-1.0.0.zip
python3 scripts/validate.py distributions/agensi-free/examples/scene_en.json
python3 scripts/validate.py distributions/agensi-free/examples/scene_zh.json
python3 -m unittest discover -s tests -p 'test_agensi_free.py' -v
python3 -m unittest discover -s tests
```

The optional local render used an evidence-only `espeak` CLI adapter backed by
macOS `say`; exact eSpeak is not installed. See `a3-render.txt`.

## Known limitations and blockers

- **A8 distribution is BLOCKED** pending the owner's license/terms decision.
  The repository has no `LICENSE` file; do not upload the package yet.
- **A11 owner approval is pending.** The PR must stay Draft. No merge,
  Agensi upload, payment configuration or paid service was performed.
- A3 used offline macOS `say`, not eSpeak. The exact eSpeak path is NOT RUN.
- The A1 runs are simulated Agensi-style hosts, not the live platform.
- One pre-existing test failure (`/var` vs `/private/var`) is unrelated to
  this PR and reproduces on clean `main`.
- The CLAIM comment for Issue #40 was prepared but not posted; the local
  permission classifier blocked it. See `claim.md`.

## Owner decisions required

1. License and redistribution terms (A8).
2. Review and approve the Draft PR (A11).
3. Post the prepared CLAIM on Issue #40 if the process requires it.
4. Decide whether to submit to Agensi after the above; this task did not
   upload anything.
