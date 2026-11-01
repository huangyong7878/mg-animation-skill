# A7 — Manual Security Review

Reviewer: Agent B (AI role) · Date: 2026-11-01
Scope: the 13 files in the final `agensi-free-1.0.0.zip` (SKILL.md, README.md,
three references, eight example files) plus the repository-side packaging and
test scripts.

## Automated scan

Command: `python3 scripts/package_agensi_free.py --scan-only`

Result: `PASS: package scan (allowlist, secrets, commands, injection, paths, links)`

Checks enforced:

- allowlist of text suffixes and paths;
- AWS/GitHub/API-key/private-key/credential patterns;
- `shell=True`, `os.system`, `subprocess`, `eval`, `exec`, `curl|sh`,
  `wget|sh`, root deletion, encoded PowerShell, base64 decode;
- prompt-injection phrases and chat-template tokens;
- absolute POSIX/Windows paths;
- remote/`data:` asset references and long base64 blobs;
- invisible and bidirectional control characters;
- embedded ZIP signatures;
- non-allowlisted external URLs and plain `http://` links.

## Manual review findings

| Area | Finding |
|---|---|
| Executable content | None. Every ZIP member is UTF-8 `.md` or `.json`; no scripts, binaries, archives or executable permission bits. |
| Network access | None in the package instructions for the text path. The only external URL is the static HTTPS source-repository link in `README.md`. No fetch, upload or telemetry instruction. |
| Credentials | No API keys, tokens, passwords, cookies or environment-variable collection. The skill explicitly forbids requesting or echoing them. |
| Shell / local execution | The free path instructs no terminal use. Optional local rendering is user-run, requires explicit approval, and uses documented repository scripts. The skill cannot execute anything by itself. |
| Prompt injection | Article/brief content is treated as data. Instructions embedded in user material are to be ignored; the safety reference states this explicitly. |
| Hidden content | No zero-width, bidi or template-token characters. No hidden HTML comments. |
| Dangerous file operations | None. No deletion, overwrite, traversal or absolute-path instructions. |
| Third-party assets | None. No images, fonts, audio, video, PDFs or copied text blocks. |
| Package structure | One root `SKILL.md`, one `README.md`, three references, eight example files. No nesting, no duplicate skill. |
| URL allowlist | Exact `https://github.com/huangyong7878/mg-animation-skill` host/path only; lookalike domains are rejected by `is_allowed_url`. |
| Symlinks | The builder rejects symlinks and any resolved path outside the package root; the verifier rejects symlink ZIP members. |
| Hidden / duplicate members | The shared `member_name_issues` rejects hidden/dot components; the verifier rejects duplicate ZIP names and duplicate manifest paths. |
| Permissions requested | The text path needs only the source the user provides. Optional rendering asks for the minimum local terminal/file access and is gated on approval. |

## Residual risks

1. The host agent may have terminal or network tools regardless of the skill's
   instructions. The host operator remains responsible for its permission
   settings; the skill cannot sandbox the host.
2. Optional local rendering executes the user's existing renderer and TTS
   stack. Its supply-chain integrity is outside this package.
3. Static documentation can become stale. The Agensi limits quoted in
   `references/safety-and-limitations.md` were checked on 2026-10-31 and must
   be rechecked before submission.
4. The source-repository link could change or be redirected; it is a plain
   link, not fetched automatically.

## Verdict

**PASS for the automated and manual checks performed here.**
No package content executes code or contacts the network. This is not a
substitute for the Agensi platform's own 8-category scan and human review;
the platform result is unknown until an actual submission.
