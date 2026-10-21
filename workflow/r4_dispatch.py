"""Explicit human-approved R0 -> R4 rework dispatch. Never runs R4 code."""
import hashlib
import json
from pathlib import Path

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dispatch(workdir, *, selected_ids, approved_by, inbox, artifact_root, repository=None,
             dry_run=False, runner=None, allowed_files=None, max_runtime_seconds=1200):
    from workflow import orchestrator as r0
    from studio.r4_runner import valid_path
    root, state, spec = r0.load_state(workdir)
    if state["status"] != "review_pending":
        raise ValueError("Rework dispatch requires review_pending state")
    if not approved_by or len(approved_by.strip()) < 2:
        raise ValueError("Explicit approval identity required")
    if not selected_ids or len(set(selected_ids)) != len(selected_ids):
        raise ValueError("Select unique approved finding IDs")
    draft_path = root / "r4_rework_draft" / "rework_task_candidate.json"
    task = r0.read_json(draft_path)
    if task.get("status") != "draft_unverified":
        raise ValueError("Expected unverified R5 task candidate")
    source_candidate = root / "r5_deepseek" / "findings_candidate.json"
    if not source_candidate.is_file() or digest(source_candidate) != task["source_candidate_sha256"]:
        raise ValueError("R4 candidate source evidence was changed or missing")
    original = r0.read_json(source_candidate)
    delivery = r0.read_json(root / "delivery.json")
    base = Path(artifact_root).resolve()
    video = (base / delivery["artifacts"]["video_path"]).resolve()
    if not video.is_relative_to(base) or not video.is_file() or digest(video) != task["video_sha256"]:
        raise ValueError("Stale or missing R4 source MP4")
    if (task["spec_sha256"] != state["spec_sha256"] or
            task["implementation_commit"] != delivery["implementation_commit"] or
            task["spec_revision"] != spec["revision"]):
        raise ValueError("Stale R4 candidate: version binding mismatch")
    if state.get("production_mode") == "formal":
        if not state.get("production_lock_hashes"):
            raise ValueError("Missing formal production locks")
        lock_hashes = state["production_lock_hashes"]
    else:
        lock_hashes = None
    if (task["video_sha256"] != original["video_sha256"]
            or task["implementation_commit"] != original["implementation_commit"]
            or task["spec_sha256"] != original["spec_sha256"]):
        raise ValueError("R4 task does not match original R5 evidence")
    all_findings = {f["id"]: f for f in task["findings"]}
    original_findings = {f["id"]: f for f in original["findings"]}
    if all_findings != original_findings:
        raise ValueError("R4 task findings differ from R5 evidence")
    if len(all_findings) != len(task["findings"]) or any(i not in all_findings for i in selected_ids):
        raise ValueError("Approved finding IDs not present in candidate")
    chosen = [f for f in task["findings"] if f["id"] in selected_ids]
    if not allowed_files or any(not valid_path(f) for f in allowed_files):
        raise ValueError("Specify safe --allow-file entries explicitly")
    if not 30 <= max_runtime_seconds <= 1800:
        raise ValueError("Invalid R4 timeout")
    out = Path(inbox).resolve()
    if out.exists():
        raise ValueError("R4 task destination exists; refusing overwrite or duplicate dispatch")
    if (out == root or out.is_relative_to(root)):
        raise ValueError("Use a separate R4 executor inbox, not the R0 workspace")
    envelope = {
        "schema_version": "1.0",
        "kind": "r4_rework_assignment",
        "status": "approved_for_rework_only",
        "approval": {"approved_by": approved_by.strip(),
                     "scope": "selected_visual_fixes_only",
                     "explicit_cli_authorization": True},
        "project_id": state["project_id"],
        "spec_id": state["spec_id"],
        "spec_revision": state["spec_revision"],
        "spec_sha256": state["spec_sha256"],
        "source_implementation_commit": delivery["implementation_commit"],
        "source_video_sha256": task["video_sha256"],
        "source_task_sha256": digest(draft_path),
        "production_lock_hashes": lock_hashes,
        "execution_policy": {"allowed_files": list(dict.fromkeys(allowed_files)),
                             "max_runtime_seconds": max_runtime_seconds},
        "approved_finding_ids": selected_ids,
        "findings": chosen,
        "required_delivery": ["new_implementation_commit", "new_stage_d_render",
                              "new_media_manifest", "new_independent_r5_review"],
        "prohibited": ["alter_script_lock", "alter_voice_lock", "change_approved_av_cues",
                       "reuse_old_r5_pass", "publish"],
    }
    lines = [
        "# R4 implementation assignment — explicitly approved for visual rework",
        "", "Approval: " + approved_by.strip(),
        "Base commit: " + delivery["implementation_commit"],
        "Spec SHA256: " + state["spec_sha256"],
        "Source video SHA256: " + task["video_sha256"],
        "Do not change narration, storyboards, event cues, Script Lock or Voice Lock.",
        "Use a separate worktree/branch; do not overwrite prior delivery artifacts.",
        "Produce a NEW implementation commit, render and request independent R5.",
        "No R5 PASS or R7 publishing authorization.", ""
    ]
    for f in chosen:
        lines += ["## " + f["id"] + " [" + f["severity"] + "]",
                  "Time: " + str(f.get("timestamp_s","unknown")),
                  "Expected: " + f["expected"],
                  "Observed: " + f["observed"],
                  "Evidence (verify in full video): " + f["evidence"],
                  "Fix: " + f["fix_request"], ""]
    markdown = "\n".join(lines)
    if dry_run:
        return {"dry_run": True, "selected": selected_ids,
                "destination": str(out), "github_issue_requested": bool(repository),
                "r0_state_unchanged": True}
    # GitHub issue is explicitly opted in; do it before writing local task,
    # so a remote failure cannot appear as a successful local dispatch.
    issue_url = None
    if repository:
        if not r0.REPOSITORY.fullmatch(repository):
            raise ValueError("Invalid owner/repo")
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            body = Path(temp) / "body.md"
            body.write_text(markdown, encoding="utf-8")
            import subprocess
            issue_url = r0.gh(["issue","create","--repo",repository,
                               "--title","R4 rework: " + state["spec_id"] +
                               " (" + ",".join(selected_ids) + ")",
                               "--body-file",str(body)],
                              runner if runner is not None else subprocess.run)
        if not issue_url.startswith("https://github.com/"):
            raise ValueError("Unexpected GitHub issue URL")
    out.mkdir(parents=True)
    envelope["github_issue_url"] = issue_url
    r0.write_json(out / "assignment.json", envelope)
    r0.write_text(out / "TASK.md", markdown)
    return {"status": "dispatched_for_rework", "inbox": str(out),
            "assignment": str(out / "assignment.json"),
            "task": str(out / "TASK.md"),
            "issue_url": issue_url, "r0_state_unchanged": True}
