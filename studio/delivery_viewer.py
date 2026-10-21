"""Read-only, provenance-checked Stage D delivery discovery and media selection."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ID = re.compile(r"^stage_d_(?:studio_[a-f0-9]{16}|delivery(?:_v[0-9]+)?)$")

def resolve_delivery(repo, identifier):
    if not isinstance(identifier, str) or not ID.fullmatch(identifier):
        raise ValueError("Invalid delivery identifier")
    root = (Path(repo).resolve() / "work/orders_pilot").resolve()
    folder = (root / identifier).resolve()
    if not folder.is_relative_to(root) or not folder.is_dir():
        raise ValueError("Delivery not found")
    return folder

def display_version(identifier):
    if identifier == "stage_d_delivery":
        return "初版"
    if identifier.startswith("stage_d_delivery_v"):
        return "V" + identifier.rsplit("_v", 1)[1]
    return "Studio 构建 " + identifier.removeprefix("stage_d_studio_")[:8]

def file_time(folder):
    stat = folder.stat()
    created = getattr(stat, "st_birthtime", None)
    if created is None:
        # Linux filesystems may not expose birth time. Do NOT call mtime 'created'.
        return {"time": None, "time_basis": "unknown"}
    return {"time": datetime.fromtimestamp(created, timezone.utc).isoformat(),
            "time_basis": "filesystem_birthtime"}

def review_status(folder):
    # A pending template is NOT an independent review.
    report = folder / "qa_report.json"
    if report.is_file():
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
            decision = data.get("decision")
            if decision == "pending":
                return "待独立审核"
            # Merely finding a report is not enough to certify R5 PASS.
            return "有审核记录（未验证）"
        except (OSError, ValueError):
            return "审核记录异常"
    return "待独立审核"

def inspect(repo, identifier):
    repo_root = str(Path(repo).resolve())
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from workflow.media_manifest import verify_manifest
    folder = resolve_delivery(repo, identifier)
    delivery = json.loads((folder / "delivery.json").read_text())
    manifest = json.loads((folder / "media_manifest.json").read_text())
    spec = json.loads((folder / "director_spec.json").read_text())
    errors = verify_manifest(manifest, folder, spec, delivery)
    video_rel = delivery["artifacts"]["video_path"]
    video = (folder / video_rel).resolve()
    if not video.is_relative_to(folder) or not video.is_file() or video.suffix.lower() != ".mp4":
        errors.append("Invalid or absent MP4")
    return {"id": identifier, "version": display_version(identifier),
            **file_time(folder), "review_status": review_status(folder),
            "status":delivery["status"],
            "source_sha":delivery["implementation_commit"],
            "spec_sha256":delivery["spec_sha256"],
            "manifest_ok":not errors, "errors":errors,
            "media_count":len(manifest["files"]),
            "video_url":("/api/deliveries/"+identifier+"/video") if not errors else None,
            "r5_pass":False,"r7_authorized":False}

def list_deliveries(repo):
    root=Path(repo).resolve() / "work/orders_pilot"
    if not root.is_dir():
        return []
    items=[]
    for path in sorted(root.iterdir(),reverse=True):
        if path.is_dir() and ID.fullmatch(path.name):
            try:
                items.append(inspect(repo,path.name))
            except (OSError,ValueError,KeyError,TypeError):
                items.append({"id":path.name,"version":display_version(path.name),
                              **file_time(path),"review_status":"无法确认",
                              "status":"invalid","manifest_ok":False,
                              "errors":["Invalid delivery or provenance"]})
    return sorted(items, key=lambda item: item.get("time") or "", reverse=True)

def verified_video(repo, identifier):
    result=inspect(repo,identifier)
    if not result["manifest_ok"] or result["status"] != "ready_for_qa":
        raise ValueError("Video not approved for preview: integrity or delivery status failed")
    folder=resolve_delivery(repo,identifier)
    delivery=json.loads((folder/"delivery.json").read_text())
    video=(folder/delivery["artifacts"]["video_path"]).resolve()
    if not video.is_relative_to(folder) or not video.is_file():
        raise ValueError("Video not found")
    return video
