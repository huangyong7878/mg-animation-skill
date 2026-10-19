#!/usr/bin/env python3
"""Build offline, provider-neutral director / visual-QA / rework task ZIPs.

Packages are file attachments; this script DOES NOT call any model API.
It DOES NOT judge a video or certify that a reviewer actually watched one.
"""
import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from workflow.check_handoff import canonical_digest, required_checks, validate_bundle
except ModuleNotFoundError:
    from check_handoff import canonical_digest, required_checks, validate_bundle


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_file(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Missing or empty input: {path}")
    return path


def copy(src, dest):
    check_file(src)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)


def write_text(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def write_json(path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2))


def get_dir(output_dir):
    root = Path(output_dir).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"Output directory already has files; refusing overwrite: {root}")
    zip_path = root.with_suffix(".zip")
    if zip_path.exists():
        raise ValueError(f"ZIP already exists; refusing overwrite: {zip_path}")
    root.mkdir(parents=True, exist_ok=True)
    return root, zip_path


def add_shared(root, role, schema):
    copy(ROOT / "roles" / role, root / "role.md")
    copy(ROOT / "roles" / "QUALITY_RUBRIC.md", root / "quality_rubric.md")
    copy(ROOT / "contracts" / schema, root / "contract.schema.json")


def director(args, root):
    copy(args.brief, root / "inputs" / "brief.md")
    if args.timings:
        copy(args.timings, root / "inputs" / "timings.json")
    add_shared(root, "DIRECTOR.md", "director_spec.schema.json")
    copy(ROOT / "references" / "creative-director.md",
         root / "references" / "creative-director.md")
    copy(ROOT / "references" / "technical-director.md",
         root / "references" / "technical-director.md")
    copy(ROOT / "references" / "visual-contract.md",
         root / "references" / "visual-contract.md")
    copy(ROOT / "references" / "storyboard-contract.md",
         root / "references" / "storyboard-contract.md")
    copy(ROOT / "SKILL.md", root / "references" / "SKILL.md")
    write_text(root / "START_HERE.md", """# 总导演任务（可交给任意支持文件的强模型）

读取 role.md、quality_rubric.md、inputs/brief.md 及附带的 references。
阅读 contract.schema.json，按照其**准确格式**返回以下完整文件：

- storyboard.md：供用户审批的人类可读分镜
- director_spec.json：可验证的镜头规格和视觉 Contract
- director_notes.md：信息缺口、事实假设、引擎能力假设和设计取舍

创意优先，但必须明确物体连续运动、数学/因果状态与可验收要求。
不要让工程执行者重新决定核心创意；也不要强迫所有镜头采用同一种模板。
未获人类确认，一律 approval.status=draft；没有正式锁定音频时 narration.status=draft。
存在未知的关键事实或缺失素材时明确说明，不能编造来源或验收状态。

**重要：** 生成的导演规格需要在实际仓库中运行：
python workflow/check_handoff.py --spec director_spec.json
不要自称已执行了未真实运行的测试。
""")
    return "director"


def qa_template(spec, delivery):
    return {
        "schema_version": "1.0",
        "project_id": spec["project_id"],
        "spec_id": spec["spec_id"],
        "spec_revision": spec["revision"],
        "spec_sha256": canonical_digest(spec),
        "implementation_commit": delivery["implementation_commit"],
        "reviewer": {"name": "TO_BE_FILLED", "independent_context": False},
        "decision": "pending",
        "checks": [
            {"shot_id": shot, "requirement_id": req, "result": "needs_review",
             "evidence": "NOT_INSPECTED"}
            for shot, req in sorted(required_checks(spec))
        ],
        "findings": [],
        "summary": "NOT_INSPECTED",
    }


