#!/usr/bin/env python3
"""GitHub-backed human-in-the-loop orchestrator for MG animation handoffs.

The CLI prepares reproducible prompts and exchanges files. It DOES NOT invoke
Muse, DeepSeek or a reviewer model, and never merges or publishes videos.
Writes to GitHub only when the operator explicitly calls publish or feedback.
"""
import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

try:
    from workflow.check_handoff import canonical_digest, required_checks, validate_bundle
    from workflow.production_gates import verify_production_locks, read as read_lock
except ModuleNotFoundError:
    from check_handoff import canonical_digest, required_checks, validate_bundle
    from production_gates import verify_production_locks, read as read_lock


ALLOWED_EXECUTORS = ("muse", "deepseek", "other")
HEX_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
REPOSITORY = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")
PR_REFERENCE = re.compile(r"^(?:[1-9][0-9]*|https://github[.]com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/pull/[1-9][0-9]*)$")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def load_state(workdir):
    root = Path(workdir).resolve()
    state_file = root / "state.json"
    if not state_file.exists():
        raise ValueError("Workspace not initialized. Run prepare first.")
    return root, read_json(state_file), read_json(root / "director_spec.json")


def save_state(root, state):
    write_json(root / "state.json", state)


def ensure_files(root, files, label):
    """Check local artifact paths, reject escaping paths and empty files."""
    base = Path(root).resolve()
    for item in files:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label}: empty path")
        candidate = (base / item).resolve()
        if not candidate.is_relative_to(base):
            raise ValueError(f"{label}: path outside artifact root: {item}")
        if not candidate.is_file() or candidate.stat().st_size == 0:
            raise ValueError(f"{label}: missing/empty file: {item}")


def executor_brief(spec, digest, executor):
    lines = [
        "# MG animation execution task",
        "",
        "Executor: " + executor,
        "Project: " + spec["project_id"],
        "Specification: " + spec["spec_id"] + " revision " + str(spec["revision"]),
        "Canonical spec SHA256: " + digest,
        "Narration: " + spec["narration"]["status"] + " (draft means silent prototype only)",
        "",
        "## Non-negotiable",
        "Read director_spec.json and implement all required visual elements and motion.",
        "Preserve order identity, continuous state transitions and the dynamic model.",
        "Do not silently downgrade requirements; report blockers and deviations.",
        "Render actual video and sample keyframes. Do not claim unperformed tests.",
        "Use a feature branch and PR. Never push straight to main or merge.",
        "Create delivery.json per contracts/delivery.schema.json with the current",
        "spec_sha256 and the actual HEAD commit SHA; no placeholder commit IDs.",
        "Include source_paths, video_path, keyframe_paths and executed checks.",
        "",
        "## Shot acceptance",
    ]
    for shot in spec["shots"]:
        lines.extend(["", "### " + shot["id"], shot["visual_description"]])
        if shot.get("dynamic_model"):
            lines.append("Dynamic model: " + shot["dynamic_model"])
        contract = shot["visual_contract"]
        for item in contract["must_show"]:
            lines.append("- SHOW " + item["id"] + ": " + item["desc"])
        for item in contract.get("continuous_motion", []):
            lines.append("- MOTION " + item["id"] + ": " + item["desc"])
        for item in shot["acceptance"]:
            lines.append("- ACCEPT " + item)
    lines += [
        "",
        "## Submission",
        "Provide source, actual rendered MP4, keyframes, delivery.json and PR URL.",
        "QA will be performed by a separate strong-model review context.",
    ]
    return "\n".join(lines)


