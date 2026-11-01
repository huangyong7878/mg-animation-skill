"""Build and audit the Agensi Free text-only distribution.

Repository tooling only: this file is deliberately excluded from the ZIP.
The package is an allowlisted set of UTF-8 text files with a root SKILL.md,
a deterministic ZIP, a per-file SHA256 manifest and a ZIP SHA256 sidecar.

Usage:
    python scripts/package_agensi_free.py
    python scripts/package_agensi_free.py --scan-only
    python scripts/package_agensi_free.py --verify distributions/agensi-free/dist/agensi-free-1.0.0.zip
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = ROOT / "distributions" / "agensi-free"
DEFAULT_OUT = PACKAGE_ROOT / "dist"

ALLOWED_PATTERNS = (
    "SKILL.md",
    "README.md",
    "references/*.md",
    "examples/*.md",
    "examples/*.json",
)
TEXT_SUFFIXES = {".md", ".json"}
ALLOWED_NAME_RE = re.compile(
    r"^(?:SKILL\.md|README\.md|references/[A-Za-z0-9._-]+\.md|examples/[A-Za-z0-9._-]+\.(?:md|json))$"
)
MAX_FILES = 100
MAX_TOTAL_BYTES = 2 * 1024 * 1024
MAX_TOTAL_CHARS = 2_000_000
FIXED_DATE = (1980, 1, 1, 0, 0, 0)
ALLOWED_URL_HOST = "github.com"
ALLOWED_URL_PATH = "/huangyong7878/mg-animation-skill"


def is_allowed_url(url: str) -> bool:
    """Only the exact source-repository host/path is allowed.

    A bare prefix check would accept lookalikes such as
    ``https://github.com/huangyong7878/mg-animation-skill.evil.com``.
    """
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_URL_HOST:
        return False
    if parsed.username or parsed.password or port not in (None, 443):
        return False
    path = parsed.path.rstrip("/")
    return path == ALLOWED_URL_PATH or path.startswith(ALLOWED_URL_PATH + "/")


def member_name_issues(name: str) -> list[str]:
    """Shared path rules for the builder and the verifier.

    Keeping one function prevents the two sides from drifting; the verifier
    must never attest to a package the builder would refuse to produce.
    """
    issues: list[str] = []
    parts = PurePosixPath(name)
    if not ALLOWED_NAME_RE.match(name):
        issues.append("not on the allowlist")
    if parts.is_absolute() or ".." in parts.parts or "\\" in name or name.startswith("/"):
        issues.append("unsafe path")
    if any(part.startswith(".") for part in parts.parts):
        issues.append("hidden file")
    if name != "SKILL.md" and parts.name == "SKILL.md":
        issues.append("nested SKILL.md")
    if parts.suffix.lower() not in TEXT_SUFFIXES:
        issues.append("non-text suffix")
    return issues

SECRET_PATTERNS = (
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"gh[pousr]_[A-Za-z0-9]{20,}", "GitHub token"),
    (r"sk-[A-Za-z0-9]{20,}", "API secret key"),
    (r"-----BEGIN (?:RSA |OPENSSH |EC |PGP )?PRIVATE KEY-----", "private key"),
    (r"(?i)\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]", "credential assignment"),
)
DANGEROUS_PATTERNS = (
    (r"\bshell\s*=\s*True\b", "shell=True"),
    (r"\bos\.system\s*\(", "os.system"),
    (r"\bsubprocess\.(?:run|Popen|call)\s*\(", "subprocess execution"),
    (r"\beval\s*\(", "eval"),
    (r"\bexec\s*\(", "exec"),
    (r"curl[^\n|]*\|\s*(?:ba)?sh", "curl pipe to shell"),
    (r"wget[^\n|]*\|\s*(?:ba)?sh", "wget pipe to shell"),
    (r"rm\s+-rf\s+/(?:\s|$)", "root deletion"),
    (r"powershell[^\n]*-enc(?:odedcommand)?\b", "encoded PowerShell"),
    (r"base64\s+-d\b", "base64 decode"),
)
INJECTION_PATTERNS = (
    (r"(?i)ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions", "prompt-injection phrase"),
    (r"(?i)disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions", "prompt-injection phrase"),
    (r"(?i)you\s+are\s+now\s+(?:a|an|the)\b", "role-replacement phrase"),
    (r"<\|im_start\|>", "chat template token"),
    (r"\[/?INST\]", "instruction template token"),
    (r"BEGIN\s+SYSTEM\s+PROMPT", "fake system prompt"),
)
ABSOLUTE_PATH_PATTERNS = (
    (r"(?<![\w.])/(?:Users|home|root|etc|opt|usr|var|private|tmp)/", "absolute POSIX path"),
    (r"\b[A-Za-z]:\\", "absolute Windows path"),
)
REMOTE_ASSET_PATTERN = r'"asset"\s*:\s*"(?:https?|data|file):'
DATA_URL_PATTERN = r"data:[a-z0-9.+-]+/[a-z0-9.+-]+;base64,"
LONG_BASE64_PATTERN = r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{200,}={0,2}"
INVISIBLE_CHARS = "​‌‍‎‏‪‫‬‭‮⁠﻿"


class PackageError(RuntimeError):
    """Raised when the package fails an allowlist, safety or integrity check."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def read_version(package_root: Path = PACKAGE_ROOT) -> str:
    skill = Path(package_root) / "SKILL.md"
    match = re.search(r"^version:\s*([0-9A-Za-z._-]+)\s*$", skill.read_text(encoding="utf-8"), re.M)
    if not match:
        raise PackageError("SKILL.md frontmatter is missing a single-line version")
    return match.group(1)


