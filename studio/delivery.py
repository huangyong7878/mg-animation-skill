"""Pilot 001 Stage D build bridge with fail-closed preflight.

A future generic renderer can implement the same interface. This bridge only
runs the existing approved Pilot builder; it neither selects a new voice nor
approves R5/R7.
"""
import json
import re
import subprocess
from pathlib import Path

PILOT = Path("work/orders_pilot")
FILES = {
    "spec": "formal_locked_director_spec.json",
    "scene": "scene.json",
    "plan": "formal_narration_candidate.json",
    "cue-contract": "formal_av_cues_candidate.json",
    "script": "script_candidate.txt",
    "storyboard": "storyboard_candidate.md",
    "script-lock": "script_lock.json",
    "voice-lock": "voice_lock.json",
    "audio": "r4_handoff/media/voice.wav",
    "timings": "r4_handoff/media/timings.json",
}
SOURCE_FILES = ("scripts/primitives/orderflow.py", "work/orders_pilot/scene.json")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
RUN_ID = re.compile(r"^[a-f0-9]{16}$")

def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, check=True, timeout=20).stdout.strip()

def preflight(repo):
    repo = Path(repo).resolve()
    issues = []
    paths = {key: repo / PILOT / name for key,name in FILES.items()}
    for key, path in paths.items():
        if not path.is_file() or path.stat().st_size == 0:
            issues.append("Missing locked build input: " + key)
    try:
        sha = _git(repo, "rev-parse", "HEAD")
        if not COMMIT.fullmatch(sha):
            issues.append("HEAD is not a full source commit")
        status = _git(repo, "status", "--porcelain", "--", *SOURCE_FILES,
                      *[str(PILOT / name) for name in FILES.values()])
        if status:
            issues.append("Uncommitted changes in production implementation or locked inputs")
    except (OSError, subprocess.SubprocessError):
        sha = None
        issues.append("Cannot inspect Git HEAD")
    # Reuse the production lock gate, not a duplicate UI approximation.
    if not issues:
        try:
            from workflow.build_stage_d_artifact import load, verify_lock
            spec = load(paths["spec"]); scene = load(paths["scene"])
            plan = load(paths["plan"]); cues = load(paths["cue-contract"])
            verify_lock(spec, scene, plan, cues, paths["script"],
                        paths["audio"], paths["timings"],
                        storyboard=paths["storyboard"], plan_path=paths["plan"],
                        cue_path=paths["cue-contract"],
                        script_lock=load(paths["script-lock"]),
                        voice_lock=load(paths["voice-lock"]))
        except Exception as exc:
            issues.append("Production lock/AV contract gate failed: " + str(exc)[:250])
    return {"ready": not issues, "issues": issues, "source_sha": sha,
            "builder": "Pilot 001 Stage D (locked voice only)",
            "r5_pass": False, "r7_authorized": False}

def run_build(repo, run_id):
    """Explicit synchronous invocation for background worker; never publish."""
    repo = Path(repo).resolve()
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid render run ID")
    before = preflight(repo)
    if not before["ready"]:
        raise ValueError("Stage D blocked: " + "; ".join(before["issues"]))
    sha = before["source_sha"]
    dest = repo / PILOT / ("stage_d_studio_" + run_id)
    if dest.exists():
        raise ValueError("Immutable delivery destination already exists")
    argv = ["python3", "workflow/build_stage_d_artifact.py"]
    for flag, name in FILES.items():
        argv += ["--" + flag, str(repo / PILOT / name)]
    argv += ["--source-sha", sha, "--out", str(dest)]
    proc = subprocess.run(argv, cwd=repo, capture_output=True, text=True,
                          timeout=900, check=False)
    result = {"status":"ready_for_qa" if proc.returncode == 0 else "failed",
              "source_sha":sha, "delivery_dir":str(dest), "exit_code":proc.returncode,
              "output":(proc.stdout + "\n" + proc.stderr)[-5000:],
              "r5_pass":False, "r7_authorized":False}
    if proc.returncode == 0:
        delivery = json.loads((dest / "delivery.json").read_text())
        if delivery.get("implementation_commit") != sha or delivery.get("status") != "ready_for_qa":
            raise ValueError("Unexpected Stage D delivery provenance")
        result["video_path"] = str(dest / delivery["artifacts"]["video_path"])
    return result
