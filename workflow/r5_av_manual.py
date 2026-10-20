#!/usr/bin/env python3
"""Import an independent human/external-model Stage C AV report OFFLINE.

No GitHub Actions, no GitHub token, no Gemini key, no network I/O. The reviewer
must really examine the media independently; local schema checking cannot
establish that they did. Does NOT grant Stage D release approval.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow.r5_av_review import verify_inputs, validate_observations
from workflow.r5_review import read_json, write_json, sha256


def import_manual(artifact_root, observations_path, reviewer_name, out,
                  independent_attested=False):
    if not isinstance(reviewer_name, str) or not re.fullmatch(
            r"[^\x00-\x1f<>]{2,100}", reviewer_name):
        raise ValueError("Reviewer name must contain 2..100 safe printable characters")
    spec, delivery, plan, contract, timing, cues, video, voice = verify_inputs(
        artifact_root, selection=None
    )
    raw = Path(observations_path).read_text(encoding="utf-8")
    result = validate_observations(raw, cues, float(spec["output"]["duration_s"]))
    if result["decision"] == "pass" and not independent_attested:
        raise ValueError("PASS requires explicit independent human/external review attestation")
    if result["decision"] == "pass" and not (
            result["audio_evaluated"] and result["video_evaluated"]):
        raise ValueError("PASS requires independently reviewed audio and video")
    origin = {
        "method": "manual_import",
        "reviewer": reviewer_name,
        "independent_context_attested": bool(independent_attested),
        "verified_by_code": False,
    }
    report = {
        **result, "report_kind": "r5_stagec_av",
        "review_origin": origin, "stage": "C", "status": "prototype",
        "implementation_commit": delivery["implementation_commit"],
        "source_run_id": None,
        "source_artifact": None,
        "video_sha256": sha256(video), "audio_sha256": sha256(voice),
        "release_approved": False,
    }
    audit = {
        "scope": "Manual Stage C AV observation, not Stage D release",
        "implementation_commit": delivery["implementation_commit"],
        "provider": "human_or_external_model",
        "reviewer": reviewer_name, "automated_model_called": False,
        "usage": None, "cost_usd": None,
        "decision": report["decision"],
        "video_sha256": report["video_sha256"],
        "audio_sha256": report["audio_sha256"],
        "storage_backend": read_json(
            Path(artifact_root) / "media_manifest.json")["storage"]["backend"],
        "independent_context_attested": bool(independent_attested),
        "reviewer_identity_verified": False,
    }
    target = Path(out)
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / "av_qa_report.json", report)
    write_json(target / "av_r5_audit.json", audit)
    print(f"Imported independent Stage C AV report: {report['decision']} "
          f"for {delivery['implementation_commit']} (no network/API call)")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-root", required=True)
    p.add_argument("--observations", required=True,
                   help="External or human-authored JSON matching AV observation schema")
    p.add_argument("--reviewer", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--attest-independent", action="store_true",
                   help="Assert reviewer actually watched/heard the media independently")
    a = p.parse_args(argv)
    try:
        import_manual(a.artifact_root, a.observations, a.reviewer, a.out,
                      a.attest_independent)
    except (ValueError, KeyError, OSError, RuntimeError, TypeError,
            json.JSONDecodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
