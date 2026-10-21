"""R5 findings -> explicit owner-approved R0 dispatch. Never launches R4."""
import json
import re
from pathlib import Path

RUN_ID = re.compile(r"^review_[0-9a-f]{16}$")
INBOX_ID = re.compile(r"^[a-zA-Z0-9_-]{3,80}$")
PROJECT_EDIT_POLICY = {
    "orders_two_routes": (
        "scripts/primitives/orderflow.py",
        "tests/test_pilot001_visual_fix.py",
    ),
}

def recommended_files(project_id):
    return list(PROJECT_EDIT_POLICY.get(project_id, ()))


def _run(repo, run_id):
    if not isinstance(run_id,str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("Invalid R5 run ID")
    root=(Path(repo).resolve()/"work/mg_studio/r5_runs").resolve()
    path=(root/run_id).resolve()
    if not path.is_relative_to(root) or not path.is_dir():
        raise ValueError("R5 review not found")
    return path

def _delivery(repo, run):
    from studio.delivery_viewer import resolve_delivery, inspect
    identifier=(run/"source_delivery_id.txt").read_text(encoding="utf-8").strip()
    folder=resolve_delivery(repo, identifier)
    meta=inspect(repo, identifier)
    if not meta["manifest_ok"] or meta["status"] != "ready_for_qa":
        raise ValueError("Source delivery failed integrity verification")
    return identifier,folder,meta

def candidates(repo):
    root=Path(repo).resolve()/"work/mg_studio/r5_runs"
    if not root.is_dir():
        return []
    out=[]
    for run in sorted(root.iterdir(),reverse=True):
        if not run.is_dir() or not RUN_ID.fullmatch(run.name):
            continue
        try:
            task=json.loads((run/"r4_rework_draft/rework_task_candidate.json").read_text())
            _, _, delivery=_delivery(repo,run)
            from workflow.orchestrator import load_state
            _,state,_=load_state(run)
            if state["status"] != "review_pending":
                continue
            if task["implementation_commit"] != delivery["source_sha"] or task["spec_sha256"] != delivery["spec_sha256"]:
                continue
            out.append({"id":run.name,"delivery_id":(run/"source_delivery_id.txt").read_text().strip(),
                "source_sha":task["implementation_commit"],"video_sha256":task["video_sha256"],
                "scope":task["r5_scope"],"status":task["status"],
                "findings":task["findings"],
                "recommended_files":recommended_files(task["project_id"])})
        except (OSError,ValueError,KeyError,TypeError):
            continue
    return out

def approve(repo, *, run_id, selected_ids, allowed_files, approved_by, inbox_id):
    from workflow.r4_dispatch import dispatch
    from studio.r4_runner import valid_path
    run=_run(repo,run_id)
    if not isinstance(inbox_id,str) or not INBOX_ID.fullmatch(inbox_id):
        raise ValueError("Invalid inbox name")
    if not isinstance(selected_ids,list) or not selected_ids or len(selected_ids)>50 or not all(isinstance(x,str) for x in selected_ids):
        raise ValueError("Choose finding IDs explicitly")
    if not isinstance(allowed_files,list) or not allowed_files or len(allowed_files)>20 or not all(isinstance(f,str) and valid_path(f) for f in allowed_files):
        raise ValueError("Explicit valid editable files are required")
    if not isinstance(approved_by,str) or approved_by.strip() != "Project owner":
        raise ValueError("This workflow requires explicit project-owner approval")
    identifier,folder,_=_delivery(repo,run)
    task=json.loads((run/"r4_rework_draft/rework_task_candidate.json").read_text())
    if task.get("status")!="draft_unverified" or task.get("r5_scope")!="sampled_frames_only":
        raise ValueError("Only sampled-frame unverified findings can be dispatched for rework")
    recommendations = recommended_files(task["project_id"])
    if recommendations and not set(allowed_files).issubset(set(recommendations)):
        raise ValueError("Editable files exceed project-approved policy")
    inbox=Path(repo).resolve()/"work/r4_inbox"/inbox_id
    return dispatch(run,selected_ids=selected_ids,approved_by=approved_by,
                    inbox=inbox,artifact_root=folder,allowed_files=allowed_files)
