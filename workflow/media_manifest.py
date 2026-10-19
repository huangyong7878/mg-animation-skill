#!/usr/bin/env python3
"""Generate and verify an immutable media SHA256 manifest beside a delivery.

This tool does not upload to GitHub, decode the video, or perform visual QA.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

try:
    from workflow.check_handoff import canonical_digest, validate_bundle
except ModuleNotFoundError:
    from check_handoff import canonical_digest, validate_bundle

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "media_manifest.schema.json"
COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest_file(path):
    value = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def inside(root, relative):
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root) or Path(relative).is_absolute():
        raise ValueError(f"Media path escapes artifact root: {relative}")
    if not candidate.is_file() or candidate.stat().st_size == 0:
        raise ValueError(f"Media is missing/empty: {relative}")
    return candidate


def media_files(delivery, extras):
    artifacts = delivery["artifacts"]
    if not artifacts.get("video_path"):
        raise ValueError("Media manifest requires delivery.artifacts.video_path")
    entries = [("video", artifacts["video_path"])]
    entries += [("keyframe", p) for p in artifacts.get("keyframe_paths", [])]
    for role in ("audio", "timings"):
        path = artifacts.get(role + "_path")
        if path:
            entries.append((role, path))
    entries.extend(("additional", p) for p in extras)
    return entries


def create_manifest(spec, delivery, artifact_root, backend, artifact_name=None,
                    run_url=None, extras=(), location_url=None):
    errors = validate_bundle(spec, delivery)
    if errors:
        raise ValueError("Invalid handoff: " + "; ".join(errors))
    if not COMMIT_SHA.fullmatch(delivery["implementation_commit"]):
        raise ValueError("implementation_commit must be a full 40-character hex SHA")
    if backend == "actions" and not artifact_name:
        raise ValueError("Actions backend requires --artifact-name")
    if backend != "actions" and (artifact_name or run_url):
        raise ValueError("Artifact name/run URL only apply to actions backend")
    if backend == "external":
        if not location_url or not location_url.startswith("https://"):
            raise ValueError("External backend requires HTTPS --location-url")
    elif location_url:
        raise ValueError("--location-url only applies to external backend")
    if run_url and not re.fullmatch(
            r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[1-9][0-9]*",
            run_url):
        raise ValueError("Invalid GitHub Actions run URL")
    seen = set()
    files = []
    for role, relative in media_files(delivery, extras):
        if relative in seen:
            raise ValueError(f"Duplicate media path: {relative}")
        seen.add(relative)
        path = inside(artifact_root, relative)
        files.append({
            "role": role, "path": str(Path(relative).as_posix()),
            "size_bytes": path.stat().st_size,
            "sha256": digest_file(path),
        })
    manifest = {
        "schema_version": "1.0",
        "project_id": spec["project_id"],
        "spec_id": spec["spec_id"],
        "spec_revision": spec["revision"],
        "spec_sha256": canonical_digest(spec),
        "implementation_commit": delivery["implementation_commit"].lower(),
        "attempt": delivery["attempt"],
        "stage": delivery["stage"],
        "storage": {"backend": backend},
        "files": files,
    }
    if backend == "actions":
        manifest["storage"]["artifact_name"] = artifact_name
        if run_url:
            manifest["storage"]["run_url"] = run_url
    if backend == "external":
        manifest["storage"]["location_url"] = location_url
    validate_schema(manifest)
    return manifest


def validate_schema(manifest):
    validator = Draft202012Validator(read_json(SCHEMA))
    errors = sorted(validator.iter_errors(manifest), key=lambda e: list(map(str, e.absolute_path)))
    if errors:
        raise ValueError("Media manifest schema: " + "; ".join(e.message for e in errors))


def verify_manifest(manifest, artifact_root, spec=None, delivery=None):
    validate_schema(manifest)
    errors = []
    if (spec is None) != (delivery is None):
        raise ValueError("Provide both spec and delivery when checking provenance")
    if spec is not None:
        handoff = validate_bundle(spec, delivery)
        errors.extend(handoff)
        for field in ("project_id", "spec_id"):
            if manifest[field] != spec[field]:
                errors.append(f"Manifest {field} differs from director specification")
        if manifest["spec_revision"] != spec["revision"]:
            errors.append("Manifest director revision mismatch")
        if manifest["spec_sha256"] != canonical_digest(spec):
            errors.append("Manifest director fingerprint mismatch")
        if manifest["implementation_commit"] != delivery["implementation_commit"].lower():
            errors.append("Manifest implementation commit mismatch")
        if manifest["attempt"] != delivery["attempt"]:
            errors.append("Manifest attempt mismatch")
        expected_paths = {p for _, p in media_files(delivery, ())}
        covered = {entry["path"] for entry in manifest["files"]}
        if expected_paths - covered:
            errors.append(f"Manifest omitted declared delivery media: {sorted(expected_paths-covered)}")
    seen = set()
    for entry in manifest["files"]:
        relative = entry["path"]
        if relative in seen:
            errors.append(f"Duplicate media file entry: {relative}")
            continue
        seen.add(relative)
        try:
            path = inside(artifact_root, relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if path.stat().st_size != entry["size_bytes"]:
            errors.append(f"File size mismatch: {relative}")
        if digest_file(path) != entry["sha256"]:
            errors.append(f"File sha256 mismatch: {relative}")
    return errors


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--spec", required=True)
    create.add_argument("--delivery", required=True)
    create.add_argument("--artifact-root", required=True)
    create.add_argument("--backend", choices=("actions", "external", "local"), default="local")
    create.add_argument("--artifact-name")
    create.add_argument("--run-url")
    create.add_argument("--location-url")
    create.add_argument("--extra-file", action="append", default=[])
    create.add_argument("--out", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--artifact-root", required=True)
    verify.add_argument("--spec")
    verify.add_argument("--delivery")
    args = p.parse_args(argv)
    try:
        if args.command == "create":
            manifest = create_manifest(
                read_json(args.spec), read_json(args.delivery),
                args.artifact_root, args.backend, args.artifact_name,
                args.run_url, args.extra_file, args.location_url)
            out = Path(args.out).resolve()
            root = Path(args.artifact_root).resolve()
            if not out.is_relative_to(root):
                raise ValueError("Manifest must be saved INSIDE artifact root")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
            print(f"CREATED {out} | {len(manifest['files'])} media file(s)")
        else:
            if bool(args.spec) != bool(args.delivery):
                raise ValueError("Pass --spec AND --delivery, or neither")
            errors = verify_manifest(
                read_json(args.manifest), args.artifact_root,
                read_json(args.spec) if args.spec else None,
                read_json(args.delivery) if args.delivery else None)
            if errors:
                for issue in errors:
                    print("ERROR:", issue, file=sys.stderr)
                return 1
            print("PASS: media byte integrity and requested metadata checks")
        print("NOTE: No video decode, model invocation or visual QA performed.")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("ERROR:", str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