def prepare(spec_path, workdir, executor="muse", formal_assets=None):
    if executor not in ALLOWED_EXECUTORS:
        raise ValueError("Unsupported executor")
    root = Path(workdir).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("Workspace is not empty; refusing to overwrite an existing run")
    spec = read_json(spec_path)
    errors = validate_bundle(spec)
    if errors:
        raise ValueError("Invalid director specification: " + "; ".join(errors))
    # Formal R4 dispatch is impossible without BOTH previous human-declared
    # preproduction approvals. Prototype work remains backward compatible.
    hashes = None
    if formal_assets is not None:
        keys = ("script", "storyboard", "plan", "cues",
                "audio", "timings", "script_lock", "voice_lock")
        if any(not formal_assets.get(k) for k in keys):
            raise ValueError("Formal R4 requires script/storyboard approval and voice approval assets")
        plan, cues = read_lock(formal_assets["plan"]), read_lock(formal_assets["cues"])
        hashes = verify_production_locks(
            spec, plan, cues, formal_assets["script"],
            formal_assets["storyboard"], formal_assets["plan"],
            formal_assets["cues"], formal_assets["audio"],
            formal_assets["timings"], read_lock(formal_assets["script_lock"]),
            read_lock(formal_assets["voice_lock"]))
    if formal_assets is None and (
            spec["approval"]["status"] == "approved"
            or spec["narration"]["status"] == "locked"):
        raise ValueError("Approved/locked production requires --formal preproduction locks")
    digest = canonical_digest(spec)
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "director_spec.json", spec)
    task = executor_brief(spec, digest, executor)
    if hashes:
        task += ("\n\n## FORMAL R4: upstream production locks verified\n"
                 "R2/R3 approved script/storyboard and selected voice are fixed.\n"
                 "No rewriting dialogue or reinterpreting beats at Stage D.\n"
                 "Script lock digest: " + hashes["script_lock_digest"] + "\n"
                 "Voice lock digest: " + hashes["voice_lock_digest"] + "\n"
                 "Changing any locked asset requires NEW human approval and fresh QA.\n")
        for key, filename in (
                ("script_lock", "script_lock.json"),
                ("voice_lock", "voice_lock.json")):
            shutil.copyfile(formal_assets[key], root / filename)
    write_text(root / "executor_task.md", task)
    state = {
        "version": "1.0", "project_id": spec["project_id"],
        "spec_id": spec["spec_id"], "spec_revision": spec["revision"],
        "spec_sha256": digest, "executor": executor, "status": "prepared",
        "attempt": 0, "issue_url": None, "implementation_pr_url": None,
        "implementation_commit": None, "history": [],
        "production_mode": "formal" if hashes else "prototype",
        "production_lock_hashes": hashes,
    }
    save_state(root, state)
    return state