def qa(args, root):
    spec = read_json(args.spec)
    delivery = read_json(args.delivery)
    errors = validate_bundle(spec, delivery)
    if errors:
        raise ValueError("Spec and delivery mismatch: " + "; ".join(errors))
    if delivery["status"] != "ready_for_qa":
        raise ValueError("Delivery is not marked ready_for_qa")
    media = check_file(args.video)
    if media.suffix.lower() not in (".mp4", ".mov", ".webm"):
        raise ValueError("QA requires an actual video container file")
    copy(args.spec, root / "inputs" / "director_spec.json")
    copy(args.delivery, root / "inputs" / "delivery.json")
    copy(media, root / "media" / ("render" + media.suffix.lower()))
    for index, frame in enumerate(args.frames or []):
        src = check_file(frame)
        if src.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            raise ValueError("Frame must be an image file")
        copy(src, root / "media" / "frames" / (f"{index:03d}_" + src.name))
    if args.timings:
        copy(args.timings, root / "inputs" / "timings.json")
    if args.evidence_dir:
        try:
            from workflow.qa_evidence import verify_evidence, EVIDENCE_FILE
        except ModuleNotFoundError:
            from qa_evidence import verify_evidence, EVIDENCE_FILE
        evidence_root = Path(args.evidence_dir).resolve()
        problems = verify_evidence(evidence_root, args.video, args.spec)
        if problems:
            raise ValueError("Invalid QA evidence: " + "; ".join(problems))
        index = read_json(evidence_root / EVIDENCE_FILE)
        names = [EVIDENCE_FILE]
        names += [entry["filename"] for entry in index["frames"]]
        names += [entry["path"] for entry in index["contact_sheets"]]
        for name in names:
            copy(evidence_root / name, root / "media" / "evidence" / name)
    add_shared(root, "REVIEWER.md", "qa.schema.json")
    write_json(root / "outputs" / "qa_template.json", qa_template(spec, delivery))
    write_text(root / "START_HERE.md", """# 独立多模态 QA 任务（必须真正查看视频）

1. 在**独立于制作模型的上下文**打开 role.md、quality_rubric.md、
   inputs/director_spec.json、inputs/delivery.json 和 media/render.*。
2. 审查真实视频；连续运动需要看连续时间段，不只看片头/片尾静帧。
   如果包含 media/evidence/evidence_index.json，可按时间戳复核已校验的联系表和连续抽样帧；但仍需要看原始视频。
3. 参考 outputs/qa_template.json、contract.schema.json 生成**完整** qa_report.json。
4. 不得以文件存在、测试通过或代码写有 contract 标签代替视觉验收。
5. 请把真实视频对应的时间位置写入 evidence/ timestamp_s；不可编造证据。
6. 若当前模型无法读取/播放媒体，返回 decision=pending、needs_review，
   并说明需要的视频抽帧/时间序列，不得宣布 pass。
7. 无声原型只审无声阶段，正式配音未锁定时不能确认发布。

此包 media/ 下是操作员提供的文件；manifest.json 用 SHA256 记录字节，
但不能独立证明它来自 delivery 所指 Git commit。需另外核对来源。
源代码故意不包含在 QA 包内，以保证先作独立视觉判断。
""")
    return "qa"


def rework(args, root):
    spec, delivery, report = map(read_json, (args.spec, args.delivery, args.qa))
    errors = validate_bundle(spec, delivery, report)
    if errors:
        raise ValueError("Stale or malformed QA: " + "; ".join(errors))
    if report["decision"] not in ("rework", "blocked"):
        raise ValueError("Rework package requires QA decision rework or blocked")
    copy(args.spec, root / "inputs" / "director_spec.json")
    copy(args.delivery, root / "inputs" / "delivery.json")
    copy(args.qa, root / "inputs" / "qa_report.json")
    add_shared(root, "REWORK_SUPERVISOR.md", "delivery.schema.json")
    issues = []
    for item in sorted(report["findings"],
                       key=lambda f: {"P0": 0, "P1": 1, "P2": 2}[f["severity"]]):
        issues.append(
            f"### {item['severity']} / {item['id']} / {item['shot_id']}\n"
            f"- 期待：{item['expected']}\n- 实测：{item['observed']}\n"
            f"- 证据：{item['evidence']}\n- 最小修复：{item['fix_request']}\n"
        )
    write_text(root / "START_HERE.md", """# 定点返工任务

阅读 role.md、inputs/ 下的规格/交付/QA 和下列问题清单。
只修改真实未通过的部分，不替换已获认可的镜头设计。
提交新 commit、新渲染视频、新 delivery，要求独立审查者重新审片。
问题不清或根源是导演规格歧义时，升级给总导演，不得隐性降级。

""" + "\n".join(issues) +
               ("\nQA 未列具体问题：停止盲目返工并向 QA 索取明确证据。\n"
                if not issues else ""))
    return "rework"


def finalize(root, zip_path, task):
    files = [p for p in root.rglob("*") if p.is_file()]
    manifest = {
        "package_version": "1.0", "task": task,
        "notice": "File bundle only. No model was invoked and no visual QA was performed.",
        "files": {str(p.relative_to(root)): {
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "size_bytes": p.stat().st_size,
        } for p in sorted(files)},
    }
    write_json(root / "manifest.json", manifest)
    with zipfile.ZipFile(zip_path, mode="x", compression=zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(root.rglob("*")):
            if p.is_file():
                archive.write(p, arcname=p.relative_to(root))
    return zip_path


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="task", required=True)
    p = sub.add_parser("director", help="Package script/brief for a replacement strong-model director")
    p.add_argument("--brief", required=True)
    p.add_argument("--timings")
    p.add_argument("--out", required=True)
    p = sub.add_parser("qa", help="Package actual video and current delivery for independent model review")
    p.add_argument("--spec", required=True)
    p.add_argument("--delivery", required=True)
    p.add_argument("--video", required=True)
    p.add_argument("--frame", dest="frames", action="append", default=[])
    p.add_argument("--evidence-dir", help="Verified timed frames generated by workflow/qa_evidence.py")
    p.add_argument("--timings")
    p.add_argument("--out", required=True)
    p = sub.add_parser("rework", help="Package a failed current review for targeted repairs")
    p.add_argument("--spec", required=True)
    p.add_argument("--delivery", required=True)
    p.add_argument("--qa", required=True)
    p.add_argument("--out", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        root, zip_path = get_dir(args.out)
        if args.task == "director":
            task = director(args, root)
        elif args.task == "qa":
            task = qa(args, root)
        else:
            task = rework(args, root)
        path = finalize(root, zip_path, task)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("ERROR:", str(exc), file=sys.stderr)
        return 1
    print("CREATED", path)
    print("NOTE: File transfer only; another model needs actual access to these materials.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
