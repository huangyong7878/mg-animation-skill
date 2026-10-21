"""Safe single-assignment local Codex runner for MG Studio.

This does not push, merge, render, perform R5 review, or publish. It creates
a detached Git worktree outside the source checkout, and refuses an unapproved
or stale assignment. Treat sandboxing as defense in depth, not a hard OS jail.
"""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

LOCKED_PREFIXES = (
    "work/orders_pilot/script_lock.json",
    "work/orders_pilot/voice_lock.json",
    "work/orders_pilot/formal_locked_director_spec.json",
    "work/orders_pilot/formal_narration_candidate.json",
    "work/orders_pilot/formal_av_cues_candidate.json",
    "work/orders_pilot/script_candidate.txt",
    "work/orders_pilot/storyboard_candidate.md",
)

def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout.strip()

def validate_assignment(repo, path):
    path = Path(path).resolve()
    allowed = (repo / "work/r4_inbox/pilot001_v3/assignment.json").resolve()
    if path != allowed or not path.is_file():
        raise ValueError("Only the approved Pilot 001 V3 local assignment is allowed")
    task = json.loads(path.read_text(encoding="utf-8"))
    if task.get("kind") != "r4_rework_assignment" or task.get("status") != "approved_for_rework_only":
        raise ValueError("Assignment has no approved R4 authorization")
    if not task.get("approval", {}).get("explicit_cli_authorization"):
        raise ValueError("Missing explicit R0 authorization")
    expected = {"V2-P1-001", "V2-P1-002", "V2-P2-001",
                "V2-P2-002", "V2-P2-003", "V2-P2-004"}
    if set(task.get("approved_finding_ids", [])) != expected:
        raise ValueError("Assignment IDs differ from approved V2 rework scope")
    if task.get("source_implementation_commit") != "32e4ffbc676ed4c2a379d528a7f0e2632a4490ec":
        raise ValueError("Unexpected V2 source commit")
    if not task.get("production_lock_hashes", {}).get("script_lock_digest") or not task.get("production_lock_hashes", {}).get("voice_lock_digest"):
        raise ValueError("Missing production lock digests")
    if not all(x.get("id") in expected for x in task.get("findings", [])):
        raise ValueError("Unexpected finding in assignment")
    if len(task["findings"]) != len(expected):
        raise ValueError("Incomplete finding set")
    _git(repo, "cat-file", "-e", task["source_implementation_commit"] + "^{commit}")
    return task

def execute(repo, assignment, on_event=None):
    """Yield progress through callback; never touch source checkout working tree."""
    repo = Path(repo).resolve()
    task = validate_assignment(repo, assignment)
    base_commit = _git(repo, "rev-parse", "HEAD")
    if _git(repo, "status", "--porcelain"):
        # Local user workspace can have untracked artifacts; worktree still isolates it.
        pass
    workroot = Path(tempfile.mkdtemp(prefix="mg-studio-r4-"))
    tree = workroot / "repo"
    _git(repo, "worktree", "add", "--detach", str(tree), base_commit)
    if on_event:
        on_event("worktree: " + str(tree) + "\n")
    request = {
        "approval": task["approval"], "findings": task["findings"],
        "prohibited": task["prohibited"],
        "spec_sha256": task["spec_sha256"],
        "source_implementation_commit": task["source_implementation_commit"],
        "production_lock_hashes": task["production_lock_hashes"],
    }
    prompt = (
        "You are R4 implementing ONLY the approved visual changes on the current "
        "mg-animation-skill checkout. Read the animation implementation and tests. "
        "Do not edit narration, locked assets, script, storyboard, cues, or approvals. "
        "Do not use network tools, push Git, merge PRs, publish, or claim R5 PASS. "
        "Do not create commits. Your work will be independently reviewed. "
        "Visual rework assignment:\n" + json.dumps(request, ensure_ascii=False)
    )
    try:
        proc = subprocess.run(
            ["codex", "exec", "--sandbox", "workspace-write", prompt],
            cwd=tree, capture_output=True, text=True, timeout=1200, check=False)
        output = (proc.stdout + "\n" + proc.stderr)[-12000:]
        tracked = _git(tree, "diff", "--name-only").splitlines()
        untracked = _git(tree, "ls-files", "--others", "--exclude-standard").splitlines()
        changed = tracked + untracked
        forbidden = [p for p in changed if p in LOCKED_PREFIXES or p.startswith((".git", "approvals/", "media/"))]
        if forbidden:
            raise ValueError("Locked or disallowed files touched: " + ", ".join(forbidden))
        # Codex should modify implementation only, not commit independently.
        if _git(tree, "rev-parse", "HEAD") != base_commit:
            raise ValueError("Executor unexpectedly changed Git HEAD")
        report = {"status": "ready_for_manual_review" if proc.returncode == 0 else "executor_failed",
                  "exit_code": proc.returncode,
                  "worktree": str(tree), "base_commit": base_commit,
                  "changed_files": changed, "forbidden": forbidden,
                  "output": output,
                  "next_step": "Review git diff, run tests, re-render and independent R5. No commit/push/merge was done."}
        (workroot / "result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
        return report
    except Exception:
        # Leave worktree for forensic inspection, not auto-promote changes.
        raise
