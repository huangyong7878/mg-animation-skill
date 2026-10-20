#!/usr/bin/env python3
"""R4 Stage D OFFLINE build. Only human-approved director + locked real voice.

Never generates/approves narration, calls an API, marks independent QA passed,
or publishes. Pilot 001 only; media bytes/versions are immutable and hashed.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.primitives.orderflow import PILOT_EVENT_SECONDS
from workflow.av_sync_contract import validate_av_cues
from workflow.build_stagec_artifact import check_preview_video
from workflow.check_handoff import canonical_digest, required_checks, validate_bundle
from workflow.media_manifest import create_manifest, verify_manifest
from workflow.production_gates import verify_production_locks

SHA = re.compile(r"^[0-9a-f]{40}$")
LOCKED = ("narration.txt", "media/voice.wav", "media/timings.json")
SOURCES = ("source/scene.json", "source/narration_plan.json",
           "source/approved_av_cues.json", "source/storyboard.md")
APPROVALS = ("approvals/script_lock.json", "approvals/voice_lock.json")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            value.update(chunk)
    return value.hexdigest()


def command(args):
    result = subprocess.run([str(arg) for arg in args], cwd=ROOT,
                            capture_output=True, text=True, check=True, timeout=180)
    return result.stdout


def verify_lock(spec, scene, plan, cues, script, wav, timing, *,
                storyboard, plan_path, cue_path, script_lock, voice_lock):
    problems = validate_bundle(spec)
    if problems:
        raise ValueError("Invalid director spec: " + "; ".join(problems))
    if (spec["project_id"], spec["spec_id"]) != ("orders_two_routes", "orders_shot_001"):
        raise ValueError("Only the Pilot 001 approved director spec is supported")
    if (spec["approval"]["status"] != "approved"
            or not spec["approval"].get("approved_by")
            or not spec["approval"].get("approved_at")):
        raise ValueError("Stage D requires explicit human director approval")
    # R2→R3 script/storyboard approval comes before voice approval; both
    # are required before formal R4 can produce Stage D.
    verify_production_locks(
        spec, plan, cues, script, storyboard, plan_path, cue_path,
        wav, timing, script_lock, voice_lock)
    narration = spec["narration"]
    if narration["status"] != "locked":
        raise ValueError("Stage D refuses draft narration")
    if tuple(narration.get(k) for k in ("script_path", "audio_path",
                                      "timings_path")) != LOCKED:
        raise ValueError("Pilot Stage D uses fixed locked-media paths")
    if narration["alignment"] != "sentence":
        raise ValueError("Pilot D requires measured sentence timing")
    for path, key in ((wav, "audio_sha256"), (timing, "timings_sha256")):
        if not Path(path).is_file() or digest(path) != narration.get(key):
            raise ValueError("Locked " + key + " mismatch")
    canvas, output = scene["canvas"], spec["output"]
    if ((canvas["width"], canvas["height"], canvas["fps"]) !=
            (output["width"], output["height"], output["fps"])
            or abs(canvas["duration"] - output["duration_s"]) > .001):
        raise ValueError("Scene does not match approved duration/canvas")
    shots = scene.get("scenes", [])
    if (len(shots) != 1 or shots[0].get("id") != spec["shots"][0]["id"]
            or not any(e.get("type") == "orderflow"
                       for e in shots[0].get("elements", []))):
        raise ValueError("Scene is not the approved Pilot orderflow shot")
    if plan.get("test_only") is not False:
        raise ValueError("Stage D refuses unapproved Stage C test narration")
    seg = plan.get("narration", {}).get("segments", [])
    if len(seg) != 3:
        raise ValueError("Pilot final narration needs three cues")
    if Path(script).read_text(encoding="utf-8").strip() != "\n".join(
            str(x["text"]).strip() for x in seg):
        raise ValueError("Locked script does not match narrated cue words")
    timings = load(timing)
    if (abs(timings["duration"] - output["duration_s"]) > .05
            or len(timings["segments"]) != 3):
        raise ValueError("Locked timings differ from video duration/cues")
    event_report = validate_av_cues(
        spec, plan, PILOT_EVENT_SECONDS, cues, timings=timings,
        expected_status="approved")
    if [c["segment_id"] for c in event_report["cues"]] != [
            "intro", "out_of_stock", "in_stock"]:
        raise ValueError("Final B-before-A cue order mismatch")
    with wave.open(str(wav), "rb") as sound:
        if (sound.getnchannels(), sound.getsampwidth(),
                sound.getframerate()) != (1, 2, 22050):
            raise ValueError("Pilot final audio must be mono 22050Hz PCM16 WAV")
        if abs(sound.getnframes() / 22050 - output["duration_s"]) > .04:
            raise ValueError("Final WAV duration mismatch")
        if not any(sound.readframes(sound.getnframes())):
            raise ValueError("Final WAV is silent")
    return event_report


def build(spec_path, scene_path, plan_path, cue_path, script_path,
          audio_path, timings_path, source_sha, output_root, *,
          storyboard_path, script_lock_path, voice_lock_path):
    if not SHA.fullmatch(source_sha):
        raise ValueError("Full Git SHA required")
    checkout = command(["git", "rev-parse", "HEAD"]).strip()
    if checkout != source_sha:
        raise ValueError("R4 implementation commit does not match checkout")
    out = Path(output_root).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite existing Stage D media")
    spec, scene, plan, cues = map(load, (spec_path, scene_path,
                                        plan_path, cue_path))
    script_lock = load(script_lock_path)
    voice_lock = load(voice_lock_path)
    event_report = verify_lock(
        spec, scene, plan, cues, script_path, audio_path, timings_path,
        storyboard=storyboard_path, plan_path=plan_path, cue_path=cue_path,
        script_lock=script_lock, voice_lock=voice_lock)
    pairs = [
        (script_path, LOCKED[0]), (audio_path, LOCKED[1]),
        (timings_path, LOCKED[2]), (scene_path, SOURCES[0]),
        (plan_path, SOURCES[1]), (cue_path, SOURCES[2]),
        (storyboard_path, SOURCES[3]),
        (script_lock_path, APPROVALS[0]), (voice_lock_path, APPROVALS[1]),
    ]
    for source, relative in pairs:
        dest = out / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    save(out / "director_spec.json", spec)
    save(out / "av_sync_report.json", event_report)
    command([sys.executable, "scripts/validate.py", out / SOURCES[0]])
    video_rel = "media/stage_d_final.mp4"
    command([sys.executable, "scripts/render.py", out / SOURCES[0],
             "--audio", out / LOCKED[1], "--timings", out / LOCKED[2],
             "--out", out / video_rel])
    meta = json.loads(command([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height,nb_frames",
        "-of", "json", out / video_rel]))
    check_preview_video(meta, spec)
    frames = []
    for second in (2.0, 6.4, 8.5, 10.6):
        relative = "media/keyframes/t%08d.png" % int(second * 1000)
        (out / relative).parent.mkdir(parents=True, exist_ok=True)
        command(["ffmpeg", "-v", "error", "-y", "-ss", second, "-i",
                 out / video_rel, "-frames:v", "1", out / relative])
        if not (out / relative).is_file() or (out / relative).stat().st_size == 0:
            raise ValueError("Video QA evidence keyframe not generated")
        frames.append(relative)
    delivery = {
        "schema_version": "1.0",
        "project_id": spec["project_id"], "spec_id": spec["spec_id"],
        "spec_revision": spec["revision"],
        "spec_sha256": canonical_digest(spec),
        "implementation_commit": source_sha,
        "attempt": 1, "stage": "D", "status": "ready_for_qa",
        "artifacts": {
            "source_paths": list(SOURCES), "video_path": video_rel,
            "audio_path": LOCKED[1], "timings_path": LOCKED[2],
            "keyframe_paths": frames,
        },
        "checks": [
            {"name": "script_storyboard_and_voice_preproduction_locks",
             "result": "pass",
             "detail": "Separate human-declared script/storyboard and voice approvals bind original text/plan/cues/storyboard plus final audio/timings; signer identity not cryptographically verified."},
            {"name": "locked_voice_and_director", "result": "pass",
             "detail": "Approved spec metadata and WAV/timing hashes match. Human identity not cryptographically authenticated."},
            {"name": "av_event_timings", "result": "pass",
             "detail": "Approved cue contract agrees with measured voice and declared R4 event times; not an independent AV review."},
            {"name": "final_mp4", "result": "pass",
             "detail": "Real H264/AAC duration, resolution and frames checked with ffprobe."},
        ], "deviations": [],
        "notes": "Ready for independent Stage D QA only; NOT approved for release.",
    }
    problems = validate_bundle(spec, delivery)
    if problems:
        raise ValueError("Stage D delivery invalid: " + "; ".join(problems))
    save(out / "delivery.json", delivery)
    qa = {
        "schema_version": "1.0", "project_id": spec["project_id"],
        "spec_id": spec["spec_id"], "spec_revision": spec["revision"],
        "spec_sha256": canonical_digest(spec),
        "implementation_commit": source_sha,
        "reviewer": {"name": "NOT_REVIEWED", "independent_context": False},
        "decision": "pending",
        "checks": [
            {"shot_id": shot, "requirement_id": req, "result": "needs_review",
             "evidence": "PENDING real independent viewing and listening"}
            for shot, req in sorted(required_checks(spec))
        ],
        "findings": [],
        "summary": "QA template only. No independent Stage D AV review was performed.",
    }
    if validate_bundle(spec, delivery, qa):
        raise ValueError("QA template schema invalid")
    save(out / "qa_template.json", qa)
    (out / "release_checklist.md").write_text(
        "# Stage D: human release checklist (NOT APPROVED)\n\n"
        "- [ ] Independent R5 inspected full video AND real narration audio\n"
        "- [ ] R5 supplied full qa_report.json for every director requirement\n"
        "- [ ] R0 received delivery and recorded independent R5 QA\n"
        "- [ ] release-check passes against the immutable media bundle\n"
        "- [ ] R7 independently approves final video and permanent archive\n",
        encoding="utf-8")
    (out / "build_log.txt").write_text(
        "Stage D R4 offline render; no TTS/model call and no release approval.\n",
        encoding="utf-8")
    extras = ("director_spec.json", "narration.txt", "av_sync_report.json",
              *APPROVALS,
              "qa_template.json", "release_checklist.md", "build_log.txt")
    manifest = create_manifest(spec, delivery, out, backend="local", extras=extras)
    save(out / "media_manifest.json", manifest)
    errors = verify_manifest(manifest, out, spec, delivery)
    if errors:
        raise ValueError("Invalid final media hashes: " + "; ".join(errors))
    # The supplied QA is pending: publishing must remain blocked.
    if not validate_bundle(spec, delivery, qa, release=True, artifact_root=out):
        raise ValueError("Unsafe: pending QA unexpectedly passed release gate")
    print("STAGE D READY FOR INDEPENDENT QA — RELEASE BLOCKED:", out)
    return delivery


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("spec", "scene", "plan", "cue-contract", "script",
                 "audio", "timings", "source-sha", "out",
                 "storyboard", "script-lock", "voice-lock"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        build(args.spec, args.scene, args.plan, args.cue_contract, args.script,
              args.audio, args.timings, args.source_sha, args.out,
              storyboard_path=args.storyboard, script_lock_path=args.script_lock,
              voice_lock_path=args.voice_lock)
    except (ValueError, KeyError, OSError, RuntimeError, json.JSONDecodeError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired,
            wave.Error) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