def gh(command, runner=subprocess.run):
    """Execute gh safely with an argument array and no shell."""
    try:
        result = runner(["gh", *command], check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise ValueError("GitHub CLI gh is not installed or on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError("GitHub CLI failed: " + (exc.stderr or str(exc))) from exc
    return result.stdout.strip()


def publish(workdir, repository, dry_run=False, runner=subprocess.run):
    root, state, spec = load_state(workdir)
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("Repository must be owner/name")
    if state["status"] != "prepared":
        raise ValueError("Task can only be published once from prepared state")
    command = ["issue", "create", "--repo", repository,
               "--title", "MG implementation: " + spec["creative"]["title"],
               "--body-file", str(root / "executor_task.md")]
    if dry_run:
        return {"dry_run": True, "command": ["gh", *command]}
    issue_url = gh(command, runner)
    if not re.fullmatch(r"https://github[.]com/[^/]+/[^/]+/issues/[0-9]+", issue_url):
        raise ValueError("GitHub returned an unexpected issue URL; state not updated")
    state["issue_url"] = issue_url
    state["status"] = "published"
    state["history"].append({"event": "issue_created", "url": issue_url})
    save_state(root, state)
    return {"issue_url": issue_url}


def read_pr_head(repository, reference, runner=subprocess.run):
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("Repository must be owner/name")
    if not PR_REFERENCE.fullmatch(str(reference)):
        raise ValueError("PR reference must be a number or valid GitHub PR URL")
    data = json.loads(gh(["pr", "view", str(reference), "--repo", repository,
                          "--json", "headRefOid,url,state"], runner))
    if not HEX_SHA.fullmatch(data.get("headRefOid", "")):
        raise ValueError("PR has no valid head commit")
    if data.get("state") != "OPEN":
        raise ValueError("Implementation PR must be open")
    return data


def check_formal_artifact(root, state, spec, artifact_root):
    """Formal R0 gate: reject a changed script/voice even when R4 says 'pass'."""
    if state.get("production_mode") != "formal":
        return
    base = Path(artifact_root).resolve()
    files = {
        "script": "narration.txt",
        "storyboard": "source/storyboard.md",
        "plan": "source/narration_plan.json",
        "cues": "source/approved_av_cues.json",
        "audio": "media/voice.wav",
        "timings": "media/timings.json",
        "script_lock": "approvals/script_lock.json",
        "voice_lock": "approvals/voice_lock.json",
    }
    ensure_files(base, files.values(), "Formal R4")
    inputs = {key: base / relative for key, relative in files.items()}
    approvals = verify_production_locks(
        spec, read_lock(inputs["plan"]), read_lock(inputs["cues"]),
        inputs["script"], inputs["storyboard"], inputs["plan"],
        inputs["cues"], inputs["audio"], inputs["timings"],
        read_lock(inputs["script_lock"]), read_lock(inputs["voice_lock"]))
    if approvals != state.get("production_lock_hashes"):
        raise ValueError("R4 changed the previously approved script/voice version")
    # Compare original R0 lock records, not just hash data in the delivery.
    for key in ("script_lock", "voice_lock"):
        if read_lock(inputs[key]) != read_lock(root / (key + ".json")):
            raise ValueError("R4 delivered a different " + key)
    from workflow.media_manifest import verify_manifest
    manifest = read_json(base / "media_manifest.json")
    delivery = read_json(base / "delivery.json")
    if delivery["stage"] != "D" or delivery["status"] != "ready_for_qa":
        raise ValueError("Formal production rejects draft Stage C delivery")
    problems = verify_manifest(manifest, base, spec, delivery)
    if problems:
        raise ValueError("Formal media hash verification failed: " + "; ".join(problems))
    covered = {f["path"] for f in manifest["files"]}
    if set(files.values()) - covered:
        raise ValueError("Formal media manifest omits approved source or lock evidence")


def receive(workdir, delivery_path, artifact_root, repository=None, pr=None,
            runner=subprocess.run):
    root, state, spec = load_state(workdir)
    if state["status"] not in ("prepared", "published", "rework_requested"):
        raise ValueError("Cannot receive delivery in state " + state["status"])
    delivery = read_json(delivery_path)
    if delivery.get("stage") == "D" and state.get("production_mode") != "formal":
        raise ValueError("Stage D may only be received after formal R0 lock approval")
    if state.get("production_mode") == "formal":
        check_formal_artifact(root, state, spec, artifact_root)
    errors = validate_bundle(spec, delivery)
    if errors:
        raise ValueError("Delivery does not match specification: " + "; ".join(errors))
    if delivery["status"] != "ready_for_qa":
        raise ValueError("Delivery must be ready_for_qa; blocked/prototype cannot be reviewed as complete")
    if not HEX_SHA.fullmatch(delivery["implementation_commit"]):
        raise ValueError("Delivery must contain an actual full 40-character Git commit SHA")
    expected_attempt = state["attempt"] + 1
    if delivery["attempt"] != expected_attempt:
        raise ValueError(f"Expected delivery attempt {expected_attempt}")
    if bool(repository) != bool(pr):
        raise ValueError("Provide both --repo and --pr, or neither for local-only delivery")
    if pr:
        head = read_pr_head(repository, pr, runner)
        if head["headRefOid"].lower() != delivery["implementation_commit"].lower():
            raise ValueError("Delivery commit does not match current PR HEAD")
        pr_url = head["url"]
    else:
        pr_url = state.get("implementation_pr_url")

    artifacts = delivery["artifacts"]
    paths = [*artifacts["source_paths"]]
    paths.extend(artifacts.get("keyframe_paths", []))
    if not artifacts.get("video_path"):
        raise ValueError("ready_for_qa delivery requires a rendered video_path")
    paths.append(artifacts["video_path"])
    ensure_files(artifact_root, paths, "Delivery")
    write_json(root / "delivery.json", delivery)
    state["status"] = "implementation_received"
    state["attempt"] = expected_attempt
    state["implementation_pr_url"] = pr_url
    state["implementation_commit"] = delivery["implementation_commit"]
    state["history"].append({"event": "delivery_received", "attempt": expected_attempt,
                              "commit": delivery["implementation_commit"]})
    save_state(root, state)
    return state


def make_review(workdir):
    root, state, spec = load_state(workdir)
    if state["status"] != "implementation_received":
        raise ValueError("Review package requires a newly received delivery")
    delivery = read_json(root / "delivery.json")
    checks = [{"shot_id": shot_id, "requirement_id": requirement_id,
               "result": "needs_review", "evidence": "NOT YET REVIEWED"}
              for shot_id, requirement_id in sorted(required_checks(spec))]
    qa = {
        "schema_version": "1.0",
        "project_id": spec["project_id"], "spec_id": spec["spec_id"],
        "spec_revision": spec["revision"], "spec_sha256": state["spec_sha256"],
        "implementation_commit": delivery["implementation_commit"],
        "reviewer": {"name": "REPLACE_WITH_REVIEWER", "independent_context": False},
        "decision": "pending", "checks": checks, "findings": [],
        "summary": "NOT YET REVIEWED",
    }
    write_json(root / "qa_template.json", qa)
    instructions = "\n".join([
        "# Independent MG visual QA — review task",
        "",
        "Use a NEW independent review context. Inspect actual MP4 and contiguous frames.",
        "Do not infer visual correctness from code or element labels.",
        "Read director_spec.json and delivery.json, and actual video at the path below.",
        "Video (relative to executor artifact root): " + delivery["artifacts"]["video_path"],
        "Review all must_show and continuous_motion IDs; replace NOT YET REVIEWED",
        "with evidence and result (pass / needs_review / fail) for every requirement.",
        "Include timestamp and grounded evidence for P0/P1/P2 findings; give precise fixes.",
        "Do not mark pass if any item is unreviewed or unresolved P0/P1 exists.",
        "Return complete qa_report.json conforming to contracts/qa.schema.json.",
        "The template is pending and DOES NOT represent a completed review.",
        "Bind your report to commit " + delivery["implementation_commit"],
        "",
        "If voice is draft, review only as a SILENT prototype; never approve release.",
    ])
    write_text(root / "review_task.md", instructions)
    state["status"] = "review_pending"
    save_state(root, state)
    return {"review_task": str(root / "review_task.md"),
            "qa_template": str(root / "qa_template.json")}


def rework_instructions(qa, state):
    lines = [
        "# Targeted implementation rework",
        "",
        "Specification: " + state["spec_id"] + " rev " + str(state["spec_revision"]),
        "Spec SHA256: " + state["spec_sha256"],
        "Review based on commit: " + state["implementation_commit"],
        "Produce NEW Git commit, re-render and send updated delivery.json.",
        "Do not change the locked director specification or silently downgrade.",
        "Do not treat this QA as valid for your next commit; request fresh review.",
        "",
        "## Findings",
    ]
    if not qa["findings"]:
        lines.append("No actionable findings were supplied; escalate to the director.")
    for item in sorted(qa["findings"], key=lambda f: {"P0": 0, "P1": 1, "P2": 2}[f["severity"]]):
        lines.extend(["",
                      "### " + item["id"] + " [" + item["severity"] + "] " + item["shot_id"],
                      "Expected: " + item["expected"],
                      "Observed: " + item["observed"],
                      "Evidence: " + item["evidence"],
                      "Fix: " + item["fix_request"]])
    return "\n".join(lines)


def record_qa(workdir, qa_path, max_attempts=2):
    root, state, spec = load_state(workdir)
    if state["status"] != "review_pending":
        raise ValueError("QA can only be recorded after a review package was created")
    delivery = read_json(root / "delivery.json")
    qa = read_json(qa_path)
    errors = validate_bundle(spec, delivery, qa)
    if errors:
        raise ValueError("Invalid QA report: " + "; ".join(errors))
    if qa["decision"] == "pass":
        state["status"] = "qa_passed"
    elif qa["decision"] in ("rework", "blocked"):
        state["status"] = "rework_requested" if qa["decision"] == "rework" and state["attempt"] < max_attempts else "escalation_required"
    else:
        raise ValueError("QA decision must be pass, rework or blocked; pending is not a completed review")
    write_json(root / "qa_report.json", qa)
    if qa["decision"] != "pass":
        write_text(root / "rework_task.md", rework_instructions(qa, state))
    state["history"].append({"event": "qa_recorded", "decision": qa["decision"],
                             "attempt": state["attempt"]})
    save_state(root, state)
    return state


def feedback(workdir, repository, pr, dry_run=False, runner=subprocess.run):
    root, state, _ = load_state(workdir)
    if state["status"] not in ("rework_requested", "escalation_required"):
        raise ValueError("Feedback requires a failed QA")
    if not (root / "rework_task.md").is_file():
        raise ValueError("Rework task missing")
    head = read_pr_head(repository, pr, runner) if not dry_run else None
    if head and head["headRefOid"].lower() != state["implementation_commit"].lower():
        raise ValueError("PR advanced since QA; do not post feedback for stale commit")
    command = ["pr", "comment", str(pr), "--repo", repository,
               "--body-file", str(root / "rework_task.md")]
    if dry_run:
        return {"dry_run": True, "command": ["gh", *command]}
    result = gh(command, runner)
    state["history"].append({"event": "feedback_posted", "pr": str(pr)})
    save_state(root, state)
    return {"comment": result}


def release_check(workdir, artifact_root):
    root, state, spec = load_state(workdir)
    if state["status"] != "qa_passed":
        raise ValueError("Release requires successful independent QA")
    delivery = read_json(root / "delivery.json")
    qa = read_json(root / "qa_report.json")
    if state.get("production_mode") != "formal":
        raise ValueError("Release blocked: script/storyboard and voice locks required before formal R4")
    if state.get("production_mode") == "formal":
        check_formal_artifact(root, state, spec, artifact_root)
    errors = validate_bundle(spec, delivery, qa, release=True, artifact_root=artifact_root)
    if errors:
        raise ValueError("Release blocked: " + "; ".join(errors))
    return {"release_gate": "pass", "notice": "Metadata and hashes only; human/video QA still required."}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--spec", required=True)
    p.add_argument("--workdir", required=True)
    p.add_argument("--executor", choices=ALLOWED_EXECUTORS, default="muse")
    p.add_argument("--formal", action="store_true",
                   help="Require approved script/storyboard and voice locks before R4")
    for key in ("script", "storyboard", "plan", "cues",
                "audio", "timings", "script-lock", "voice-lock"):
        p.add_argument("--" + key)
    p = sub.add_parser("publish")
    p.add_argument("--workdir", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("receive")
    p.add_argument("--workdir", required=True)
    p.add_argument("--delivery", required=True)
    p.add_argument("--artifact-root", required=True)
    p.add_argument("--repo")
    p.add_argument("--pr")
    p = sub.add_parser("review-package")
    p.add_argument("--workdir", required=True)
    p = sub.add_parser("review")
    p.add_argument("--workdir", required=True)
    p.add_argument("--provider", choices=("deepseek",), required=True)
    p.add_argument("--artifact-root", required=True)
    p.add_argument("--model", default="deepseek-flash")
    p = sub.add_parser("record-qa")
    p.add_argument("--workdir", required=True)
    p.add_argument("--qa", required=True)
    p.add_argument("--max-attempts", type=int, default=2)
    p = sub.add_parser("feedback")
    p.add_argument("--workdir", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--pr", required=True)
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("release-check")
    p.add_argument("--workdir", required=True)
    p.add_argument("--artifact-root", required=True)
    p = sub.add_parser("status")
    p.add_argument("--workdir", required=True)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            if args.formal:
                assets = {key: getattr(args, key.replace("-", "_"))
                          for key in ("script", "storyboard", "plan", "cues",
                                      "audio", "timings", "script-lock", "voice-lock")}
                assets = {key.replace("-", "_"): value for key, value in assets.items()}
            else:
                keys = ("script", "storyboard", "plan", "cues",
                        "audio", "timings", "script_lock", "voice_lock")
                if any(getattr(args, key) for key in keys):
                    raise ValueError("Formal approval inputs require --formal")
                assets = None
            result = prepare(args.spec, args.workdir, args.executor, assets)
        elif args.command == "publish":
            result = publish(args.workdir, args.repo, args.dry_run)
        elif args.command == "receive":
            result = receive(args.workdir, args.delivery, args.artifact_root,
                             args.repo, args.pr)
        elif args.command == "review-package":
            result = make_review(args.workdir)
        elif args.command == "review":
            from workflow.r5_provider import review_deepseek
            result = review_deepseek(args.workdir, args.artifact_root, model=args.model)
        elif args.command == "record-qa":
            if args.max_attempts < 1:
                parser.error("--max-attempts must be positive")
            result = record_qa(args.workdir, args.qa, args.max_attempts)
        elif args.command == "feedback":
            result = feedback(args.workdir, args.repo, args.pr, args.dry_run)
        elif args.command == "release-check":
            result = release_check(args.workdir, args.artifact_root)
        else:
            result = load_state(args.workdir)[1]
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, "ERROR: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
