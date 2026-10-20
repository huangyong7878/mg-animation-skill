#!/usr/bin/env python3
"""Build real Stage C *draft* TTS, timings, subtitles and a non-release AV preview.

No model API, no Fish/Edge network TTS, no approval, and no R5 claim.
Runs from an exact Git commit in an unprivileged GitHub Actions workflow.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

# Direct execution (python workflow/build_stagec_artifact.py) sets sys.path[0]
# to workflow/. Add the checked-out repository root for scripts + workflow imports.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from scripts.narrate import create_narration, RATE
    from scripts.primitives.orderflow import PILOT_EVENT_SECONDS
    from workflow.check_handoff import canonical_digest, validate_bundle
    from workflow.media_manifest import create_manifest, verify_manifest
    from workflow.av_sync_contract import validate_av_cues
except ModuleNotFoundError:
    from narrate import create_narration, RATE
    from scripts.primitives.orderflow import PILOT_EVENT_SECONDS
    from check_handoff import canonical_digest, validate_bundle
    from media_manifest import create_manifest, verify_manifest
    from av_sync_contract import validate_av_cues

SOURCE_PATHS = (
    "work/orders_pilot/stagec_narration.json",
    "work/orders_pilot/stagec_av_cues.json",
    "workflow/av_sync_contract.py",
    "contracts/av_sync_cues.schema.json",
    "work/orders_pilot/scene.json",
    "scripts/primitives/orderflow.py",
    "scripts/primitives/__init__.py",
    "scripts/narrate.py",
    "scripts/render.py",
)
SHA = re.compile(r"^[0-9a-f]{40}$")

# Pilot-specific narration alignment windows are derived from real motion
# markers in scripts/primitives/orderflow.py. Times are wall-clock seconds.
# (allowed start min, max, latest end): allow small synthesis variation,
# but never claim a voice/visual alignment we didn't actually check.
CUE_WINDOWS = {
    "intro": (0.0, 0.3, 3.3),
    "out_of_stock": (PILOT_EVENT_SECONDS["branch_split"],
                     PILOT_EVENT_SECONDS["branch_split"] + 0.35,
                     PILOT_EVENT_SECONDS["order_b_queue_arrival"] + 1.0),
    "in_stock": (PILOT_EVENT_SECONDS["order_a_ship_arrival"] - 0.6,
                 PILOT_EVENT_SECONDS["order_a_ship_arrival"] - 0.1,
                 12.9),
}
CUE_SEQUENCE = ("intro", "out_of_stock", "in_stock")
CUE_KEYWORDS = {
    "intro": ("两张订单",),
    "out_of_stock": ("库存不足", "订单B"),
    "in_stock": ("库存充足", "订单A"),
}


def run(argv, log):
    result = subprocess.run([str(v) for v in argv], cwd=ROOT,
                            capture_output=True, text=True)
    log.append("$ " + " ".join(str(v) for v in argv) + "\n"
               + result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"Command failed ({argv[0]}): "
                           + result.stderr[-2000:])
    return result.stdout


def require_plan(spec, scene, plan):
    errors = validate_bundle(spec)
    if errors:
        raise ValueError("Invalid director spec: " + "; ".join(errors))
    if spec["approval"]["status"] != "draft" or spec["narration"]["status"] != "draft":
        raise ValueError("Stage C test must not use or assert approved/locked narration")
    if spec["project_id"] != "orders_two_routes":
        raise ValueError("Stage C smoke test only supports Pilot orders_two_routes")
    output, canvas = spec["output"], scene["canvas"]
    for field in ("width", "height", "fps"):
        if output[field] != canvas[field]:
            raise ValueError(f"Director and scene {field} mismatch")
    if abs(float(output["duration_s"]) - float(canvas["duration"])) > .01:
        raise ValueError("Director and scene duration mismatch")
    if plan.get("test_only") is not True:
        raise ValueError("Test narration plan requires explicit test_only=true")
    segments = plan.get("narration", {}).get("segments")
    if not isinstance(segments, list) or not (1 <= len(segments) <= 10):
        raise ValueError("Narration plan needs 1..10 explicit test segments")
    ids = tuple(item.get("id") if isinstance(item, dict) else None
                for item in segments)
    if ids != CUE_SEQUENCE:
        raise ValueError("Stage C narration cue order must follow actual B-then-A picture timeline")
    for item in segments:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            raise ValueError("Each test segment needs text")
        if not item["text"].strip():
            raise ValueError("Empty narration text is forbidden")
        cue = item["id"]
        if not all(token in item["text"] for token in CUE_KEYWORDS[cue]):
            raise ValueError(f"Narration id/text does not match the {cue} visual branch")
        start = item.get("start")
        if type(start) not in (int, float):
            raise ValueError(f"Missing explicit start time for {cue} visual cue")
        minimum, maximum, _ = CUE_WINDOWS[cue]
        if not minimum <= float(start) <= maximum:
            raise ValueError(f"Narration cue {cue} start {start} outside the animation window")
    return segments


def check_timing_files(plan, timing, wav_path, srt_path, seconds):
    segments = plan["narration"]["segments"]
    actual = timing.get("segments", [])
    if len(actual) != len(segments):
        raise ValueError("TTS timing segment count differs from source narration")
    duration = float(timing.get("duration", -1))
    if abs(duration - seconds) > .03:
        raise ValueError("Generated TTS PCM duration differs from scene duration")
    with wave.open(str(wav_path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, RATE):
            raise ValueError("TTS WAV has wrong PCM format")
        length = wav.getnframes() / RATE
    if abs(length - seconds) > .03:
        raise ValueError("TTS WAV frame duration differs from scene duration")
    if not srt_path.is_file() or srt_path.stat().st_size == 0:
        raise ValueError("Generated SRT missing/empty")

    prev_end = 0.
    for index, (expected, timed) in enumerate(zip(segments, actual)):
        if timed.get("text") != expected["text"].strip():
            raise ValueError(f"Transcript mismatch for segment {index}")
        if timed.get("id") != expected.get("id", f"segment_{index+1}"):
            raise ValueError(f"Segment ID mismatch for segment {index}")
        start, end = float(timed["start"]), float(timed["end"])
        if start < prev_end - 0.005 or end <= start or end > seconds + .03:
            raise ValueError(f"TTS segment {index} is overlapping/outside duration")
        if timed.get("alignment") != "synthesized_segment_exact":
            raise ValueError("Missing measured synthesis timing provenance")
        cue = expected["id"]
        min_start, max_start, latest_end = CUE_WINDOWS[cue]
        if not min_start - .06 <= start <= max_start + .06:
            raise ValueError(f"Narration cue {cue} starts outside actual visual event window")
        if abs(start - expected["start"]) > .07:
            raise ValueError(f"Narration cue {cue} started away from requested visual event time")
        if end > latest_end + .05:
            raise ValueError(f"Narration cue {cue} ends too late for its visual event window")
        prev_end = end
    subtitles = srt_path.read_text(encoding="utf-8")
    for item in segments:
        if item["text"] not in subtitles:
            raise ValueError("SRT missing narration text")
    return {"narrated_segments": len(actual), "wav_duration_s": round(length, 3),
            "last_narration_end_s": round(prev_end, 3)}


def check_preview_video(info, spec):
    video = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    audio = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if len(video) != 1 or len(audio) != 1:
        raise ValueError("Stage C AV preview must have exactly one video and one audio stream")
    v, a = video[0], audio[0]
    if v.get("codec_name") != "h264" or a.get("codec_name") != "aac":
        raise ValueError("Stage C preview must contain H.264 video and AAC audio")
    if (int(v.get("width", 0)), int(v.get("height", 0))) != (
            spec["output"]["width"], spec["output"]["height"]):
        raise ValueError("Stage C preview resolution mismatch")
    if str(v.get("nb_frames", "")) != str(round(spec["output"]["fps"]
                                               * spec["output"]["duration_s"])):
        raise ValueError("Stage C preview missing expected video frames")
    duration = float(info["format"]["duration"])
    if abs(duration - spec["output"]["duration_s"]) > .15:
        raise ValueError("Stage C preview AV container duration mismatch")


def build(spec_path, scene_path, plan_path, source_sha, artifact_root,
          artifact_name, run_url):
    if not SHA.fullmatch(source_sha):
        raise ValueError("Expected exact lowercase Git SHA-1, 40 hex characters")
    current = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                             check=True, capture_output=True, text=True).stdout.strip()
    if current != source_sha:
        raise ValueError("Checkout commit does not match requested source SHA")
    root = Path(artifact_root).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("Refusing to overwrite populated artifact output")
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    scene = json.loads(Path(scene_path).read_text(encoding="utf-8"))
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    cue_contract = json.loads(
        (ROOT / "work/orders_pilot/stagec_av_cues.json").read_text(encoding="utf-8")
    )
    segments = require_plan(spec, scene, plan)
    # Fail before TTS/render if the director's narration/visual-event contract
    # does not correspond to this exact renderer timeline and script.
    validate_av_cues(spec, plan, PILOT_EVENT_SECONDS, cue_contract)
    for relative in SOURCE_PATHS:
        if not (ROOT / relative).is_file():
            raise ValueError(f"Missing source path {relative}")

    (root / "media").mkdir(parents=True, exist_ok=True)
    for relative in SOURCE_PATHS:
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, root / relative)
    shutil.copyfile(spec_path, root / "director_spec.json")
    (root / "narration.txt").write_text(
        "\n".join(s["text"].strip() for s in segments) + "\n", encoding="utf-8"
    )
    runtime_plan = {**plan, "canvas": scene["canvas"], "scenes": scene["scenes"]}
    wav, timing = root / "media/voice.wav", root / "media/timings.json"
    result = create_narration(runtime_plan, wav, timing,
                              engine="espeak", speed=175, voice="zh")
    del result
    srt = root / "media/timings.srt"
    timing_data = json.loads(timing.read_text(encoding="utf-8"))
    measured = check_timing_files(plan, timing_data, wav, srt,
                                  float(scene["canvas"]["duration"]))
    cue_report = validate_av_cues(
        spec, plan, PILOT_EVENT_SECONDS, cue_contract, timings=timing_data)
    (root / "av_sync_report.json").write_text(
        json.dumps(cue_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    log = ["Stage C draft test with offline eSpeak; does not replace formal narration."]
    run([sys.executable, "scripts/validate.py", scene_path], log)
    preview_rel = "media/stagec_av_preview.mp4"
    preview = root / preview_rel
    run([sys.executable, "scripts/render.py", scene_path,
         "--audio", wav, "--timings", timing, "--out", preview], log)
    info = json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height,nb_frames",
        "-of", "json", preview], log))
    check_preview_video(info, spec)
    delivery = {
        "schema_version": "1.0",
        "project_id": spec["project_id"], "spec_id": spec["spec_id"],
        "spec_revision": spec["revision"], "spec_sha256": canonical_digest(spec),
        "implementation_commit": source_sha,
        "attempt": 1, "stage": "C", "status": "prototype",
        "artifacts": {
            "source_paths": list(SOURCE_PATHS),
            "video_path": preview_rel, "audio_path": "media/voice.wav",
            "timings_path": "media/timings.json",
        },
        "checks": [
            {"name": "offline_tts_generated", "result": "pass",
             "detail": "eSpeak zh synthesized measured PCM, not an AI-generated/natural voice"},
            {"name": "timings_and_srt_validated", "result": "pass",
             "detail": f"Validated {measured['narrated_segments']} measured sentence timings, WAV length and SRT transcript"},
            {"name": "narration_visual_event_cues", "result": "pass",
             "detail": "R3 cue contract matched planned and measured TTS to R4 declared animation event times; does NOT establish pixel/auditory semantic QA"},
            {"name": "av_preview_probed", "result": "pass",
             "detail": "ffprobe confirmed H.264 + AAC, frame count, resolution and duration"},
        ],
        "deviations": [],
        "notes": ("Stage C engineering smoke-test ONLY. Sample script is unapproved;"
                  " original narration and director approval remain draft;"
                  " AV preview is NOT Stage D, synchronized-word QA or release approval."),
    }
    errors = validate_bundle(spec, delivery)
    if errors:
        raise ValueError("Stage C delivery invalid: " + "; ".join(errors))
    (root / "delivery.json").write_text(
        json.dumps(delivery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "build_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    extras = ["media/timings.srt", "narration.txt", "director_spec.json",
              "av_sync_report.json",
              "build_log.txt", *SOURCE_PATHS]
    manifest = create_manifest(
        spec, delivery, root, backend="actions",
        artifact_name=artifact_name, run_url=run_url, extras=extras)
    (root / "media_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errors = verify_manifest(manifest, root, spec, delivery)
    if errors:
        raise ValueError("Stage C media integrity failed: " + "; ".join(errors))
    print("Stage C draft built:", root, "source:", source_sha,
          "segments:", measured["narrated_segments"],
          "duration_s:", measured["wav_duration_s"])
    print("NOT A RELEASE. R5 does not accept Stage C as Stage B visual approval.")
    return delivery


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", default=str(ROOT / "examples/workflow_orders_spec.json"))
    p.add_argument("--scene", default=str(ROOT / "work/orders_pilot/scene.json"))
    p.add_argument("--plan", default=str(ROOT / "work/orders_pilot/stagec_narration.json"))
    p.add_argument("--source-sha", required=True)
    p.add_argument("--artifact-root", required=True)
    p.add_argument("--artifact-name", required=True)
    p.add_argument("--run-url", required=True)
    args = p.parse_args(argv)
    try:
        build(args.spec, args.scene, args.plan, args.source_sha,
              args.artifact_root, args.artifact_name, args.run_url)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
