"""Read-only R5 sampled-frame review history; never interprets it as AV pass."""
import json
import re
from pathlib import Path

WORKDIR_ID = re.compile(r"^formal_r4(?:_v[0-9]+)?$")
MAX_OBSERVATIONS = 25000

def review_history(repo):
    base = Path(repo).resolve() / "work/orders_pilot"
    if not base.is_dir():
        return []
    reports = []
    candidates = [p for p in base.iterdir() if p.is_dir() and WORKDIR_ID.fullmatch(p.name)]
    runs = Path(repo).resolve() / "work/mg_studio/r5_runs"
    if runs.is_dir():
        candidates.extend(p for p in runs.iterdir()
                          if p.is_dir() and p.name.startswith("review_"))
    for workdir in sorted(candidates):
        source = workdir / "r5_deepseek"
        evidence_file = source / "evidence.json"
        text_file = source / "observations.md"
        if not evidence_file.is_file() or not text_file.is_file():
            continue
        try:
            evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
            if evidence.get("provider") != "deepseek" or evidence.get("scope") != "sampled_frames_only":
                continue
            state_file = workdir / "state.json"
            state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.is_file() else {}
            observations = text_file.read_text(encoding="utf-8")[:MAX_OBSERVATIONS]
            reports.append({
                "id": workdir.name, "provider": "DeepSeek",
                "scope": "仅抽帧视觉观察",
                "sampled_frames": evidence.get("sampled_frames"),
                "source_sha": evidence.get("implementation_commit"),
                "video_sha256": evidence.get("video_sha256"),
                "spec_sha256": evidence.get("spec_sha256"),
                "r0_status": state.get("status", "unknown"),
                "decision": "pending_full_av_review",
                "audio_reviewed": False, "full_motion_reviewed": False,
                "observations": observations,
                "token_usage": evidence.get("usage", {}).get("total_tokens"),
            })
        except (OSError, ValueError, TypeError, KeyError):
            continue
    return reports
