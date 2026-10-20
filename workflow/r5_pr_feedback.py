#!/usr/bin/env python3
"""Post a model-reviewed R5 QA summary to the uniquely matching, still-open PR.

Trusted workflow-run metadata and authenticated GitHub API choose the PR.
Never merges, approves, labels or edits any source branch.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def api(method, endpoint, token, payload=None, transport=None):
    if transport:
        return transport(method, endpoint, payload)
    url = "https://api.github.com" + endpoint
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "MG-R5-QA-comment-bot",
    }
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return json.loads(response.read(2_000_000))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API {method} {endpoint}: HTTP {exc.code}") from None


def safe_event(event, repository):
    run = event.get("workflow_run", {})
    if not REPO_RE.fullmatch(repository):
        raise ValueError("Invalid repository")
    if run.get("name") != "Pilot 001 Render and QA Artifact":
        raise ValueError("Unexpected upstream workflow")
    if run.get("event") != "pull_request" or run.get("conclusion") != "success":
        raise ValueError("Only successful PR render runs can trigger R5 comments")
    if run.get("head_repository", {}).get("full_name", "").lower() != repository.lower():
        raise ValueError("External fork cannot trigger privileged R5")
    sha = run.get("head_sha", "")
    if not SHA_RE.fullmatch(sha):
        raise ValueError("Missing 40-character source SHA")
    if not isinstance(run.get("id"), int) or run["id"] < 1:
        raise ValueError("Missing source run ID")
    return sha, run["id"]


def associated_pr(repository, sha, token, transport=None):
    # PR is resolved using authenticated GitHub metadata, never untrusted ZIP.
    matches = api("GET", f"/repos/{repository}/commits/{sha}/pulls?per_page=100",
                  token, transport=transport)
    eligible = [
        item for item in matches
        if item.get("state") == "open"
        and item.get("head", {}).get("sha") == sha
        and item.get("head", {}).get("repo", {}).get("full_name", "").lower()
            == repository.lower()
        and item.get("base", {}).get("repo", {}).get("full_name", "").lower()
            == repository.lower()
        and isinstance(item.get("number"), int)
    ]
    if len(eligible) != 1:
        raise ValueError("Cannot unambiguously identify an open same-repo PR at source SHA")
    return eligible[0]["number"]


def neutral(value, maximum=600):
    s = re.sub(r"[\x00-\x1f\x7f]", " ", str(value or "")).strip()
    s = s.replace("@", "@\u200b").replace("<", "‹").replace(">", "›")
    s = s.replace("`", "'").replace("|", "¦")
    return s[:maximum] + ("…" if len(s) > maximum else "")


def comment_body(report, audit, repo, pr):
    if audit.get("decision") != report.get("decision"):
        raise ValueError("QA report and audit decision disagree")
    sha = report["implementation_commit"]
    run_id = audit["source_run_id"]
    if not SHA_RE.fullmatch(sha) or audit["implementation_commit"] != sha:
        raise ValueError("QA source SHA differs from audit")
    marker = f"<!-- mg-r5 run:{run_id} sha:{sha} -->"
    decision = report["decision"].upper()
    title = {"PASS": "Visual checks passed (Stage B only)",
             "REWORK": "Targeted rework required",
             "PENDING": "Human/video inspection still required",
             "BLOCKED": "Visual QA blocked"}[decision]
    rows = [
        marker,
        f"### R5 Independent Visual QA — {decision}",
        f"**{title}** — Automated model review; **not release approval**.",
        "",
        f"- **Source SHA**: `{sha}`",
        f"- **Build run**: https://github.com/{repo}/actions/runs/{run_id}",
        f"- **Provider/model**: `{neutral(audit['provider'], 50)}/{neutral(audit['model'], 80)}`",
        f"- **Spec SHA256**: `{report['spec_sha256']}`",
        f"- **Checks**: {sum(c['result']=='pass' for c in report['checks'])}"
        f"/{len(report['checks'])} pass",
        "- **Scope**: Silent Stage B preview only. Human release gate unchanged.",
        "",
        "**Summary:** " + neutral(report["summary"], 1100),
        "",
    ]
    for finding in report["findings"][:15]:
        at_time = finding.get("timestamp_s")
        at = f" at {at_time:g}s" if isinstance(at_time, (int, float)) else ""
        rows.append(
            f"- **{finding['severity']} {neutral(finding['id'], 60)}** "
            f"({neutral(finding['shot_id'], 60)}{at}): "
            f"{neutral(finding['observed'])}. "
            f"**Expected:** {neutral(finding['expected'])}. "
            f"**Fix:** {neutral(finding['fix_request'])}."
        )
    rows += [
        "", "Full `qa_report.json` and token usage are available in the R5 Actions artifact.",
        "Unverified claims, incomplete video input, or stale PR HEAD must never be considered PASS.",
    ]
    return "\n".join(rows)[:13500]


def publish(event, repository, token, report, audit, transport=None):
    if not token:
        raise ValueError("GITHUB_TOKEN missing")
    sha, run_id = safe_event(event, repository)
    if (report.get("implementation_commit") != sha
            or audit.get("implementation_commit") != sha
            or str(audit.get("source_run_id")) != str(run_id)):
        raise ValueError("Artifact/source-run metadata mismatch; comment refused")
    pr = associated_pr(repository, sha, token, transport)
    # Fetch current PR HEAD before sending comment; refuse stale source.
    current = api("GET", f"/repos/{repository}/pulls/{pr}", token, transport=transport)
    if (current.get("state") != "open" or
            current.get("head", {}).get("sha") != sha):
        raise ValueError("PR HEAD changed during review; stale comment suppressed")
    body = comment_body(report, audit, repository, pr)
    marker = f"<!-- mg-r5 run:{run_id} sha:{sha} -->"
    comments = api("GET", f"/repos/{repository}/issues/{pr}/comments?per_page=100",
                   token, transport=transport)
    if any(marker in item.get("body", "") for item in comments):
        print("Existing comment for this source run found; no duplicate")
        return None
    created = api("POST", f"/repos/{repository}/issues/{pr}/comments",
                  token, {"body": body}, transport=transport)
    print(f"R5 comment posted on PR #{pr}: {created.get('html_url','')}")
    return created


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--audit", required=True)
    args = parser.parse_args(argv)
    try:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
        event = json.loads(Path(args.event).read_text(encoding="utf-8"))
        publish(event, os.environ["GITHUB_REPOSITORY"],
                os.environ["GITHUB_TOKEN"], report, audit)
    except (OSError, ValueError, KeyError, RuntimeError, TypeError,
            json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
