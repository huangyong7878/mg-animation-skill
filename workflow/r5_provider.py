"""Fail-closed R5 model adapters. Visual-only DeepSeek review never auto-passes QA."""
import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path
from urllib import request

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def extract_frames(video, folder, fps=2):
    folder.mkdir(parents=True, exist_ok=False)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video),
                    "-vf", f"fps={fps},scale=640:-2",
                    "-q:v", "4", str(folder / "frame_%03d.jpg")],
                   check=True, timeout=120)
    frames = sorted(folder.glob("frame_*.jpg"))
    if not frames:
        raise ValueError("No decoded frames; R5 blocked")
    return frames

def review_deepseek(workdir, artifact_root, *, model="deepseek-flash",
                    endpoint="https://api.deepseek.com/chat/completions",
                    transport=None):
    """Calls paid external API explicitly; records image-only observations, not R5 PASS."""
    from workflow.orchestrator import load_state, read_json, write_json, required_checks
    root, state, spec = load_state(workdir)
    if state["status"] != "review_pending":
        raise ValueError("Run receive and review-package before R5 review")
    delivery = read_json(root / "delivery.json")
    if delivery.get("stage") != "D" or delivery.get("status") != "ready_for_qa":
        raise ValueError("Expected Stage D ready_for_qa delivery")
    base = Path(artifact_root).resolve()
    video_rel = delivery["artifacts"]["video_path"]
    video = (base / video_rel).resolve()
    if not video.is_relative_to(base) or not video.is_file():
        raise ValueError("Video missing or outside artifact root")
    if not os.environ.get("DEEPSEEK_API_KEY") and transport is None:
        raise ValueError("DEEPSEEK_API_KEY is required")
    dest = root / "r5_deepseek"
    if dest.exists():
        raise ValueError("R5 output exists; refusing overwrite or duplicate paid request")
    dest.mkdir(parents=True)
    frames = extract_frames(video, dest / "frames")
    parts = [{"type": "text", "text": (
        "你是独立 R5 视觉审核员。下面是按时间排列的抽样帧，不是视频或音频。"
        "根据真实画面评价颜色身份、分支、节点、可读性；按 P0/P1/P2 给出问题、时间、证据。"
        "不得声称听过音频或检查了全部连续运动。不要生成 PASS。"\n        "只输出 JSON 对象，包含 findings 数组；每项必须有 id, severity(P0/P1/P2), shot_id, expected, observed, fix_request, evidence，以及可选 timestamp_s。"\n        "每个问题必须有真实可观察帧证据；没有问题则 findings 为空数组。不要编造证据。"
        "\\nDirector spec: " + json.dumps(spec, ensure_ascii=False) +
        "\\nVisual checks: " + json.dumps(sorted(required_checks(spec)), ensure_ascii=False) +
        "\\nFrames: " + str(len(frames)) + " sampled at 2 frames/sec."
    )}]
    for i, path in enumerate(frames):
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        parts.append({"type": "text", "text": f"帧 {i}: t≈{i / 2:.2f}s"})
        parts.append({"type": "image_url",
                      "image_url": {"url": "data:image/jpeg;base64," + encoded,
                                    "detail": "original"}})
    data = {"model": model, "messages": [{"role": "user", "content": parts}],
            "stream": False}
    if transport is None:
        if endpoint != "https://api.deepseek.com/chat/completions":
            raise ValueError("Nonstandard DeepSeek endpoint forbidden")
        req = request.Request(endpoint, data=json.dumps(data).encode(),
                              headers={"Authorization": "Bearer " + os.environ["DEEPSEEK_API_KEY"],
                                       "Content-Type": "application/json"}, method="POST")
        with request.urlopen(req, timeout=180) as response:
            result = json.loads(response.read())
    else:
        result = transport(data)
    observations = result["choices"][0]["message"]["content"]
    if not isinstance(observations, str) or not observations.strip():
        raise ValueError("Empty model observations")
    (dest / "observations.md").write_text(observations, encoding="utf-8")
    # The provider is never authoritative. Parse structured findings as a
    # candidate only; preserve raw text if the model does not return valid JSON.
    from jsonschema import Draft202012Validator
    snippet = observations.strip()
    if snippet.startswith("```"):
        snippet = snippet.split("\\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(snippet)
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, dict) and isinstance(parsed.get("findings"), list):
        proposed = {
            "schema_version": "1.0", "scope": "sampled_frames_only",
            "spec_sha256": state["spec_sha256"],
            "implementation_commit": delivery["implementation_commit"],
            "video_sha256": sha(video), "findings": parsed["findings"],
        }
        schema = read_json(root.parent.parent.parent.parent / "contracts" / "r5_rework_candidate.schema.json") if False else None
        from workflow.r5_rework import SCHEMA
        schema = read_json(SCHEMA)
        if Draft202012Validator(schema).is_valid(proposed):
            write_json(dest / "findings_candidate.json", proposed)

    evidence = {"provider": "deepseek", "model": model, "scope": "sampled_frames_only",
                "sampled_frames": len(frames), "video_sha256": sha(video),
                "implementation_commit": delivery["implementation_commit"],
                "spec_sha256": state["spec_sha256"],
                "usage": result.get("usage", {}),
                "audio_reviewed": False, "full_motion_reviewed": False,
                "model_decision": "not_authoritative"}
    write_json(dest / "evidence.json", evidence)
    qa = read_json(root / "qa_template.json")
    qa["reviewer"] = {"name": "DeepSeek vision — sampled frames only", "independent_context": True}
    qa["summary"] = ("DeepSeek sampled-frame observations saved separately; "
                     "full-motion and audio evidence absent. Pending independent completion.")
    qa["decision"] = "pending"
    for c in qa["checks"]:
        c["result"] = "needs_review"
        c["evidence"] = "Still requires full independent R5 review; see r5_deepseek/observations.md"
    write_json(dest / "qa_report_PENDING.json", qa)
    return {"status": "pending", "observations": str(dest / "observations.md"),
            "qa_draft": str(dest / "qa_report_PENDING.json"),
            "evidence": str(dest / "evidence.json"), "usage": evidence["usage"]}