def collect_files(package_root: Path = PACKAGE_ROOT) -> list[tuple[str, Path]]:
    package_root = Path(package_root).resolve()
    selected: dict[str, Path] = {}
    for pattern in ALLOWED_PATTERNS:
        for path in sorted(package_root.glob(pattern)):
            if path.is_symlink():
                raise PackageError(f"Symlinks are not allowed: {path.relative_to(package_root).as_posix()}")
            if not path.is_file():
                continue
            try:
                path.resolve().relative_to(package_root)
            except ValueError as exc:
                raise PackageError(f"File escapes package root: {path}") from exc
            rel = path.relative_to(package_root).as_posix()
            issues = member_name_issues(rel)
            if issues:
                raise PackageError(f"Invalid package file {rel}: {', '.join(issues)}")
            selected[rel] = path
    if "SKILL.md" not in selected:
        raise PackageError("Package root must contain SKILL.md")
    skill_names = [rel for rel in selected if PurePosixPath(rel).name == "SKILL.md"]
    if skill_names != ["SKILL.md"]:
        raise PackageError(f"Package must contain exactly one root SKILL.md, found {skill_names}")
    files = [(rel, selected[rel]) for rel in sorted(selected)]
    if not files:
        raise PackageError("Package is empty")
    if len(files) > MAX_FILES:
        raise PackageError(f"Too many files: {len(files)} > {MAX_FILES}")
    total_bytes = sum(path.stat().st_size for _, path in files)
    if total_bytes > MAX_TOTAL_BYTES:
        raise PackageError(f"Package too large: {total_bytes} > {MAX_TOTAL_BYTES} bytes")
    return files


