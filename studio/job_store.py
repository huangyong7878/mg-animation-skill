"""SQLite journal for locally launched MG Studio R4 jobs.

Never stores credentials or full model transcripts. Interrupted running jobs
become 'interrupted' on restart; they are not automatically retried.
"""
import json
import sqlite3
import threading
import time
from pathlib import Path

class JobStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started REAL NOT NULL,
                updated REAL NOT NULL,
                result_json TEXT
            )""")
            db.execute("UPDATE jobs SET status='interrupted', updated=? WHERE status='running'",
                       (time.time(),))

    def _db(self):
        return sqlite3.connect(self.path, timeout=5)

    def active(self):
        with self.lock, self._db() as db:
            return db.execute("SELECT id FROM jobs WHERE status='running' LIMIT 1").fetchone() is not None

    def start(self, task_id):
        with self.lock, self._db() as db:
            if db.execute("SELECT 1 FROM jobs WHERE status='running' LIMIT 1").fetchone():
                raise ValueError("Another R4 job is running")
            now = time.time()
            row = db.execute("INSERT INTO jobs (task_id,status,started,updated) VALUES (?,?,?,?)",
                             (task_id,"running",now,now))
            return row.lastrowid

    def finish(self, job_id, status, result):
        if status not in {"ready_for_manual_review","executor_failed","blocked","failed"}:
            raise ValueError("Invalid R4 terminal state")
        # Do not store raw model transcripts, potentially containing secrets.
        safe = {k: result[k] for k in ("worktree","base_commit","changed_files",
                    "forbidden_files","head_changed","exit_code","note") if k in result}
        if "error" in result:
            safe["error"] = str(result["error"])[:300]
        with self.lock, self._db() as db:
            cur = db.execute("UPDATE jobs SET status=?,updated=?,result_json=? WHERE id=? AND status='running'",
                       (status,time.time(),json.dumps(safe,ensure_ascii=False),job_id))
            if cur.rowcount != 1:
                raise ValueError("R4 job no longer running")

    def list(self, limit=20):
        with self.lock, self._db() as db:
            rows = db.execute("SELECT id,task_id,status,started,updated,result_json FROM jobs ORDER BY id DESC LIMIT ?",
                              (min(max(1,limit),100),)).fetchall()
        return [{"id":r[0], "task_id":r[1], "status":r[2],
                 "started":r[3], "updated":r[4],
                 "result":json.loads(r[5]) if r[5] else None} for r in rows]
