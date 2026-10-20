#!/usr/bin/env python3
"""Manual-only Stage C AV review authorization and PR feedback.

All billable action requires explicit workflow_dispatch(stagec_run_id), two
independent repository opt-ins and a verified successful same-repo PR run.
No downloaded PR code is executed; GitHub metadata selects the correct PR.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from workflow.r5_pr_feedback import api, associated_pr, neutral, REPO_RE, SHA_RE
except ModuleNotFoundError:
    from r5_pr_feedback import api, associated_pr, neutral, REPO_RE, SHA_RE

RUN_RE = re.compile(r"^[1-9][0-9]{0,18}$")
EXPECTED_PATH = ".github/workflows/stagec-audio-artifacts.yml"
EXPECTED_NAME = "Stage C Pilot Narration and AV Draft"
REVIEW_NAME = "R5 Independent Stage C Audiovisual QA"
REVIEW_PATH = ".github/workflows/r5-stagec-av-qa.yml"


def selected_run(repo, run_id, token, transport=None):
    if not REPO_RE.fullmatch(repo) or not isinstance(run_id, str) or not RUN_RE.fullmatch(run_id):
        raise ValueError("Invalid repository or Stage C run ID")
    number = int(run_id)
    info = api("GET", f"/repos/{repo}/actions/runs/{number}", token, transport=transport)
    if (info.get("id") != number or info.get("name") != EXPECTED_NAME
            or info.get("path", "").split("@", 1)[0] != EXPECTED_PATH
            or info.get("event") != "pull_request"
            or info.get("status") != "completed"
            or info.get("conclusion") != "success"):
        raise ValueError("Run must be a successful, completed Stage C pull_request build")
    if (info.get("repository", {}).get("full_name", "").lower() != repo.lower()
            or (info.get("head_repository") or {}).get("full_name", "").lower() != repo.lower()):
        raise ValueError("Cross-repository or fork run is not authorized")
    sha = info.get("head_sha")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError("Invalid immutable source SHA")
    pr = associated_pr(repo, sha, token, transport)
    assert_current_pr(repo, pr, sha, token, transport)
    return {
        "source_run_id": number,
        "implementation_commit": sha,
        "pr": pr,
        "source_artifact": f"mg-orders-stagec-draft-{number}-{sha[:12]}",
    }


def selected_saved_review(repo, reviewed_run_id, selection, token, transport=None):
    """Authenticate previous R5 run before reading its stored QA artifact.

    The previous R5 job may have failed *only after* the model succeeded
    (PR comment 403), so a failed run is allowed; presence of a validated
    report and matching hashes is checked again before publication.
    """
    number, sha, _ = validated_selection(selection)
    if not isinstance(reviewed_run_id, str) or not RUN_RE.fullmatch(reviewed_run_id):
        raise ValueError("Review run ID must be a positive decimal integer")
    review_id = int(reviewed_run_id)
    info = api("GET", f"/repos/{repo}/actions/runs/{review_id}",
               token, transport=transport)
    if (info.get("id") != review_id
            or info.get("name") != REVIEW_NAME
            or info.get("path", "").split("@", 1)[0] != REVIEW_PATH
            or info.get("event") != "workflow_dispatch"
            or info.get("status") != "completed"
            or info.get("conclusion") not in ("success", "failure")
            or info.get("head_branch") != "main"
            or info.get("repository", {}).get("full_name", "").lower() != repo.lower()
            or (info.get("head_repository") or {}).get("full_name", "").lower() != repo.lower()):
        raise ValueError("Not a trusted completed main-branch Stage C R5 review run")
    return {
        "review_run_id": review_id,
        "review_artifact_name": f"r5-stagec-av-{number}-{sha}",
    }


def validate_saved_evidence(selection, report, audit, artifact_root):
    """Fail closed if review report does not belong to verified source bytes."""
    number, sha, pr = validated_selection(selection)
    if (audit.get("provider") != "gemini" or not audit.get("model")
            or audit.get("pr") != pr
            or audit.get("source_run_id") != number
            or audit.get("implementation_commit") != sha
            or audit.get("source_artifact") != selection["source_artifact"]
            or report.get("implementation_commit") != sha
            or report.get("source_run_id") != number
            or report.get("source_artifact") != selection["source_artifact"]
            or report.get("report_kind") != "r5_stagec_av"
            or report.get("stage") != "C" or report.get("status") != "prototype"
            or report.get("release_approved") is not False
            or report.get("decision") != audit.get("decision")):
        raise ValueError("Stored R5 review is not the selected Stage C source")
    from workflow.r5_av_review import verify_inputs, validate_observations
    from workflow.r5_review import sha256
    spec, _, _, _, _, cue_report, video, audio = verify_inputs(artifact_root, selection)
    if (report.get("video_sha256") != sha256(video)
            or audit.get("video_sha256") != sha256(video)
            or report.get("audio_sha256") != sha256(audio)
            or audit.get("audio_sha256") != sha256(audio)):
        raise ValueError("Stored R5 review does not match original MP4/WAV hashes")
    keys = ("decision", "audio_evaluated", "video_evaluated",
            "checks", "findings", "summary")
    observations = {key: report[key] for key in keys}
    validate_observations(
        json.dumps(observations, ensure_ascii=False), cue_report,
        float(spec["output"]["duration_s"]))
    return True


def assert_current_pr(repo, pr, sha, token, transport=None):
    data = api("GET", f"/repos/{repo}/pulls/{pr}", token, transport=transport)
    if data.get("state") != "open" or data.get("head", {}).get("sha") != sha:
        raise ValueError("Stage C PR is closed or HEAD no longer matches reviewed media")


def validated_selection(selection):
    number = selection.get("source_run_id")
    sha = selection.get("implementation_commit")
    pr = selection.get("pr")
    if (type(number) is not int or number < 1 or not isinstance(sha, str)
            or not SHA_RE.fullmatch(sha) or type(pr) is not int or pr < 1
            or selection.get("source_artifact") != f"mg-orders-stagec-draft-{number}-{sha[:12]}"):
        raise ValueError("Invalid source selection")
    return number, sha, pr


def comment_marker(run_id, sha):
    return f"<!-- mg-r5-av run:{run_id} sha:{sha} -->"


def preflight(repo, selection, token, transport=None):
    number, sha, pr = validated_selection(selection)
    fresh = selected_run(repo, str(number), token, transport)
    if fresh != selection:
        raise ValueError("Selected source metadata changed")
    comments = api("GET", f"/repos/{repo}/issues/{pr}/comments?per_page=100",
                   token, transport=transport)
    if any(comment_marker(number, sha) in c.get("body", "") for c in comments):
        return {"should_run": False, "pr": pr}
    return {"should_run": True, "pr": pr}


def make_comment(report, audit, repo):
    number, sha, _ = validated_selection({
        "source_run_id": audit.get("source_run_id"),
        "implementation_commit": audit.get("implementation_commit"),
        "pr": audit.get("pr"),
        "source_artifact": audit.get("source_artifact"),
    })
    if (report.get("implementation_commit") != sha or report.get("source_run_id") != number
            or report.get("decision") != audit.get("decision")
            or len(report.get("checks", [])) == 0):
        raise ValueError("R5 AV report/audit mismatch")
    lines = [
        comment_marker(number, sha),
        f"### R5 Independent Stage C Audiovisual QA — {report['decision'].upper()}",
        "**Automated model observation, NOT human narration lock or release approval.**",
        f"- **Source**: https://github.com/{repo}/actions/runs/{number}",
        f"- **Commit**: \`{sha}\`",
        f"- **Gemini model**: \`{neutral(audit['model'], 100)}\`",
        f"- **Check results**: {sum(c['result']=='pass' for c in report['checks'])}/{len(report['checks'])} pass",
        f"- **Scope**: Stage C draft WAV + audio-containing preview MP4 only",
        "",
        "**Summary**: " + neutral(report.get("summary", ""), 800),
        "",
    ]
    for cue in report["checks"]:
        lines.append(
            f"- **{neutral(cue['segment_id'], 90)}** ({float(cue['timestamp_s']):g}s): "
            f"{neutral(cue['result'], 20)} — "
            f"heard: {neutral(cue['heard_text'], 170)}; "
            f"seen: {neutral(cue['visual_observation'], 260)}; "
            f"reason: {neutral(cue['reason'], 350)}"
        )
    lines += ["", "See \`av_qa_report.json\` and \`av_r5_audit.json\` in the Actions artifact.",
              "Draft media does not qualify as Stage D release even when this review passes."]
    return "\n".join(lines)[:13000]


def publish(repo, selection, report, audit, token, transport=None, artifact_root=None):
    number, sha, pr = validated_selection(selection)
    if audit.get("pr") != pr or audit.get("source_run_id") != number:
        raise ValueError("Audit does not refer to selected PR and source run")
    fresh = selected_run(repo, str(number), token, transport)
    if fresh != selection:
        raise ValueError("PR/run changed while the review was executing")
    if artifact_root is not None:
        validate_saved_evidence(selection, report, audit, artifact_root)
    body = make_comment(report, audit, repo)
    existing = api("GET", f"/repos/{repo}/issues/{pr}/comments?per_page=100",
                   token, transport=transport)
    if any(comment_marker(number, sha) in c.get("body", "") for c in existing):
        return None
    return api("POST", f"/repos/{repo}/issues/{pr}/comments",
               token, {"body": body}, transport=transport)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["select", "preflight", "publish", "select-review"], required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--review-run-id")
    parser.add_argument("--artifact-root")
    parser.add_argument("--selection", required=True)
    parser.add_argument("--report")
    parser.add_argument("--audit")
    args = parser.parse_args(argv)
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        if not token:
            raise ValueError("GitHub token missing")
        path = Path(args.selection)
        if args.mode == "select":
            selection = selected_run(repo, args.run_id, token)
            path.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
            if os.environ.get("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                    for k, v in selection.items():
                        output.write(f"{k}={v}\n")
            print(f"Selected Stage C build #{selection['source_run_id']} on open PR #{selection['pr']}")
        else:
            selection = json.loads(path.read_text(encoding="utf-8"))
            if args.mode == "select-review":
                data = selected_saved_review(repo, args.review_run_id, selection, token)
                if os.environ.get("GITHUB_OUTPUT"):
                    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                        for key, value in data.items():
                            output.write(f"{key}={value}\n")
                print("Authenticated previous R5 report artifact:", data)
            elif args.mode == "preflight":
                decision = preflight(repo, selection, token)
                if os.environ.get("GITHUB_OUTPUT"):
                    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                        output.write("should_run=" + str(decision["should_run"]).lower() + "\n")
                print("Authorized manual AV review:", decision)
            else:
                if not args.report or not args.audit:
                    raise ValueError("Missing validated report/audit")
                report = json.loads(Path(args.report).read_text(encoding="utf-8"))
                audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
                answer = publish(repo, selection, report, audit, token,
                                 artifact_root=args.artifact_root)
                print("PR AV QA feedback:", "already posted" if answer is None else "posted")
    except (ValueError, KeyError, OSError, RuntimeError, TypeError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