def scan_text(rel: str, text: str) -> list[str]:
    issues: list[str] = []
    for pattern, label in SECRET_PATTERNS:
        if re.search(pattern, text):
            issues.append(f"{rel}: possible secret ({label})")
    for pattern, label in DANGEROUS_PATTERNS:
        if re.search(pattern, text, re.I):
            issues.append(f"{rel}: dangerous construct ({label})")
    for pattern, label in INJECTION_PATTERNS:
        if re.search(pattern, text):
            issues.append(f"{rel}: {label}")
    for pattern, label in ABSOLUTE_PATH_PATTERNS:
        if re.search(pattern, text):
            issues.append(f"{rel}: {label}")
    if re.search(REMOTE_ASSET_PATTERN, text):
        issues.append(f"{rel}: remote or embedded asset reference")
    if re.search(DATA_URL_PATTERN, text, re.I):
        issues.append(f"{rel}: base64 data URL")
    if re.search(LONG_BASE64_PATTERN, text):
        issues.append(f"{rel}: long base64-like blob")
    if "\x00" in text:
        issues.append(f"{rel}: NUL byte in text")
    for char in INVISIBLE_CHARS:
        if char in text:
            issues.append(f"{rel}: invisible or bidirectional control character U+{ord(char):04X}")
            break
    if "PK\x03\x04" in text:
        issues.append(f"{rel}: embedded ZIP signature")
    for url in re.findall(r"https?://[^\s)\]>\"']+", text):
        if url.startswith("http://"):
            issues.append(f"{rel}: insecure http URL {url}")
        elif not is_allowed_url(url):
            issues.append(f"{rel}: non-allowlisted external URL {url}")
    return issues


def check_file_contents(files: list[tuple[str, Path]], check_links: bool = True) -> list[str]:
    issues: list[str] = []
    texts: dict[str, str] = {}
    total_chars = 0
    for rel, path in files:
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            issues.append(f"{rel}: not valid UTF-8 ({exc})")
            continue
        texts[rel] = text
        total_chars += len(text)
        issues.extend(scan_text(rel, text))
    if total_chars > MAX_TOTAL_CHARS:
        issues.append(f"Package text too large: {total_chars} > {MAX_TOTAL_CHARS} chars")
    if check_links and "SKILL.md" in texts:
        referenced = set(re.findall(r"references/[A-Za-z0-9._-]+\.md", texts["SKILL.md"]))
        referenced.update(re.findall(r"references/[A-Za-z0-9._-]+\.md", texts.get("README.md", "")))
        for ref in sorted(referenced):
            if ref not in texts:
                issues.append(f"SKILL.md/README link points to missing package file: {ref}")
    return issues


