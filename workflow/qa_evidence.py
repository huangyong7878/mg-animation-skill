#!/usr/bin/env python3
"""Prepare deterministic timed-frame evidence for independent MG video QA.

Reads real MP4/MOV/WebM with ffprobe/ffmpeg. Does not score, understand, or
approve the animation. Requested timestamps are approximate frame positions.
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

try:
    from workflow.check_handoff import canonical_digest, validate_bundle
except ModuleNotFoundError:
    from check_handoff import canonical_digest, validate_bundle

ALLOWED_VIDEO_SUFFIXES = (".mp4", ".mov", ".webm", ".mkv")
ALLOWED_FRAME_SUFFIXES = (".png",)
EVIDENCE_FILE = "evidence_index.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def read_video(path):
    video = Path(path).resolve()
    if video.suffix.lower() not in ALLOWED_VIDEO_SUFFIXES:
        raise ValueError("Video must be MP4/MOV/WebM/MKV")
    if not video.is_file() or video.stat().st_size == 0:
        raise ValueError(f"Video is missing or empty: {video}")
    return video


def run_command(argv, runner=subprocess.run):
    try:
        return runner(argv, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise ValueError(f"Missing external command: {argv[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"{argv[0]} failed: {(exc.stderr or str(exc))[:800]}") from exc


def probe_video(video, runner=subprocess.run):
    result = run_command([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_frames:format=duration",
        "-of", "json", str(video),
    ], runner)
    try:
        data = json.loads(result.stdout)
        stream = data["streams"][0]
        fps = float(Fraction(stream["avg_frame_rate"]))
        duration = float(data["format"]["duration"])
        width, height = int(stream["width"]), int(stream["height"])
    except (KeyError, IndexError, ValueError, ZeroDivisionError) as exc:
        raise ValueError("ffprobe did not return usable video metadata") from exc
    if not all(math.isfinite(v) and v > 0 for v in (fps, duration)) or width < 1 or height < 1:
        raise ValueError("Invalid video duration, dimensions or FPS")
    return {"width": width, "height": height, "fps": fps, "duration_s": duration,
            "reported_frame_count": stream.get("nb_frames")}


def check_spec(spec, video_info):
    errors = validate_bundle(spec)
    if errors:
        raise ValueError("Invalid director spec: " + "; ".join(errors))
    expected = spec["output"]
    if video_info["width"] != expected["width"] or video_info["height"] != expected["height"]:
        raise ValueError("Video resolution differs from director specification")
    if abs(video_info["fps"] - expected["fps"]) > 0.15:
        raise ValueError("Video frame rate differs from director specification")
    if abs(video_info["duration_s"] - expected["duration_s"]) > max(0.15, 3 / video_info["fps"]):
        raise ValueError("Video duration differs from director specification")


def timeline_samples(spec, duration, fps, interval, focus, radius, focus_step, max_frames):
    if not all(math.isfinite(v) and v > 0 for v in (interval, focus_step)):
        raise ValueError("interval and focus_step must be positive finite numbers")
    if not math.isfinite(radius) or radius < 0:
        raise ValueError("focus_radius must be a nonnegative finite number")
    if max_frames < 1 or max_frames > 500:
        raise ValueError("max_frames must be 1..500")
    frame_end = max(0.0, duration - 1 / fps)
    if frame_end / interval > max_frames + 5:
        raise ValueError("Uniform interval would exceed max-frames")
    if focus and len(focus) * (2 * radius / focus_step + 1) > max_frames * 5:
        raise ValueError("Focus sampling would exceed max-frames")
    times = {}

    def add(time_s, reason):
        clamped = min(frame_end, max(0.0, time_s))
        ms = round(clamped * 1000)
        item = times.setdefault(ms, set())
        item.add(reason)

    for index in range(int(frame_end / interval) + 1):
        add(index * interval, "uniform")
    add(frame_end, "last_frame")
    for shot in spec["shots"]:
        add(shot["start_s"], "shot_start")
        add(shot["start_s"] + shot["duration_s"] - 1 / fps, "shot_end")
    for at in focus:
        if not math.isfinite(at) or at < 0 or at >= duration:
            raise ValueError(f"Focus timestamp outside video: {at}")
        steps = int(math.ceil(radius / focus_step))
        for offset in range(-steps, steps + 1):
            time_s = at + offset * focus_step
            if at - radius - 1e-6 <= time_s <= at + radius + 1e-6:
                add(time_s, "focus")
        add(at, "focus_center")
    if len(times) > max_frames:
        raise ValueError(f"Planned {len(times)} frames exceeds max_frames={max_frames}")

    def shot_for(t):
        for shot in spec["shots"]:
            if shot["start_s"] <= t <= shot["start_s"] + shot["duration_s"]:
                return shot["id"]
        return None

    return [{"requested_time_s": ms / 1000, "shot_id": shot_for(ms / 1000),
             "reasons": sorted(reasons), "filename": f"frames/t{ms:08d}.png"}
            for ms, reasons in sorted(times.items())]


def extract_frame(video, time_s, output, runner=subprocess.run):
    run_command([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-ss", f"{time_s:.3f}", "-i", str(video), "-frames:v", "1",
        "-y", str(output),
    ], runner)
    if not output.is_file() or output.stat().st_size == 0:
        raise ValueError(f"ffmpeg did not produce a frame at requested {time_s:.3f}s")
    try:
        with Image.open(output) as frame:
            frame.verify()
    except (OSError, ValueError) as exc:
        raise ValueError(f"Extracted image cannot be decoded: {output}") from exc


def make_contact_sheets(output_dir, frames, cols=4, per_sheet=24):
    output_dir = Path(output_dir)
    files = []
    for sheet_index, offset in enumerate(range(0, len(frames), per_sheet), 1):
        subset = frames[offset:offset + per_sheet]
        thumb_w, thumb_h, label_h, gap = 280, 158, 28, 8
        rows = (len(subset) + cols - 1) // cols
        width = cols * (thumb_w + gap) + gap
        height = rows * (thumb_h + label_h + gap) + gap
        sheet = Image.new("RGB", (width, height), "#f7f7f7")
        canvas = ImageDraw.Draw(sheet)
        for idx, entry in enumerate(subset):
            x = gap + (idx % cols) * (thumb_w + gap)
            y = gap + (idx // cols) * (thumb_h + label_h + gap)
            with Image.open(output_dir / entry["filename"]) as im:
                photo = ImageOps.contain(im.convert("RGB"), (thumb_w, thumb_h))
            sheet.paste(photo, (x + (thumb_w - photo.width) // 2, y))
            label = (f"{entry['requested_time_s']:.3f}s | "
                     f"{entry['shot_id'] or 'unmapped'} | "
                     f"{','.join(entry['reasons'])}")
            canvas.text((x, y + thumb_h + 4), label, fill="black")
        filename = f"contact_sheet_{sheet_index:02d}.jpg"
        sheet.save(output_dir / filename, quality=85)
        files.append({"path": filename, "size_bytes": (output_dir / filename).stat().st_size,
                      "sha256": sha256_file(output_dir / filename)})
    return files


def create_evidence(spec_path, video_path, outdir, interval=1.0, focus=(),
                    radius=1.0, focus_step=0.2, max_frames=120,
                    runner=subprocess.run):
    spec = load_json(spec_path)
    video = read_video(video_path)
    info = probe_video(video, runner)
    check_spec(spec, info)
    plan = timeline_samples(spec, info["duration_s"], info["fps"], interval,
                            list(focus), radius, focus_step, max_frames)
    root = Path(outdir).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"Output directory is not empty: {root}")
    (root / "frames").mkdir(parents=True, exist_ok=True)
    frames = []
    for frame in plan:
        path = root / frame["filename"]
        extract_frame(video, frame["requested_time_s"], path, runner)
        frames.append({**frame, "size_bytes": path.stat().st_size,
                       "sha256": sha256_file(path)})
    contacts = make_contact_sheets(root, frames)
    output = {
        "evidence_version": "1.0",
        "purpose": "timed frames for human/multimodal-model review; not automatic QA",
        "limitations": [
            "Requested timestamps are approximate; exact decoded frame timestamps are not certified.",
            "Still frames and contact sheets cannot prove continuous motion; watch actual MP4.",
            "This script does not determine whether a requirement passes or fails.",
        ],
        "director": {"spec_id": spec["spec_id"], "revision": spec["revision"],
                     "spec_sha256": canonical_digest(spec)},
        "video": {"original_filename": video.name, "sha256": sha256_file(video),
                  "size_bytes": video.stat().st_size, **info},
        "sampling": {"interval_s": interval, "focus_seconds": list(focus),
                     "focus_radius_s": radius, "focus_step_s": focus_step},
        "frames": frames,
        "contact_sheets": contacts,
    }
    (root / EVIDENCE_FILE).write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def verify_evidence(evidence_dir, video_path, spec_path):
    root = Path(evidence_dir).resolve()
    record = load_json(root / EVIDENCE_FILE)
    errors = []
    video = read_video(video_path)
    spec = load_json(spec_path)
    if record["director"]["spec_sha256"] != canonical_digest(spec):
        errors.append("Evidence director spec SHA does not match")
    if record["video"]["sha256"] != sha256_file(video):
        errors.append("Evidence video SHA does not match")
    if record["video"]["size_bytes"] != video.stat().st_size:
        errors.append("Evidence video size does not match")
    seen = set()
    for entry in [*record["frames"], *record["contact_sheets"]]:
        rel = Path(entry.get("filename", entry.get("path", "")))
        file_path = (root / rel).resolve()
        if not rel.as_posix() or rel.is_absolute() or not file_path.is_relative_to(root):
            errors.append(f"Evidence path escapes output: {rel}")
            continue
        if str(rel) in seen:
            errors.append(f"Duplicate evidence path: {rel}")
            continue
        seen.add(str(rel))
        if not file_path.is_file():
            errors.append(f"Missing evidence: {rel}")
            continue
        if file_path.stat().st_size != entry["size_bytes"] or sha256_file(file_path) != entry["sha256"]:
            errors.append(f"Evidence checksum mismatch: {rel}")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create", help="Probe video; extract timed frames and contact sheets")
    p.add_argument("--spec", required=True)
    p.add_argument("--video", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--interval", type=float, default=1.0)
    p.add_argument("--focus", type=float, action="append", default=[])
    p.add_argument("--focus-radius", type=float, default=1.0)
    p.add_argument("--focus-step", type=float, default=0.2)
    p.add_argument("--max-frames", type=int, default=120)
    p = sub.add_parser("verify", help="Check evidence files against original video and spec")
    p.add_argument("--spec", required=True)
    p.add_argument("--video", required=True)
    p.add_argument("--evidence-dir", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = create_evidence(args.spec, args.video, args.outdir, args.interval,
                                     args.focus, args.focus_radius,
                                     args.focus_step, args.max_frames)
            print(f"CREATED {args.outdir}: {len(result['frames'])} timed frames, "
                  f"{len(result['contact_sheets'])} contact sheet(s)")
        else:
            errors = verify_evidence(args.evidence_dir, args.video, args.spec)
            if errors:
                for error in errors:
                    print("ERROR:", error, file=sys.stderr)
                return 1
            print("PASS: video/spec and evidence frame SHA256 match")
        print("NOTICE: this only prepares evidence; no independent visual QA occurred")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("ERROR:", str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
