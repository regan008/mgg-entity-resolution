"""
Subprocess launcher for pipeline stage scripts.

Launches the existing, unmodified scripts (preprocess.py, block.py, ...) as
child processes, captures their stdout/stderr into an in-memory ring buffer,
and exposes status for polling. One job per state at a time.
"""
import os
import subprocess
import sys
import threading
import time
import uuid

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Only these scripts may be launched, and only with these allowed flags —
# the dashboard never invents new pipeline behavior or arbitrary commands.
ALLOWED_SCRIPTS = {
    "preprocess": ("preprocess.py", set()),
    "block": ("block.py", set()),
    "score": ("score.py", set()),
    "adjudicate": ("adjudicate.py", {"--resume", "--skip-ai"}),
    "review_merge": ("review.py", set()),
    "consolidate": ("consolidate.py", set()),
    "assign_draft": ("assign_ids.py", set()),
    "assign_commit": ("assign_ids.py", {"--commit"}),
}

_LOG_MAX_LINES = 2000
_jobs: dict[str, dict] = {}
_state_locks: dict[str, str] = {}  # state -> job_id currently running for it
_lock = threading.Lock()


class JobConflict(Exception):
    pass


class UnknownScript(Exception):
    pass


def start_job(state: str, script_key: str, flags: list[str] | None = None) -> str:
    flags = flags or []
    if script_key not in ALLOWED_SCRIPTS:
        raise UnknownScript(f"Unknown script key: {script_key}")
    script_name, allowed_flags = ALLOWED_SCRIPTS[script_key]
    bad_flags = set(flags) - allowed_flags
    if bad_flags:
        raise UnknownScript(f"Flags not allowed for {script_key}: {bad_flags}")

    with _lock:
        existing = _state_locks.get(state)
        if existing and _jobs.get(existing, {}).get("status") == "running":
            raise JobConflict(f"A job is already running for state {state}")

        job_id = uuid.uuid4().hex[:12]
        cmd = [sys.executable, script_name, state, *flags]
        _jobs[job_id] = {
            "id": job_id,
            "state": state,
            "script": script_name,
            "cmd": " ".join(cmd),
            "status": "running",
            "lines": [],
            "started_at": time.time(),
            "ended_at": None,
            "returncode": None,
        }
        _state_locks[state] = job_id

    proc = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,  # never let a script block on input()
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    thread = threading.Thread(target=_pump_output, args=(job_id, proc), daemon=True)
    thread.start()
    return job_id


def _pump_output(job_id: str, proc: subprocess.Popen):
    job = _jobs[job_id]
    try:
        for line in proc.stdout:
            job["lines"].append(line.rstrip("\n"))
            if len(job["lines"]) > _LOG_MAX_LINES:
                job["lines"] = job["lines"][-_LOG_MAX_LINES:]
    finally:
        proc.wait()
        job["returncode"] = proc.returncode
        job["status"] = "done" if proc.returncode == 0 else "error"
        job["ended_at"] = time.time()
        with _lock:
            if _state_locks.get(job["state"]) == job_id:
                del _state_locks[job["state"]]


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def get_job_for_state(state: str) -> dict | None:
    job_id = _state_locks.get(state)
    return _jobs.get(job_id) if job_id else None


def get_log(job_id: str, since: int = 0) -> dict | None:
    job = _jobs.get(job_id)
    if job is None:
        return None
    return {
        "status": job["status"],
        "lines": job["lines"][since:],
        "total_lines": len(job["lines"]),
        "returncode": job["returncode"],
    }
