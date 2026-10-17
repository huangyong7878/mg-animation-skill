"""Auto pipeline for AI-directed MG animation (v2.1+).

Two stages, split by the user-review gate:

  Stage 1 (prepare):
    narration.txt → sentence segments → Edge TTS → voice.wav + timings.json
    + director_brief.md (input for the Creative Director)

    [AI Creative Director reads references/creative-director.md, designs storyboard]
    [User reviews and approves the storyboard]

  Stage 2 (render):
    approved scene.json + voice.wav → validate → render → mux audio → final.mp4

    [AI Technical Director reads references/technical-director.md, generates scene.json]

Usage:
  python scripts/auto_pipeline.py prepare narration.txt --outdir work/ep01
  python scripts/auto_pipeline.py render work/ep01/scene.json --outdir work/ep01
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narrate import create_narration
from validate import validate
from engine import load


def split_sentences(text: str) -> list[str]:
    """Split Chinese narration into sentences, keeping punctuation."""
    text = text.strip()
    # Split on 。！？；, keep the delimiter
    parts = re.split(r'(?<=[。！？；])', text)
    sentences = [p.strip() for p in parts if p.strip()]
    # Further split very long sentences on ， if > 40 chars
    out = []
    for s in sentences:
        if len(s) > 40 and '，' in s:
            sub = re.split(r'(?<=，)', s)
            out.extend(x.strip() for x in sub if x.strip())
        else:
            out.append(s)
    return out


def stage_prepare(narration_path: str, outdir: str, voice: str = None,
                  speed: int = 165, engine: str = 'fish') -> Path:
    narration_path = Path(narration_path).resolve()
    outdir = Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    text = narration_path.read_text(encoding='utf-8')
    sentences = split_sentences(text)
    if not sentences:
        raise ValueError('No sentences found in narration text')

    # Temporary narration plan (minimal input for TTS, no scene JSON needed)
    segments = []
    for i, s in enumerate(sentences):
        # Paragraph break = longer pause (detect blank lines in original)
        pause = 0.3
        segments.append({"text": s, "pause_after": pause})
    # Longer pause between paragraphs
    raw_paras = [p for p in text.split('\n\n') if p.strip()]
    if len(raw_paras) > 1:
        # Mark last sentence of each paragraph (except final) with longer pause
        sent_idx = 0
        for pi, para in enumerate(raw_paras):
            para_sents = split_sentences(para)
            if pi < len(raw_paras) - 1 and para_sents:
                segments[sent_idx + len(para_sents) - 1]["pause_after"] = 0.6
            sent_idx += len(para_sents)

    plan = {"narration": {"segments": segments}}
    plan_path = outdir / "narration_plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1),
                         encoding='utf-8')

    # TTS (Edge)
    audio_path = outdir / "voice.wav"
    timing_path = outdir / "timings.json"
    print(f"Synthesizing {len(segments)} segments with {engine}...", flush=True)
    create_narration(plan, audio_path, timing_path,
                     engine=engine, speed=speed, voice=voice)
    print(f"SAVED {audio_path}", flush=True)
    print(f"SAVED {timing_path}", flush=True)

    # Director brief for the Creative Director
    timings = json.loads(timing_path.read_text(encoding='utf-8'))
    total = max((s['end'] for s in timings['segments']), default=0)
    lines = [
        "# 导演简报 (Director Brief)",
        "",
        f"- 解说稿：{narration_path.name}",
        f"- 句子数：{len(segments)}",
        f"- 配音总时长：{total:.1f} 秒",
        f"- 时间轴精度：句级",
        "",
        "## 分句时间轴",
        "",
    ]
    for s in timings['segments']:
        lines.append(f"- [{s['start']:.1f} – {s['end']:.1f}] {s['text']}")
    lines += [
        "",
        "## 下一步",
        "",
        "AI 创意导演请阅读 `references/creative-director.md`，",
        "按其中的工作流程设计分镜表，输出给用户审核。",
    ]
    brief_path = outdir / "director_brief.md"
    brief_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"SAVED {brief_path}", flush=True)
    print(f"\nTotal narration: {total:.1f}s, {len(segments)} sentences", flush=True)
    return brief_path


def stage_render(scene_path: str, outdir: str) -> Path:
    scene_path = Path(scene_path).resolve()
    outdir = Path(outdir).resolve()

    audio_path = outdir / "voice.wav"
    timing_path = outdir / "timings.json"
    if not audio_path.exists():
        raise FileNotFoundError(f'{audio_path} not found. Run prepare first.')
    if not timing_path.exists():
        raise FileNotFoundError(f'{timing_path} not found. Run prepare first.')

    # Validate
    data = load(str(scene_path))
    issues = validate(data)
    if issues:
        raise ValueError('Scene validation failed:\n' + '\n'.join(issues))
    print('PASS: scene validation', flush=True)

    # Render (video only, then mux audio)
    basename = scene_path.stem
    silent_mp4 = outdir / f"{basename}_silent.mp4"
    final_mp4 = outdir / f"{basename}.mp4"
    render_py = Path(__file__).resolve().parent / "render.py"
    subprocess.run(
        [sys.executable, str(render_py), str(scene_path),
         '--out', str(silent_mp4)],
        check=True)
    print(f"SAVED {silent_mp4}", flush=True)

    # Mux audio
    subprocess.run(
        ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
         '-i', str(silent_mp4), '-i', str(audio_path),
         '-c:v', 'copy', '-c:a', 'aac', '-shortest',
         str(final_mp4)],
        check=True)
    print(f"SAVED {final_mp4}", flush=True)
    return final_mp4


def main():
    ap = argparse.ArgumentParser(description='AI-directed MG animation pipeline')
    sub = ap.add_subparsers(dest='stage', required=True)

    p1 = sub.add_parser('prepare', help='Text → TTS + timings + director brief')
    p1.add_argument('narration', help='Narration text file (.txt)')
    p1.add_argument('--outdir', default='work/ep01')
    p1.add_argument('--engine', choices=['espeak','edge','fish'], default='fish',
                    help='TTS engine (default fish)')
    p1.add_argument('--voice', default=None,
                    help='Voice: Edge voice name, or Fish Audio reference_id')
    p1.add_argument('--speed', type=int, default=165)

    p2 = sub.add_parser('render', help='Scene JSON + audio → final MP4')
    p2.add_argument('scene', help='Approved scene JSON')
    p2.add_argument('--outdir', default='work/ep01')

    args = ap.parse_args()
    if args.stage == 'prepare':
        stage_prepare(args.narration, args.outdir, args.voice, args.speed, args.engine)
    else:
        result = stage_render(args.scene, args.outdir)
        print(f'PIPELINE COMPLETE: {result}')


if __name__ == '__main__':
    main()
