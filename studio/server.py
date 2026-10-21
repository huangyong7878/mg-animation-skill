"""MG Studio MVP: loopback-only read-only project dashboard and Codex probe."""
import argparse
import json
import secrets
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
UI = Path(__file__).with_name("index.html")
MAX_BODY = 2048

def project_snapshot(repo):
    items = []
    for name in ("formal_r4", "formal_r4_v2"):
        p = repo / "work" / "orders_pilot" / name / "state.json"
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                items.append({"name": name, "status": data.get("status", "unknown"),
                              "attempt": data.get("attempt", 0),
                              "implementation_commit": data.get("implementation_commit"),
                              "production_mode": data.get("production_mode")})
            except (ValueError, OSError):
                items.append({"name": name, "status": "unreadable"})
    return {"project": "Pilot 001 · 两张订单，两条路径",
            "workspaces": items, "codex_installed": bool(_which("codex")),
            "mode": "read_only_mvp", "r7_release_allowed": False}

def _which(name):
    from shutil import which
    return which(name)

def create_handler(repo, token):
    class Handler(BaseHTTPRequestHandler):
        def _reply(self, status, body, content_type="application/json; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, status, obj):
            self._reply(status, json.dumps(obj, ensure_ascii=False))

        def _origin_ok(self):
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin", "")
            return host in {"127.0.0.1:8765", "localhost:8765"} and (
                not origin or origin in {"http://127.0.0.1:8765", "http://localhost:8765"})

        def do_GET(self):
            if not self._origin_ok():
                return self._json(403, {"error": "invalid host/origin"})
            path = urlparse(self.path).path
            if path == "/":
                return self._reply(200, UI.read_bytes(), "text/html; charset=utf-8")
            if path == "/app.js":
                return self._reply(200, UI.with_name("app.js").read_bytes(),
                                   "application/javascript; charset=utf-8")
            if path == "/api/status":
                return self._json(200, project_snapshot(repo))
            if path == "/api/csrf":
                return self._json(200, {"token": token})
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._origin_ok() or self.headers.get("X-MG-CSRF") != token:
                return self._json(403, {"error": "forbidden"})
            if urlparse(self.path).path != "/api/codex-probe":
                return self._json(404, {"error": "not found"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self._json(400, {"error": "invalid request size"})
            if size < 0 or size > MAX_BODY:
                return self._json(413, {"error": "request too large"})
            self.rfile.read(size)
            if not _which("codex"):
                return self._json(422, {"error": "Codex CLI not found"})
            # Fixed, read-only prompt; no arbitrary commands, no model-chosen permissions.
            try:
                proc = subprocess.run(
                    ["codex", "exec", "--sandbox", "read-only",
                     "Read README.md and summarize the repository in three sentences. Do not edit files."],
                    cwd=repo, capture_output=True, text=True, timeout=120, check=False)
                return self._json(200, {"ok": proc.returncode == 0,
                    "returncode": proc.returncode,
                    "output": (proc.stdout + "\n" + proc.stderr)[-5000:]})
            except subprocess.TimeoutExpired:
                return self._json(504, {"error": "Codex probe timed out"})

        def log_message(self, format, *args):
            pass
    return Handler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not (repo / "workflow" / "orchestrator.py").is_file():
        parser.error("--repo must point to the mg-animation-skill checkout")
    token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", 8765), create_handler(repo, token))
    print("MG Studio: http://127.0.0.1:8765")
    print("MVP only: no API keys, code writes, GitHub actions or publishing.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
