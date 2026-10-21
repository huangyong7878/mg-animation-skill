"""Generic, fail-closed R4 task runner. No commits, pushes or publishing."""
import json
import subprocess
import tempfile
from pathlib import Path
from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).resolve().parents[1] / "contracts/r4_executable_assignment.schema.json"

def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()

def valid_path(p):
    q = Path(p)
    return (not q.is_absolute() and ".." not in q.parts
            and len(q.parts) > 0 and not any(x.startswith(".git") for x in q.parts)
            and not p.startswith(("work/", "media/", "approvals/", "contracts/", "workflow/", "studio/"))
            and (p.startswith("scripts/") or p.startswith("tests/")))

def validate_assignment(repo, path):
    repo = Path(repo).resolve()
    path = Path(path).resolve()
    inbox = (repo / "work/r4_inbox").resolve()
    if not path.is_relative_to(inbox) or path.name != "assignment.json" or not path.is_file():
        raise ValueError("Assignment must be inside work/r4_inbox/<job>/assignment.json")
    task = json.loads(path.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(task))
    if errors:
        raise ValueError("Invalid executable R4 assignment: " + errors[0].message)
    ids = [f["id"] for f in task["findings"]]
    if len(ids) != len(set(ids)) or set(ids) != set(task["approved_finding_ids"]):
        raise ValueError("Finding IDs do not match approved scope")
    files = task["execution_policy"]["allowed_files"]
    if any(not valid_path(p) for p in files):
        raise ValueError("Forbidden edit path in execution policy")
    git(repo, "cat-file", "-e", task["source_implementation_commit"] + "^{commit}")
    return task

def execute(repo, assignment):
    repo = Path(repo).resolve()
    task = validate_assignment(repo, assignment)
    source = task["source_implementation_commit"]
    workroot = Path(tempfile.mkdtemp(prefix="mg-studio-r4-"))
    tree = workroot / "repo"
    git(repo, "worktree", "add", "--detach", str(tree), source)
    allowed = set(task["execution_policy"]["allowed_files"])
    brief = {"project_id": task["project_id"], "spec_sha256": task["spec_sha256"],
             "source_commit": source, "approved_findings": task["findings"],
             "allowed_files": sorted(allowed)}
    prompt = ("You are the R4 implementation executor. Fix ONLY approved findings. "
              "Only edit the explicitly allowed source files. Do not modify approvals, "
              "script/voice locks, narration or AV cues. Do not commit, push, merge, "
              "publish or claim R5 PASS. Do not use network tools. "
              "An independent gate will inspect all diffs.\n"
              + json.dumps(brief, ensure_ascii=False))
    proc = subprocess.run(
        ["codex", "exec", "--sandbox", "workspace-write", prompt],
        cwd=tree, capture_output=True, text=True,
        timeout=task["execution_policy"]["max_runtime_seconds"], check=False)
    changed = set(git(tree, "diff", "--name-only").splitlines())
    changed |= set(git(tree, "diff", "--cached", "--name-only").splitlines())
    changed |= set(git(tree, "ls-files", "--others", "--exclude-standard").splitlines())
    forbidden = sorted(changed - allowed)
    head_changed = git(tree, "rev-parse", "HEAD") != source
    status = ("blocked" if forbidden or head_changed else
              "ready_for_manual_review" if proc.returncode == 0 else "executor_failed")
    result = {"status": status, "worktree": str(tree), "base_commit": source,
              "changed_files": sorted(changed), "forbidden_files": forbidden,
              "head_changed": head_changed, "exit_code": proc.returncode,
              "output": (proc.stdout + "\n" + proc.stderr)[-12000:],
              "note": "No automatic commit/render/R5/R7. Review code and test first."}
    (workroot / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result
