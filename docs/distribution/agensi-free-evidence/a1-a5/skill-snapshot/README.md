# MG Infographic Storyboard — Free Edition

A text-first skill for turning a script, article or topic into:

1. a shot-by-shot **storyboard**,
2. a **MG Animation Scene JSON v2.1** document,
3. **QA notes** covering assumptions, factual status, timing and layout risks.

The skill runs entirely inside the host AI agent. The text path needs no
Python, FFmpeg, TTS, network access or local repository.

## What it is not

- It is **not** a video generator by default.
- It does **not** download or install software.
- It does **not** verify facts automatically.
- It is **not** an interactive canvas or a hosted rendering service.

An optional local rendering path exists for users who already have the legacy
MG Animation Skill repository. It requires an explicit request and approval,
plus Python 3.10+, FFmpeg/`ffprobe`, a TTS engine and the legacy dependencies.

## How Agensi loads it

Agensi sends `SKILL.md` to the connected agent and can provide other text
files on demand. This package has one root skill and three text references:

```text
SKILL.md
README.md
references/scene-contract-lite.md
references/output-and-qa.md
references/safety-and-limitations.md
examples/brief_en.md
examples/storyboard_en.md
examples/scene_en.json
examples/qa_notes_en.md
examples/brief_zh.md
examples/storyboard_zh.md
examples/scene_zh.json
examples/qa_notes_zh.md
```

The agent is instructed to request `references/scene-contract-lite.md` before
writing JSON, `references/output-and-qa.md` before finalizing deliverables and
`references/safety-and-limitations.md` before factual or rendering decisions.
Do not assume all files are preloaded.

## Quick start

English:

> Turn this article into a 24-second infographic animation storyboard and a
> Scene JSON v2.1 document. Audience: high-school students. Narration in
> English. Do not invent statistics. Add QA notes.

Chinese:

> 把这个主题做成 24 秒的信息图动画分镜和 Scene JSON v2.1：光合作用如何把
> 阳光变成植物需要的糖。受众是初中生。不要编造数据，附上 QA 说明。

The agent should declare defaults, deliver the three artifacts and state that
no video was rendered unless it actually was.

## Optional local rendering

Only with an existing checkout and explicit user approval:

```bash
python scripts/validate.py path/to/scene.json
python scripts/pipeline.py path/to/scene.json --engine espeak --output-dir output/demo
ffprobe -v error -show_entries format=duration -show_entries stream=codec_type,codec_name path/to/demo.mp4
```

Requirements: Python 3.10+, Pillow, numpy, jsonschema, FFmpeg and `ffprobe`,
plus a configured TTS engine. Offline `espeak` is a functional test voice, not
a natural narrator. Edge TTS requires network and an already-installed
dependency. Do not install packages or call paid services automatically.

## Examples

`examples/` contains one English and one Chinese brief, storyboard, Scene JSON
and QA-note example. Both JSON documents are written against the real v2.1
contract. They contain **no claim objects** and assert **no `verified`
status**; their explanatory statements are user-provided general knowledge and
are not independently verified. They are illustrative text, not rendered
media.

## Limits

- Narration durations in the text path are estimates.
- Very long text can still overflow even when the layout engine wraps and
  shrinks it; split shots instead of shrinking type below legibility.
- The legacy renderer supports pairwise transitions, not complex multi-scene
  compositing.
- A public repository without a license file does not grant redistribution
  rights. Distribution terms are decided by the project owner.

## Files not included in the ZIP

`LISTING.md` and the repository-side packaging/test scripts are intentionally
excluded from the distributed package so consumers receive only the skill,
its references and examples.

## Source project

Legacy implementation and issue tracker:
<https://github.com/huangyong7878/mg-animation-skill>
