"""Explicit, paid, sampled-frame R5 submission for immutable Stage D deliveries.

One-click wrapper invokes existing R0 formal gates; no R5 PASS or R7 writes.
"""
import json
import os
import re
import secrets
from pathlib import Path

RUN = re.compile(r"^review_[0-9a-f]{16}$")

def _deps(repo):
    import sys
    root = str(Path(repo).resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    from workflow import orchestrator as r0
    from workflow.r5_registry import run_review
    from studio.delivery_viewer import resolve_delivery, inspect
    return r0, run_review, resolve_delivery, inspect

def review_preflight(repo, delivery_id):
    r0, _, resolve, inspect = _deps(repo)
    folder = resolve(repo, delivery_id)
    item = inspect(repo, delivery_id)
    issues = []
    if not item["manifest_ok"] or item["status"] != "ready_for_qa":
        issues.append("Delivery integrity/status is not ready for QA")
    manifest = json.loads((folder/"media_manifest.json").read_text())
    delivery = json.loads((folder/"delivery.json").read_text())
    if manifest["implementation_commit"] != delivery["implementation_commit"]:
        issues.append("Implementation SHA mismatch")
    for key in ("script_lock", "voice_lock"):
        if not (folder/"approvals"/(key+".json")).is_file():
            issues.append("Missing formal production approval: "+key)
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        issues.append("DEEPSEEK_API_KEY is not configured in MG Studio environment")
    if os.environ.get("R5_ENABLED") != "true":
        issues.append("R5_ENABLED must equal true for an explicit paid request")
    existing = []
    workroot = Path(repo).resolve()/"work/mg_studio/r5_runs"
    if workroot.exists():
        for state_file in workroot.glob("review_*/state.json"):
            try:
                state = json.loads(state_file.read_text())
                received = state_file.parent/"delivery.json"
                if received.is_file():
                    old = json.loads(received.read_text())
                    if old["implementation_commit"] == delivery["implementation_commit"] and old["spec_sha256"] == delivery["spec_sha256"] and (state_file.parent/"source_delivery_id.txt").read_text().strip() == delivery_id:
                        existing.append(state_file.parent.name)
            except (OSError, ValueError, KeyError):
                continue
    if existing:
        issues.append("A matching R5 review run already exists: "+", ".join(existing))
    return {"ready": not issues, "issues": issues, "delivery_id": delivery_id,
            "source_sha":delivery["implementation_commit"],
            "estimated_frame_count":None,
            "scope":"sampled_frames_only", "paid_api":True,
            "audio_reviewed":False,"full_motion_reviewed":False}

def submit_review(repo, delivery_id):
    repo = Path(repo).resolve()
    check = review_preflight(repo, delivery_id)
    if not check["ready"]:
        raise ValueError("R5 review blocked: "+"; ".join(check["issues"]))
    r0, run_review, resolve, _ = _deps(repo)
    folder = resolve(repo, delivery_id)
    target = repo/"work/mg_studio/r5_runs"/("review_"+secrets.token_hex(8))
    assets = {
        "script":folder/"narration.txt",
        "storyboard":folder/"source/storyboard.md",
        "plan":folder/"source/narration_plan.json",
        "cues":folder/"source/approved_av_cues.json",
        "audio":folder/"media/voice.wav",
        "timings":folder/"media/timings.json",
        "script_lock":folder/"approvals/script_lock.json",
        "voice_lock":folder/"approvals/voice_lock.json",
    }
    target.mkdir(parents=True,exist_ok=False)
    (target/"source_delivery_id.txt").write_text(delivery_id)
    # R0's real contract gates verify locks and immutable media. No API call
    # happens until all prepare/receive/review-package operations succeed.
    r0.prepare(folder/"director_spec.json", target, formal_assets=assets)
    r0.receive(target, folder/"delivery.json", folder)
    r0.make_review(target)
    result = run_review("deepseek", target, folder)
    return {"status":"pending_full_av_review","workdir":str(target),
            "delivery_id":delivery_id,"result":result,
            "r5_pass":False,"r7_authorized":False}
