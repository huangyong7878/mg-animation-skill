#!/usr/bin/env python3
"""Two immutable preproduction gates, BEFORE formal R4 work (no network or approval).

R2 writes narration/storyboard; R3 supplies shot/cue contract; a human
actually approves script_lock; voice is synthesized/tested next; a human
listens and approves voice_lock; only then R0 may dispatch *formal* R4.
This validates claimed human approvals + SHA256, not signer's identity.
Existing Stage B/C experiments deliberately do not require production locks.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jsonschema import Draft202012Validator

from workflow.av_sync_contract import validate_av_cues
from workflow.check_handoff import canonical_digest, schema_errors
from scripts.primitives.orderflow import PILOT_EVENT_SECONDS

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def director_storyboard_digest(spec):
    """Stable through the later voice lock; a real creative/shot change invalidates it."""
    return canonical_digest({
        "project_id": spec["project_id"],
        "spec_id": spec["spec_id"],
        "revision": spec["revision"],
        "creative": spec["creative"],
        "output": spec["output"],
        "shots": spec["shots"],
        "narration_script_path": spec["narration"]["script_path"],
        "narration_alignment": spec["narration"]["alignment"],
    })


def validate_structure(filename, payload):
    schema = read(ROOT / "contracts" / filename)
    problems = list(Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).iter_errors(payload))
    if problems:
        raise ValueError("Invalid formal approval: " + "; ".join(p.message for p in problems))


def verify_script_lock(spec, plan, cues, script_path, storyboard_path, plan_path,
                       cues_path, lock):
    validate_structure("script_lock.schema.json", lock)
    if schema_errors("spec", spec):
        raise ValueError("Formal script lock requires a schema-valid director spec")
    for key, wanted in (
            ("project_id", spec["project_id"]), ("spec_id", spec["spec_id"]),
            ("spec_revision", spec["revision"])):
        if lock[key] != wanted:
            raise ValueError("Script lock references stale director " + key)
    for key, path in (
            ("script_sha256", script_path),
            ("storyboard_sha256", storyboard_path),
            ("plan_sha256", plan_path), ("cues_sha256", cues_path)):
        if digest(path) != lock[key]:
            raise ValueError("Script/storyboard lock hash mismatch: " + key)
    if lock["director_storyboard_sha256"] != director_storyboard_digest(spec):
        raise ValueError("Changed director storyboard invalidates script lock")
    if plan.get("test_only") is not False:
        raise ValueError("Formal script must not be a Stage C test_only narration")
    lines = [segment.get("text", "").strip()
             for segment in plan.get("narration", {}).get("segments", [])]
    if not lines or "\n".join(lines) != Path(script_path).read_text(encoding="utf-8").strip():
        raise ValueError("Script lock words differ from exact narration plan")
    if not Path(storyboard_path).read_text(encoding="utf-8").strip():
        raise ValueError("Empty storyboard cannot be approved")
    # R3 contract locks both semantic order and renderer-event meanings,
    # before a TTS provider has even been selected.
    validate_av_cues(spec, plan, PILOT_EVENT_SECONDS, cues, expected_status="approved")
    return canonical_digest(lock)


def verify_voice_lock(spec, script_lock_digest, wav_path, timings_path, voice_lock):
    validate_structure("voice_lock.schema.json", voice_lock)
    if voice_lock["script_lock_sha256"] != script_lock_digest:
        raise ValueError("Voice lock based on stale script/storyboard version")
    for path, key in ((wav_path, "audio_sha256"),
                      (timings_path, "timings_sha256")):
        if digest(path) != voice_lock[key]:
            raise ValueError("Voice lock hash mismatch: " + key)
        if spec["narration"].get(key) != voice_lock[key]:
            raise ValueError("Director locked audio/timing hash is stale: " + key)
    if spec["approval"]["status"] != "approved" or spec["narration"]["status"] != "locked":
        raise ValueError("Formal R4 requires director approved AND narration locked")
    return canonical_digest(voice_lock)


def verify_production_locks(spec, plan, cues, script_path, storyboard_path,
                            plan_path, cues_path, wav_path, timings_path,
                            script_lock, voice_lock):
    script_digest = verify_script_lock(spec, plan, cues, script_path,
                                       storyboard_path, plan_path, cues_path,
                                       script_lock)
    voice_digest = verify_voice_lock(spec, script_digest, wav_path,
                                     timings_path, voice_lock)
    return {"script_lock_digest": script_digest, "voice_lock_digest": voice_digest}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=("script", "voice"), required=True)
    for name in ("spec", "plan", "cues", "script", "storyboard", "script-lock",
                 "plan-path", "cues-path"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--audio")
    p.add_argument("--timings")
    p.add_argument("--voice-lock")
    a = p.parse_args(argv)
    try:
        spec, plan, cues = (read(a.spec), read(a.plan), read(a.cues))
        script = read(a.script_lock)
        script_digest = verify_script_lock(
            spec, plan, cues, a.script, a.storyboard,
            a.plan_path, a.cues_path, script)
        if a.stage == "voice":
            if not all((a.audio, a.timings, a.voice_lock)):
                raise ValueError("Voice lock requires audio, timings, voice-lock")
            voice_digest = verify_voice_lock(
                spec, script_digest, a.audio, a.timings, read(a.voice_lock))
            print("PASS: human-declared voice lock and fixed script:",
                  script_digest, voice_digest)
        else:
            print("PASS: human-declared script/storyboard lock:", script_digest)
    except (KeyError, ValueError, OSError, TypeError, json.JSONDecodeError) as exc:
        p.exit(1, "BLOCKED: " + str(exc) + "\n")
    print("NOTICE: Cannot cryptographically verify approver identity or media quality.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
