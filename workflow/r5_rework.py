"""R0 converts source-bound, unverified R5 observations into R4 draft tasks.

This route never edits review state, files under locked approvals, or qa_report.json.
It cannot count as independent full-audiovisual QA or authorize release.
"""
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "r5_rework_candidate.schema.json"

def filehash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare_rework(workdir, candidate_path, artifact_root):
    from workflow.orchestrator import load_state, read_json, write_json, write_text
    root, state, spec = load_state(workdir)
    if state["status"] != "review_pending":
        raise ValueError("Rework draft requires review_pending R0 state")
    candidate_path = Path(candidate_path).resolve()
    candidate = read_json(candidate_path)
    schema = read_json(SCHEMA)
    errors = sorted(Draft202012Validator(schema).iter_errors(candidate), key=lambda e: list(map(str,e.path)))
    if errors:
        raise ValueError("Invalid R5 finding candidate: " + "; ".join(e.message for e in errors))
    delivery = read_json(root / "delivery.json")
    if candidate["spec_sha256"] != state["spec_sha256"]:
        raise ValueError("R5 candidate based on stale director spec")
    if candidate["implementation_commit"] != delivery["implementation_commit"]:
        raise ValueError("R5 candidate based on stale implementation")
    if candidate["scope"] != "sampled_frames_only":
        raise ValueError("Unsupported R5 candidate evidence scope")
    video = (Path(artifact_root).resolve() / delivery["artifacts"]["video_path"]).resolve()
    if not video.is_relative_to(Path(artifact_root).resolve()) or not video.is_file():
        raise ValueError("Missing delivered video for source-bound R5 findings")
    if candidate["video_sha256"] != filehash(video):
        raise ValueError("R5 candidate video hash mismatch")
    valid_shots = {s["id"] for s in spec["shots"]}
    if any(f["shot_id"] not in valid_shots for f in candidate["findings"]):
        raise ValueError("Unknown shot ID in R5 findings")
    ids = [f["id"] for f in candidate["findings"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate R5 finding ID")
    out = root / "r4_rework_draft"
    if out.exists():
        raise ValueError("Refusing to overwrite existing R4 rework draft")
    out.mkdir()
    ordered = sorted(candidate["findings"],
                     key=lambda f: ({"P0":0,"P1":1,"P2":2}[f["severity"]],f.get("timestamp_s",9999),f["id"]))
    task = {
        "schema_version": "1.0", "status": "draft_unverified",
        "r5_scope": candidate["scope"], "requires_human_evidence_review": True,
        "audio_reviewed": False, "full_motion_reviewed": False,
        "project_id": spec["project_id"], "spec_id": spec["spec_id"],
        "spec_revision": spec["revision"], "spec_sha256": state["spec_sha256"],
        "implementation_commit": delivery["implementation_commit"],
        "video_sha256": candidate["video_sha256"], "source_candidate_sha256": filehash(candidate_path),
        "locked_content_policy": "Do not change narration, storyboard, AV cue, Script Lock or Voice Lock",
        "findings": ordered,
    }
    lines = ["# R4 rework task — DRAFT / requires evidence review", "",
             "R5 scope: sampled frames ONLY; not full video motion/audio review.",
             "No R5 PASS, state transition, or release authorization.",
             "Source implementation: " + task["implementation_commit"],
             "Director spec SHA256: " + task["spec_sha256"],
             "Video SHA256: " + task["video_sha256"],
             "Do not modify script/voice locks, narration, storyboard or approved AV events.",
             "Produce a NEW commit, render NEW immutable Stage D delivery, then independent R5 review.", ""]
    if not ordered:
        lines += ["No actionable candidate findings. Do not treat this as PASS."]
    for f in ordered:
        lines += ["## " + f["id"] + " — " + f["severity"] + " / " + f["shot_id"],
                  "Time: " + (str(f["timestamp_s"]) + " s" if "timestamp_s" in f else "unspecified"),
                  "Expected: " + f["expected"], "Observed: " + f["observed"],
                  "Evidence: " + f["evidence"], "Fix request: " + f["fix_request"], ""]
    write_json(out / "rework_task_candidate.json", task)
    write_text(out / "rework_task_candidate.md", "\n".join(lines))
    return {"status": "draft_unverified",
            "task_json": str(out / "rework_task_candidate.json"),
            "task_markdown": str(out / "rework_task_candidate.md"),
            "r0_state_unchanged": True, "finding_count": len(ordered)}
