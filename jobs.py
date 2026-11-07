"""Bounded process-local background jobs for slow local model calls."""

from collections import OrderedDict
import json
from threading import Lock, Thread
from uuid import uuid4

JOBS = OrderedDict()
LOCK = Lock()
LIMIT = 50


def start(args, handler):
    values = dict(args)
    values.pop("background", None)
    with LOCK:
        if any(row["status"] == "running" for row in JOBS.values()):
            return {"status": "error", "reason": "job_busy", "note": "A background task is already running in this Hermes process."}
        while len(JOBS) >= LIMIT:
            JOBS.popitem(last=False)
        job_id = uuid4().hex
        JOBS[job_id] = {"status": "running", "job_id": job_id}

    def work():
        try:
            result = json.loads(handler(values))
        except Exception as exc:
            result = {"status": "error", "reason": "execution_error", "note": str(exc)}
        with LOCK:
            JOBS[job_id] = {"status": "completed", "job_id": job_id, "result": result}

    try:
        Thread(target=work, name="patchsmith-" + job_id, daemon=True).start()
    except Exception as exc:
        with LOCK:
            JOBS.pop(job_id, None)
        return {"status": "error", "reason": "job_start_failed", "note": str(exc)}
    return {"status": "running", "job_id": job_id,
            "note": "Poll task_status in this Hermes process. Job handles expire on restart; keep Hermes open until completion."}


def task_status(args, **kwargs):
    try:
        job_id = args.get("job_id")
        if not isinstance(job_id, str) or len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
            raise ValueError("job_id must be the exact identifier returned by implement_task.")
        with LOCK:
            result = JOBS.get(job_id)
            if result is None:
                return json.dumps({"status": "error", "reason": "unknown_job", "note": "Unknown or expired job in this Hermes process."})
            return json.dumps(result)
    except Exception as exc:
        return json.dumps({"status": "error", "reason": "invalid_input", "note": str(exc)})
