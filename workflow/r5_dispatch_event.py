#!/usr/bin/env python3
"""Resolve a manually selected *real* upstream render run before any paid R5 call.

The user supplies only a numeric Actions run ID, never PR identity, repository,
commit SHA or trusted workflow path. All are resolved via authenticated GitHub
metadata; only a successful same-repo PR run of the expected Pilot renderer is
eligible. A synthetic event passed to existing PR gates contains only values
verified against GitHub and never contains user-supplied fields unchecked.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from workflow.r5_pr_feedback import api, safe_event, associated_pr, REPO_RE
except ModuleNotFoundError:
    from r5_pr_feedback import api, safe_event, associated_pr, REPO_RE

RUN_RE = re.compile(r"^[1-9][0-9]{0,18}$")
EXPECTED_PATH = ".github/workflows/pilot-render-artifacts.yml"
EXPECTED_NAME = "Pilot 001 Render and QA Artifact"


def resolve_run(repository, run_id_text, token, transport=None):
    """Verify selected run and return safe metadata/compatibility event."""
    if not REPO_RE.fullmatch(repository):
        raise ValueError("Invalid repository")
    if not isinstance(run_id_text, str) or not RUN_RE.fullmatch(run_id_text):
        raise ValueError("Render run ID must be a positive decimal integer")
    run_id = int(run_id_text)
    run = api("GET", f"/repos/{repository}/actions/runs/{run_id}",
              token, transport=transport)
    if run.get("id") != run_id:
        raise ValueError("GitHub returned a different run ID")
    if run.get("name") != EXPECTED_NAME:
        raise ValueError("Selected run is not the Pilot 001 renderer")
    if run.get("path", "").split("@", 1)[0] != EXPECTED_PATH:
        raise ValueError("Selected run workflow path is not the trusted Pilot renderer")
    if run.get("event") != "pull_request" or run.get("status") != "completed":
        raise ValueError("Only a completed PR render run may be selected")
    if run.get("conclusion") != "success":
        raise ValueError("Selected render run did not succeed")
    if run.get("repository", {}).get("full_name", "").lower() != repository.lower():
        raise ValueError("Source render run belongs to a different repository")
    head_repo = run.get("head_repository") or {}
    if head_repo.get("full_name", "").lower() != repository.lower():
        raise ValueError("External fork cannot trigger privileged R5")
    sha = run.get("head_sha", "")
    event = {"workflow_run": {
        "id": run_id,
        "name": EXPECTED_NAME,
        "event": "pull_request",
        "conclusion": "success",
        "head_repository": {"full_name": repository},
        "head_sha": sha,
    }}
    # Existing gate checks the 40-character SHA and source run type.
    safe_event(event, repository)
    # Verify that the SHA actually belongs to exactly one current open PR, not
    # an old or unrelated run. Rechecked independently just before billing.
    pr = associated_pr(repository, sha, token, transport)
    current = api("GET", f"/repos/{repository}/pulls/{pr}",
                  token, transport=transport)
    if (current.get("state") != "open"
            or current.get("head", {}).get("sha") != sha):
        raise ValueError("PR HEAD changed; cannot bill an obsolete revision")
    return {
        "event": event, "pr": pr, "sha": sha, "run_id": run_id,
        "artifact_name": f"mg-orders_two_routes-r1-ci-{run_id}-{sha[:12]}",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--render-run-id", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    try:
        result = resolve_run(os.environ["GITHUB_REPOSITORY"],
                             args.render_run_id, os.environ["GITHUB_TOKEN"])
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result["event"], ensure_ascii=False) + "\n",
                          encoding="utf-8")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
                for label, value in (
                        ("source_run", result["run_id"]),
                        ("source_sha", result["sha"]),
                        ("artifact_name", result["artifact_name"])):
                    out.write(f"{label}={value}\n")
        print(f"Selected authenticated Pilot PR #{result['pr']}; "
              f"render run {result['run_id']}; source SHA {result['sha']}")
    except (KeyError, TypeError, ValueError, RuntimeError, OSError,
            json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
