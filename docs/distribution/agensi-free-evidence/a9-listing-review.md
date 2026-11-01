# A9 — Listing Accuracy Review

Reviewer: Agent B (AI role) · Date: 2026-11-01
File reviewed: `distributions/agensi-free/LISTING.md`

## Claim-by-claim check

| Listing claim | Accurate? | Evidence |
|---|---|---|
| Free ($0) | Yes | No payment configuration or paid endpoint exists. |
| Produces storyboard, Scene JSON v2.1 and QA notes | Yes | `SKILL.md` defines all three; examples include all three. |
| Text-only by default | Yes | No runtime, network or TTS dependency in the text path. |
| No Python/FFmpeg/TTS needed for the free path | Yes | Read-only text generation. |
| JSON is written against the real v2.1 contract | Yes | Both example JSON files pass the real `scripts/validate.py`. |
| Does not render video by default | Yes | No renderer invocation in the default workflow. |
| Does not synthesize audio or burn subtitles in the free path | Yes | TTS and subtitle burn-in are only in the optional local path. |
| Does not install software / clone / call paid services | Yes | Explicit boundary in `SKILL.md` and safety reference. |
| Does not automatically fact-check | Yes | QA notes distinguish user-provided / verified / unverified. |
| Explains the claim gate accurately | Yes | LISTING FAQ says default validation is metadata-only; quote presence requires `--fetch-sources`; neither proves truth. |
| Not an interactive canvas or hosted service | Yes | No UI, server or deployment component. |
| Local render requires Python 3.10+, FFmpeg, TTS and approval | Yes | Documented in README and safety reference. |
| Does not guarantee Agensi approval | Yes | Stated in FAQ/limits. |
| No off-platform paid upgrade link | Yes | Only the source repository issue link. |

## Misleading-claim scan

The listing was checked for, and does not contain:

- “guaranteed MP4” or an unconditional MP4 promise;
- “fully automatic” fact-checking or production;
- “auto-install” or automatic environment setup;
- an interactive-canvas claim;
- a claim that Agensi review has passed;
- a paid upgrade or purchase link.

## Suggested-media caveat

`LISTING.md` tells the submitter not to present rendered MP4 frames as if the
free skill produced them by default. Any optional-render screenshot must be
labelled with its prerequisites.

## Verdict

**PASS** — the English listing describes the demonstrated capabilities and
discloses the text-only default and optional-render prerequisites.
