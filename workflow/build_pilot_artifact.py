#!/usr/bin/env python3
"""Build Pilot 001's actual silent video and review bundle for GitHub Artifacts.

This is a deliberately concrete pilot renderer, not an arbitrary-model API or
universal renderer. It never posts PR comments, merges or approves visual QA.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

try:
    from workflow.check_handoff import canonical_digest, validate_bundle
    from workflow.media_manifest import create_manifest, verify_manifest
    from workflow.qa_evidence import create_evidence, verify_evidence
    from workflow.role_pack import main as role_pack_main
except ModuleNotFoundError:
    from check_handoff import canonical_digest, validate_bundle
    from media_manifest import create_manifest, verify_manifest
    from qa_evidence import create_evidence, verify_evidence
    from role_pack import main as role_pack_main

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "scripts/primitives/orderflow.py",
    "scripts/primitives/__init__.py",
    "work/orders_pilot/scene.json",
)
KEYFRAME_TIMES_S = (0.0, 2.0, 4.5, 5.0, 5.3, 5.8, 6.0, 8.0, 11.5, 12.8)
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def run(command, log):
    completed = subprocess.run(
        [str(arg) for arg in command], cwd=ROOT, capture_output=True, text=True,
    )
    rendered = f"$ {' '.join(map(str, command))}\n{completed.stdout}{completed.stderr}"
    log.append(rendered)
    if completed.returncode:
        raise RuntimeError(rendered[-4000:])
    print(rendered[-1500:])
    return completed.stdout


def probe(path, log):
    result = json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,nb_frames",
        "-of", "json", path,
    ], log))
    return result


def check_pilot_scene(spec, scene):
    errors = validate_bundle(spec)
    if errors:
        raise ValueError("Bad pilot director spec: " + "; ".join(errors))
    output, canvas = spec["output"], scene["canvas"]
    for left, right in (
        ("width", "width"), ("height", "height"), ("fps", "fps"),
    ):
        if output[left] != canvas[right]:
            raise ValueError(f"Director / render scene {left} mismatch")
    if abs(output["duration_s"] - canvas["duration"]) > 0.01:
        raise ValueError("Director / render scene duration mismatch")
    if len(spec["shots"]) != 1 or len(scene["scenes"]) != 1:
        raise ValueError("Pilot builder supports precisely one shot; use a real project renderer for others")
    if spec["shots"][0]["id"] != scene["scenes"][0]["id"]:
        raise ValueError("Director / render scene shot id mismatch")


def check_video_metadata(info, spec):
    output = spec["output"]
    streams = info.get("streams", [])
    vids = [s for s in streams if s["codec_type"] == "video"]
    audios = [s for s in streams if s["codec_type"] == "audio"]
    if len(vids) != 1 or audios:
        raise ValueError("Stage B expects one video stream and NO audio stream")
    stream = vids[0]
    if (stream.get("width"), stream.get("height")) != (output["width"], output["height"]):
        raise ValueError("Rendered video resolution mismatch")
    fps = float(Fraction(stream["r_frame_rate"]))
    if abs(fps - output["fps"]) > 0.01:
        raise ValueError("Rendered video fps mismatch")
    if stream.get("codec_name") != "h264":
        raise ValueError("Rendered video is not H.264")
    expected_frames = round(output["duration_s"] * output["fps"])
    if str(stream.get("nb_frames")) != str(expected_frames):
        raise ValueError("Rendered frame count mismatch")
    if abs(float(info["format"]["duration"]) - output["duration_s"]) > 0.07:
        raise ValueError("Rendered video duration mismatch")


def build(spec_path, scene_path, source_sha, artifact_root, artifact_name, run_url):
    source_sha = source_sha.lower()
    if not HEX40.fullmatch(source_sha):
        raise ValueError("--source-sha must be a full 40-character Git hex SHA")
    actual_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip().lower()
    if actual_sha != source_sha:
        raise ValueError(f"Checkout commit {actual_sha} differs from source-sha {source_sha}")
    root = Path(artifact_root).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("Refusing to overwrite nonempty artifact root")
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    scene = json.loads(Path(scene_path).read_text(encoding="utf-8"))
    check_pilot_scene(spec, scene)
    log = []

    for relative in SOURCE_FILES:
        file = ROOT / relative
        if not file.is_file():
            raise ValueError(f"Missing tracked source: {relative}")

    (root / "media" / "keyframes").mkdir(parents=True, exist_ok=True)
    for relative in SOURCE_FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    shutil.copyfile(spec_path, root / "director_spec.json")

    run([sys.executable, "scripts/validate.py", scene_path], log)
    video_rel = "media/shot_01_silent.mp4"
    video = root / video_rel
    run([sys.executable, "scripts/render.py", scene_path, "--out", video], log)
    metadata = probe(video, log)
    check_video_metadata(metadata, spec)

    keyframes = []
    for second in KEYFRAME_TIMES_S:
        relative = f"media/keyframes/shot_01_{round(second * 1000):06d}.png"
        keyframes.append(relative)
        run(["ffmpeg", "-hide_banner", "-loglevel", "error",
             "-ss", f"{second:.3f}", "-i", video,
             "-frames:v", "1", "-y", root / relative], log)
        if not (root / relative).is_file() or (root / relative).stat().st_size == 0:
            raise ValueError(f"Missing keyframe: {relative}")

    delivery = {
        "schema_version": "1.0",
        "project_id": spec["project_id"],
        "spec_id": spec["spec_id"],
        "spec_revision": spec["revision"],
        "spec_sha256": canonical_digest(spec),
        "implementation_commit": source_sha,
        "attempt": 1,
        "stage": "B",
        "status": "ready_for_qa",
        "artifacts": {
            "source_paths": list(SOURCE_FILES),
            "video_path": video_rel,
            "keyframe_paths": keyframes,
        },
        "checks": [
            {"name": "scene_validation", "result": "pass",
             "detail": "Executed scripts/validate.py against checked-out Pilot scene"},
            {"name": "render_completed", "result": "pass",
             "detail": "Executed scripts/render.py; output exists"},
            {"name": "video_probe", "result": "pass",
             "detail": "ffprobe confirmed H.264, no audio, resolution, FPS, duration and frame count"},
        ],
        "deviations": [],
        "notes": "CI-produced silent Stage B preview; no human director approval, audio lock or independent visual QA. Attempt=1 within this CI build, NOT the historical Muse attempt number.",
    }
    errors = validate_bundle(spec, delivery)
    if errors:
        raise ValueError("Generated delivery invalid: " + "; ".join(errors))
    (root / "delivery.json").write_text(
        json.dumps(delivery, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    evidence_dir = root / "qa_evidence"
    create_evidence(spec_path, video, evidence_dir, interval=1.0,
                    focus=(5.3,), radius=1.0, focus_step=0.2)
    problems = verify_evidence(evidence_dir, video, spec_path)
    if problems:
        raise ValueError("Timed frame evidence corruption: " + "; ".join(problems))

    package_root = root / "qa_review"
    if role_pack_main([
        "qa", "--spec", str(spec_path), "--delivery", str(root / "delivery.json"),
        "--video", str(video), "--evidence-dir", str(evidence_dir),
        "--out", str(package_root),
    ]):
        raise ValueError("Failed to create portable QA review ZIP")
    # The standalone QA zip includes video, timed frames and pending QA template.
    # No model was contacted and no QA decision has been issued.

    log.append("NOTE: Rendering and metadata validation only; not independent visual QA.")
    (root / "build_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    extras = [
        "director_spec.json",
        *SOURCE_FILES,
        "build_log.txt",
        "qa_review.zip",
        "qa_evidence/evidence_index.json",
    ]
    for contact in sorted(evidence_dir.glob("contact_sheet_*.jpg")):
        extras.append(str(contact.relative_to(root)))
    manifest = create_manifest(
        spec, delivery, root, backend="actions",
        artifact_name=artifact_name, run_url=run_url, extras=extras,
    )
    (root / "media_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    errors = verify_manifest(manifest, root, spec, delivery)
    if errors:
        raise ValueError("Generated media manifest invalid: " + "; ".join(errors))
    print("CREATED CI review artifact", root, artifact_name, source_sha)
    print("NOTE: QA template remains pending; visual review requires another model or person.")
    return manifest


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", default=str(ROOT / "examples/workflow_orders_spec.json"))
    p.add_argument("--scene", default=str(ROOT / "work/orders_pilot/scene.json"))
    p.add_argument("--source-sha", required=True)
    p.add_argument("--artifact-root", required=True)
    p.add_argument("--artifact-name", required=True)
    p.add_argument("--run-url", required=True)
    args = p.parse_args(argv)
    try:
        build(args.spec, args.scene, args.source_sha, args.artifact_root,
              args.artifact_name, args.run_url)
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
