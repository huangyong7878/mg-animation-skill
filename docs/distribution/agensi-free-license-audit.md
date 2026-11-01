# Agensi Free Edition — License and Third-Party Rights Audit

> **Status: DISTRIBUTION BLOCKED.** This audit records facts and options only.
> Agent B does **not** choose a license, add a `LICENSE` file, or approve
> redistribution. Only the project owner may decide distribution terms.
>
> Audit date: 2026-11-01 · Auditor: Agent B (AI role) · Task: Issue #40
> Scope: `distributions/agensi-free/**` and the files that would be uploaded
> to Agensi.

## 1. Repository license finding

Command:

```bash
git ls-tree -r HEAD --name-only | grep -iE '(^|/)licen[cs]e'
```

Result: **no output — no `LICENSE` or `LICENSE.md` exists in the repository
tree at the audited commit.**

Consequences:

- A public GitHub repository is not, by itself, an open-source license.
- In the absence of a license, default copyright law applies: the owner
  retains all rights, and third parties have no automatic right to copy or
  redistribute the work.
- The free Agensi package cannot be published until the owner grants
  redistribution terms. This is a legal/product decision, not something an
  AI agent can infer from “the repo is public”.

## 2. Inventory of material in the proposed package

| Material | Location | Origin | Packaged? | Rights status |
|---|---|---|---|---|
| Skill instructions | `SKILL.md` | Written for this task | Yes | First-party; owner decision required |
| Package README | `README.md` | Written for this task | Yes | First-party; owner decision required |
| Contract summary | `references/scene-contract-lite.md` | Distilled from the repository's own schema/validator and `references/scene-contract.md` | Yes | First-party; no third-party text copied |
| Output/QA guide | `references/output-and-qa.md` | Written for this task | Yes | First-party; owner decision required |
| Safety guide | `references/safety-and-limitations.md` | Written for this task | Yes | First-party; owner decision required |
| English brief/storyboard/JSON | `examples/*_en.*` | Original generic civics text | Yes | Original; no quoted third-party source |
| Chinese brief/storyboard/JSON | `examples/*_zh.*` | Original generic science text | Yes | Original; no quoted third-party source |
| Listing copy | `LISTING.md` | Written for this task | No (excluded from ZIP) | First-party; owner decision required |
| Packaging/tests | `scripts/package_agensi_free.py`, `tests/test_agensi_free.py` | Written for this task | No (excluded from ZIP) | First-party; not distributed |

No images, icons, fonts, audio, video, datasets or long verbatim quotations
are included in the package.

## 3. Runtime components — not packaged, not redistributed

| Component | Role | Packaging status | Notes |
|---|---|---|---|
| Python 3.10+ | Optional local render | Not packaged | User's own environment |
| Pillow, numpy, jsonschema | Optional local render | Not packaged | Installed by the user; their licenses apply locally |
| FFmpeg / `ffprobe` | Optional local render | Not packaged | Separate executable; GPL/LGPL obligations depend on the build the user installs |
| eSpeak / Edge TTS | Optional narration | Not packaged | eSpeak is offline and functional; Edge TTS needs network |
| System fonts (PingFang, Noto, etc.) | Optional render glyphs | Not packaged | Font licenses govern local use; nothing is redistributed |
| Agensi platform | Distribution | N/A | Subject to Agensi creator/reviewer terms |

The text path has no runtime dependency and does not call these components.

## 4. External references

- Agensi documentation URLs in the task specification are referenced, not
  copied into the package.
- The package README links to the source GitHub repository. This is a plain
  hyperlink, not a transfer of content.
- Example content is generic and original; no third-party article, statistic
  or quotation is reproduced.

## 5. License options for the owner (not selected)

Agent B offers these as discussion options only:

1. **Free-use proprietary terms** — a short owner-authored EULA permitting
   free use of the packaged text but reserving other rights.
2. **Creative Commons Attribution 4.0 (CC BY 4.0)** for the packaged text,
   with a separate decision for repository code.
3. **Split licensing** — e.g., MIT for repository scripts and CC BY 4.0 for
   documentation, with a clear note on which files fall under which terms.
4. **No redistribution** — keep the package internal and do not submit it to
   Agensi.

Each option has different obligations (attribution, share-alike, warranty
disclaimers, trademark handling). The owner should choose with the Agensi
creator terms in view.

## 6. Blocking checklist for A8

| Check | Result | Evidence |
|---|---|---|
| Repository `LICENSE` exists | **NO** | `git ls-tree` returned no license file |
| Third-party assets in package | **NONE** | Allowlist contains only UTF-8 `.md` and `.json` |
| Third-party text quoted at length | **NONE** | Examples are original generic text |
| Fonts/images/audio packaged | **NONE** | Packaging allowlist and tests reject binaries |
| Runtime dependencies bundled | **NONE** | Not in ZIP; optional local only |
| Owner approved distribution terms | **NO** | Pending owner decision |
| Agensi creator terms reviewed by owner | **NO** | Pending owner action |

## 7. Decision required from the owner

Before any Agensi upload:

1. Choose and add a license/terms file (or explicitly decide not to publish).
2. Confirm that the repository owner holds all rights to the skill text.
3. Confirm the Agensi creator agreement and review requirements.
4. Record the approval in Issue #40 / PR #41.

Until then, **A8 remains BLOCKED and the package must not be uploaded**.