def build_package(package_root: Path = PACKAGE_ROOT, out_dir: Path = DEFAULT_OUT) -> dict:
    package_root = Path(package_root).resolve()
    out_dir = Path(out_dir).resolve()
    files = collect_files(package_root)
    issues = check_file_contents(files)
    if issues:
        raise PackageError("Package checks failed:\n" + "\n".join(issues))
    version = read_version(package_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"agensi-free-{version}.zip"
    entries = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for rel, path in files:
            data = path.read_bytes()
            info = zipfile.ZipInfo(rel, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
            entries.append({"path": rel, "bytes": len(data), "sha256": sha256_bytes(data)})
    zip_sha = sha256_file(zip_path)
    manifest = {
        "package": zip_path.name,
        "version": version,
        "sha256": zip_sha,
        "file_count": len(entries),
        "total_bytes": sum(entry["bytes"] for entry in entries),
        "files": entries,
    }
    manifest_path = out_dir / f"{zip_path.stem}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sidecar = out_dir / f"{zip_path.name}.sha256"
    sidecar.write_text(f"{zip_sha}  {zip_path.name}\n", encoding="utf-8")
    return {"zip": zip_path, "manifest": manifest_path, "sha256_file": sidecar, "data": manifest}


def verify_package(zip_path: Path, manifest_path: Path | None = None) -> dict:
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        raise PackageError(f"Missing package: {zip_path}")
    manifest_path = Path(manifest_path) if manifest_path else zip_path.with_name(f"{zip_path.stem}.manifest.json")
    if not manifest_path.is_file():
        raise PackageError(f"Missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("package") != zip_path.name:
        raise PackageError(f"Manifest package name mismatch: {manifest.get('package')} != {zip_path.name}")
    actual_zip_sha = sha256_file(zip_path)
    if manifest.get("sha256") != actual_zip_sha:
        raise PackageError("ZIP SHA256 does not match manifest")
    issues: list[str] = []
    total_bytes = 0
    total_chars = 0
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        if bad:
            raise PackageError(f"Corrupt ZIP member: {bad}")
        names = archive.namelist()
        if len(names) > MAX_FILES:
            issues.append(f"Too many ZIP members: {len(names)} > {MAX_FILES}")
        if len(names) != len(set(names)):
            issues.append("Duplicate ZIP member names")
        if names != sorted(names):
            issues.append("ZIP entries are not in sorted order")
        if names.count("SKILL.md") != 1:
            issues.append("ZIP must contain exactly one root SKILL.md")
        if any(name.endswith("/") for name in names):
            issues.append("ZIP contains directory entries")
        for name in names:
            for issue in member_name_issues(name):
                issues.append(f"Invalid ZIP member {name}: {issue}")
            if name.lower().endswith((".zip", ".py", ".exe", ".dll", ".so", ".dylib", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".mp3", ".mp4", ".wav", ".ttf", ".otf", ".bin")):
                issues.append(f"Disallowed ZIP member type: {name}")
            info = archive.getinfo(name)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                issues.append(f"Symlink ZIP member is not allowed: {name}")
            if mode & 0o111:
                issues.append(f"Executable permission set: {name}")
            data = archive.read(name)
            total_bytes += len(data)
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                issues.append(f"ZIP member is not UTF-8 text: {name}")
                continue
            total_chars += len(text)
            issues.extend(scan_text(name, text))
        manifest_files = manifest.get("files", [])
        manifest_entries = {entry["path"]: entry for entry in manifest_files}
        if len(manifest_files) != len(manifest_entries):
            issues.append("Manifest contains duplicate paths")
        if set(manifest_entries) != set(names):
            issues.append("Manifest file list does not match ZIP contents")
        if manifest.get("file_count") != len(names):
            issues.append("Manifest file_count does not match ZIP contents")
        if len(manifest_files) != len(names):
            issues.append("Manifest file list length does not match ZIP contents")
        if manifest.get("total_bytes") != total_bytes:
            issues.append("Manifest total_bytes does not match ZIP contents")
        for name in names:
            data = archive.read(name)
            entry = manifest_entries.get(name, {})
            if entry.get("bytes") != len(data):
                issues.append(f"Manifest byte count mismatch: {name}")
            if entry.get("sha256") != sha256_bytes(data):
                issues.append(f"Manifest SHA256 mismatch: {name}")
    if total_bytes > MAX_TOTAL_BYTES:
        issues.append(f"ZIP too large: {total_bytes} > {MAX_TOTAL_BYTES} bytes")
    if total_chars > MAX_TOTAL_CHARS:
        issues.append(f"ZIP text too large: {total_chars} > {MAX_TOTAL_CHARS} chars")
    if issues:
        raise PackageError("Package verification failed:\n" + "\n".join(issues))
    return {"zip": zip_path, "manifest": manifest_path, "data": manifest}


def scan_source(package_root: Path = PACKAGE_ROOT) -> list[str]:
    files = collect_files(package_root)
    return check_file_contents(files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify the Agensi Free text-only ZIP")
    parser.add_argument("--package-root", type=Path, default=PACKAGE_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--verify", type=Path, default=None, help="Verify an existing ZIP instead of building")
    parser.add_argument("--scan-only", action="store_true", help="Scan source files without building")
    args = parser.parse_args(argv)
    try:
        if args.scan_only:
            issues = scan_source(args.package_root)
            if issues:
                print("FAIL: package scan", file=sys.stderr)
                for issue in issues:
                    print(" -", issue, file=sys.stderr)
                return 1
            print("PASS: package scan (allowlist, secrets, commands, injection, paths, links)")
            return 0
        if args.verify:
            result = verify_package(args.verify)
            print(f"PASS: {result['zip']} | sha256 {result['data']['sha256']} | {result['data']['file_count']} files")
            return 0
        result = build_package(args.package_root, args.out_dir)
        data = result["data"]
        print(f"BUILT {result['zip']}")
        print(f"MANIFEST {result['manifest']}")
        print(f"SHA256 {data['sha256']}")
        print(f"FILES {data['file_count']} | BYTES {data['total_bytes']}")
        verify_package(result["zip"], result["manifest"])
        print("PASS: deterministic ZIP structure, manifest and safety scan")
        return 0
    except PackageError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
