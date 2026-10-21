"""MG Studio MVP: loopback-only read-only project dashboard and Codex probe."""
import argparse
import json
import re
import secrets
import uuid
import time
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
    job = {"status": "idle", "output": "", "started": 0}
    job_lock = threading.Lock()

    def run_probe():
        try:
            proc = subprocess.run(
                ["codex", "exec", "--sandbox", "read-only",
                 "Answer only: 测试成功。 Do not read or change files."],
                cwd=repo, capture_output=True, text=True, timeout=360, check=False)
            with job_lock:
                job["status"] = "completed" if proc.returncode == 0 else "failed"
                job["output"] = (proc.stdout + "\\n" + proc.stderr)[-8000:]
        except subprocess.TimeoutExpired as exc:
            with job_lock:
                job["status"] = "timed_out"
                job["output"] = "Codex connection still unavailable after 360s."
        except OSError as exc:
            with job_lock:
                job["status"] = "failed"
                job["output"] = str(exc)

    try:
        from studio.job_store import JobStore
    except ModuleNotFoundError:
        from job_store import JobStore
    store = JobStore(repo / "work/mg_studio/jobs.sqlite3")
    r4 = {"status": "idle", "output": "", "result": None, "job_id": None}
    def available_tasks():
        try:
            from studio.r4_runner import validate_assignment
        except ModuleNotFoundError:
            from r4_runner import validate_assignment
        tasks = []
        for p in sorted((repo / "work/r4_inbox").glob("*/assignment.json")):
            try:
                task = validate_assignment(repo, p)
                tasks.append({"id": p.parent.name, "project": task["project_id"],
                              "findings": len(task["findings"])})
            except (ValueError, OSError, subprocess.CalledProcessError):
                continue
        return tasks
    active_task = {"path": None}
    def run_r4():
        try:
            try:
                from studio.r4_runner import execute
            except ModuleNotFoundError:
                from r4_runner import execute
            result = execute(repo, active_task["path"])
            with job_lock:
                r4.update(status=result["status"], output=result["output"], result=result)
                store.finish(r4["job_id"], result["status"], result)
        except Exception as exc:
            with job_lock:
                r4.update(status="failed", output=type(exc).__name__ + ": " + str(exc))
                store.finish(r4["job_id"], "failed", {"error": type(exc).__name__})

    rendering = {"status": "idle", "result": None}
    def run_render(run_id):
        try:
            try:
                from studio.delivery import run_build
            except ModuleNotFoundError:
                from delivery import run_build
            result = run_build(repo, run_id)
            with job_lock:
                rendering.update(status=result["status"], result=result)
        except Exception as exc:
            with job_lock:
                rendering.update(status="failed", result={"error":str(exc)[:500]})

    review_job = {"status":"idle", "result":None, "delivery_id":None}
    def run_paid_review(delivery_id):
        try:
            from studio.r5_submit import submit_review
            result = submit_review(repo, delivery_id)
            with job_lock:
                review_job.update(status="completed", result=result)
        except Exception as exc:
            with job_lock:
                review_job.update(status="failed", result={"error":str(exc)[:600]})

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
            if path == "/api/r5/paid-status":
                with job_lock:
                    return self._json(200, dict(review_job))
            if path.startswith("/api/r5/preflight/"):
                try:
                    from studio.r5_submit import review_preflight
                    return self._json(200, review_preflight(repo,path.split("/")[-1]))
                except (ValueError, OSError, KeyError) as exc:
                    return self._json(422, {"error":str(exc)})
            if path == "/api/r5/history":
                try:
                    from studio.r5_dashboard import review_history
                except ModuleNotFoundError:
                    from r5_dashboard import review_history
                return self._json(200, {"reviews": review_history(repo)})
            if path == "/api/deliveries":
                try:
                    from studio.delivery_viewer import list_deliveries
                except ModuleNotFoundError:
                    from delivery_viewer import list_deliveries
                return self._json(200, {"deliveries": list_deliveries(repo)})
            match = re.fullmatch(r"/api/deliveries/([^/]+)/video", path)
            if match:
                try:
                    from studio.delivery_viewer import verified_video
                except ModuleNotFoundError:
                    from delivery_viewer import verified_video
                try:
                    video = verified_video(repo, match.group(1))
                except (ValueError, OSError, KeyError, TypeError):
                    return self._json(404, {"error": "Verified video unavailable"})
                total = video.stat().st_size
                requested = self.headers.get("Range")
                start, end = 0, total - 1
                if requested:
                    m = re.fullmatch(r"bytes=(\d+)-(\d*)", requested)
                    if not m:
                        return self._json(416, {"error": "Unsupported range"})
                    start = int(m.group(1))
                    end = min(int(m.group(2)), total - 1) if m.group(2) else total - 1
                    if start >= total or end < start:
                        return self._json(416, {"error": "Range not satisfiable"})
                self.send_response(206 if requested else 200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(end-start+1))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                if requested:
                    self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
                self.end_headers()
                try:
                    with video.open("rb") as stream:
                        stream.seek(start)
                        remaining = end-start+1
                        while remaining:
                            chunk = stream.read(min(65536,remaining))
                            if not chunk: break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            if path == "/api/delivery/preflight":
                try:
                    from studio.delivery import preflight
                except ModuleNotFoundError:
                    from delivery import preflight
                return self._json(200, preflight(repo))
            if path == "/api/delivery/status":
                with job_lock:
                    return self._json(200, dict(rendering))
            if path == "/api/r4/history":
                return self._json(200, {"jobs": store.list()})
            if path == "/api/r4/tasks":
                return self._json(200, {"tasks": available_tasks()})
            if path == "/api/r4":
                with job_lock:
                    return self._json(200, dict(r4))
            if path == "/api/codex-probe":
                with job_lock:
                    return self._json(200, {**job,
                        "elapsed_seconds": round(time.monotonic() - job["started"], 1)
                        if job["status"] == "running" else 0})
            if path == "/api/csrf":
                return self._json(200, {"token": token})
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            if not self._origin_ok() or self.headers.get("X-MG-CSRF") != token:
                return self._json(403, {"error": "forbidden"})
            path = urlparse(self.path).path
            if path not in ("/api/codex-probe", "/api/r4/start", "/api/delivery/build", "/api/r5/submit"):
                return self._json(404, {"error": "not found"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self._json(400, {"error": "invalid request size"})
            if size < 0 or size > MAX_BODY:
                return self._json(413, {"error": "request too large"})
            self._request_body = self.rfile.read(size)
            if path == "/api/r5/submit":
                try:
                    from studio.r5_submit import review_preflight
                    req = json.loads(self._request_body.decode("utf-8"))
                    delivery_id = req["delivery_id"]
                    if req.get("confirm_paid_sampled_review") is not True:
                        raise ValueError("Explicit paid sampled-frame review confirmation required")
                    checked = review_preflight(repo,delivery_id)
                    if not checked["ready"]:
                        return self._json(422, checked)
                except (ValueError, TypeError, KeyError, OSError) as exc:
                    return self._json(422, {"error":str(exc)})
                with job_lock:
                    if review_job["status"] != "idle":
                        return self._json(409, {"error":"R5 already started this session"})
                    review_job.update(status="running", delivery_id=delivery_id, result=None)
                threading.Thread(target=run_paid_review,args=(delivery_id,),daemon=True).start()
                return self._json(202, {"status":"running"})
            if path == "/api/delivery/build":
                try:
                    from studio.delivery import preflight
                except ModuleNotFoundError:
                    from delivery import preflight
                check = preflight(repo)
                if not check["ready"]:
                    return self._json(422, check)
                with job_lock:
                    if rendering["status"] != "idle":
                        return self._json(409, {"error":"Render already started this session"})
                    identifier = uuid.uuid4().hex[:16]
                    rendering.update(status="running", result=None)
                threading.Thread(target=run_render, args=(identifier,), daemon=True).start()
                return self._json(202, {"status":"running", "run_id":identifier})
            if path == "/api/r4/start":
                if not _which("codex"):
                    return self._json(422, {"error": "Codex CLI not found"})
                try:
                    from studio.r4_runner import validate_assignment
                except ModuleNotFoundError:
                    from r4_runner import validate_assignment
                try:
                    supplied = json.loads(self._request_body.decode("utf-8"))
                    job_id = supplied["task_id"]
                    if not isinstance(job_id, str) or not job_id or not all(c.isalnum() or c in "-_" for c in job_id):
                        raise ValueError("Invalid task ID")
                    path_to_task = repo / "work/r4_inbox" / job_id / "assignment.json"
                    validate_assignment(repo, path_to_task)
                except (ValueError, OSError, subprocess.CalledProcessError) as exc:
                    return self._json(422, {"error": str(exc)})
                with job_lock:
                    if r4["status"] == "running" or store.active():
                        return self._json(409, {"error": "R4 already started; inspect existing result"})
                    identifier = store.start(job_id)
                    active_task["path"] = path_to_task
                    r4.update(status="running", output="Starting isolated worktree…",
                              result=None, job_id=identifier)
                threading.Thread(target=run_r4, daemon=True).start()
                return self._json(202, {"status": "running", "job_id": identifier})
            if not _which("codex"):
                return self._json(422, {"error": "Codex CLI not found"})
            with job_lock:
                if job["status"] == "running":
                    return self._json(409, {"error": "probe already running"})
                job.update(status="running", output="", started=time.monotonic())
            threading.Thread(target=run_probe, daemon=True).start()
            return self._json(202, {"status": "running"})

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
