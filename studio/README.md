# MG Studio — Local Web MVP

A **read-only first increment** of MG Studio, building on existing R0–R7 code
without replacing or disturbing it. Does not require npm, FastAPI or frontend
build tools; uses Python standard library and static HTML/JS.

From your mg-animation-skill checkout:

```bash
python3 studio/server.py
```

Open http://127.0.0.1:8765 and keep the terminal running.

Features:
- Project dashboard that reads existing local R0 workspaces and states
- Codex CLI installed/not-installed detection
- Explicit-button **read-only Codex probe**; fixed safe prompt, timeout, no
  arbitrary shell commands accepted from HTTP clients
- Loopback bind only and host/origin validation plus per-process CSRF token
- **No** API keys, automatic model charges, source file edits, GitHub mutations,
  R4 rework execution, R5 approval, or R7 publishing

Smoke tests: `python3 -m unittest discover -s tests -p test_mg_studio.py -v`.

Next increments: job queue/SQLite, provider configuration in macOS Keychain,
role selection, approval UI, isolated worktrees, Codex executor, R5 task/result
viewer and media preview. These are *planned*, not claimed complete.

Security limitation: Localhost is not a security sandbox; do not expose the
service via port forwarding or a LAN proxy. Codex probe runs locally using the
current Codex login. No secret value should be entered into this MVP.
