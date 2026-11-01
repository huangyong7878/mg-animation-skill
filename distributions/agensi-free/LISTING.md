# Agensi Listing Copy — MG Infographic Storyboard (Free)

> **Internal status (not part of the public listing):** Draft only.
> Distribution is **BLOCKED** until the project owner approves license and
> redistribution terms (see `docs/distribution/agensi-free-license-audit.md`)
> and completes the Agensi submission/review. Platform uniqueness of the
> listing name must also be confirmed at submission. This file is excluded
> from the distributable ZIP.

## Listing fields

| Field | Value |
|---|---|
| Name | MG Infographic Storyboard |
| Version | 1.0.0 |
| Price | FREE |
| Category | Content creation / video pre-production |
| Language support | English, Simplified Chinese |
| Source project | <https://github.com/huangyong7878/mg-animation-skill> |

## Short summary (≤ 160 characters)

Turn a script or topic into an infographic storyboard, an MG Animation Scene
JSON v2.1 document, and QA notes. Text-only by default; no renderer required.

## Detailed description

MG Infographic Storyboard is a text-first pre-production skill for explainer
animation. Give it an article, a lesson script, a product note or just a topic,
and it returns three connected deliverables:

1. **Storyboard** — shot IDs, timings, visual elements, animation order,
   transitions, narration lines and fact status.
2. **Scene JSON v2.1** — a document written against the real MG Animation
   scene contract, using documented containers, text, cards, tables,
   timelines, icons, lines, arrows and animations.
3. **QA notes** — assumptions, unverified claims, text-overflow risks,
   narration-timing risks, and an honest statement of what was and was not
   validated.

The free edition runs entirely in the host agent. It needs no Python, FFmpeg,
TTS engine, network access or repository checkout.

### What it does well

- Structures a short explainer into three to five clear shots.
- Uses tables for comparisons, timelines for sequences and flow rows for
  processes.
- Flags claims that lack evidence instead of inventing sources.
- Produces JSON that follows the real field names, timing limits and claim
  gate of the legacy MG Animation contract.
- Works in English and Simplified Chinese.

### What it does not do

- It does not render video by default and does not promise an MP4.
- It does not synthesize audio or burn subtitles in the free text path.
- It does not install software, clone repositories or call paid services.
- It does not automatically fact-check or independently verify sources.
- It is not an interactive canvas, timeline editor or web UI.
- It does not guarantee Agensi review approval.

### Optional local rendering

If you already have the legacy MG Animation Skill repository, Python 3.10+,
FFmpeg/`ffprobe`, a TTS engine and the Python dependencies, the skill can guide
a local render using the existing `validate.py` and `pipeline.py` scripts.
That path requires your explicit approval and terminal permissions. It is not
required for the three text deliverables, and the skill will not install
anything for you.

## Audience

- Educators and course creators drafting explainer videos.
- Marketing and content teams producing storyboards before production.
- Motion-design students learning information-graphic structure.
- AI-agent users who want machine-readable scene JSON without a local engine.

## Example prompts

1. **English — education**
   > Turn this article about the water cycle into a 24-second infographic
   > storyboard and a Scene JSON v2.1 document for middle-school students.
   > Add QA notes and do not invent statistics.

2. **English — product**
   > Create a three-shot explainer storyboard for our new note-taking app.
   > Use a flow row for the problem, a table for the features and a timeline
   > for onboarding. Return the storyboard, JSON and honest QA notes.

3. **中文 — 科普**
   > 把“光合作用如何把阳光变成糖”做成 24 秒的信息图动画分镜和 Scene JSON
   > v2.1，受众是初中生。没有来源的数据不要写成事实，最后附 QA 说明。

## Requirements and permissions

| Use | Requirements |
|---|---|
| Storyboard + JSON + QA | None beyond the host agent. No terminal, network or local files. |
| Optional local render | User-owned legacy repository, Python 3.10+, Pillow, numpy, jsonschema, FFmpeg/`ffprobe`, a configured TTS engine, and explicit user approval. |

The skill is instructed not to request API keys, tokens, passwords or private
data, and not to browse, download or install anything for the text path.

## Limitations

- Narration duration is estimated in the text path; actual TTS must be
  measured separately.
- The layout engine wraps and shrinks text, but long copy can still overflow.
  Split shots rather than shrinking type below legibility.
- Scene JSON is schema-drafted unless `scripts/validate.py` was actually run.
- The legacy renderer supports pairwise transitions, not complex multi-scene
  compositing.
- Facts remain the user's responsibility unless independently verified.

## FAQ

**Does this generate an MP4?**
No, not by default. The free edition returns a storyboard, Scene JSON and QA
notes. Local rendering is optional and requires an existing installation and
your explicit approval.

**Can it check my facts?**
It can separate user-provided, verified and unverified claims, and it refuses
to fabricate sources. It does not independently verify truth. By default the
legacy validator checks claim metadata only (status, URL shape and quote
length); it does not fetch sources. Quote-presence checking requires
`--fetch-sources`, and neither mode proves that a claim is true.

**Do I need Python or FFmpeg?**
Not for the free text deliverables. Only the optional local render path needs
them.

**Will it install the renderer for me?**
No. It will not clone, install or download dependencies, and it will not call
paid services.

**Does it support Chinese?**
Yes. The package includes Simplified Chinese examples and the same v2.1
contract applies.

**Is the JSON guaranteed to render?**
It is written against the real v2.1 contract. Rendering can still fail for
missing fonts, missing image assets or environment problems. The skill states
whether validation actually ran.

## Suggested listing media

- A screenshot of a three-shot storyboard table.
- A side-by-side view of the storyboard and the generated JSON.
- A QA-notes screenshot highlighting an omitted unverified claim.
- A diagram showing the three deliverables and the optional render branch.

Do not show rendered MP4 frames as if the free skill produced them by default.
If showing an optional render, label it as a locally rendered example with its
prerequisites.

## Support

Report issues at the source project:
<https://github.com/huangyong7878/mg-animation-skill/issues>

This listing offers no off-platform paid upgrade or purchase link.
