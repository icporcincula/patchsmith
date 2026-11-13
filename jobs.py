"""Bounded process-local background jobs for slow local model calls."""

from collections import OrderedDict, deque
import json
from threading import Lock, Thread
from uuid import uuid4

JOBS = OrderedDict()
QUEUE = deque()
LOCK = Lock()
LIMIT = 50
MAX_PENDING = 10
WORKER = False


def start(args, handler):
    global WORKER
    values = dict(args)
    values.pop("background", None)
    with LOCK:
        if len(QUEUE) >= MAX_PENDING:
            return {"status": "error", "reason": "queue_full", "note": "The local task queue is full."}
        while len(JOBS) >= LIMIT and next(iter(JOBS.values()))["status"] == "completed":
            JOBS.popitem(last=False)
        job_id = uuid4().hex
        JOBS[job_id] = {"status": "queued", "job_id": job_id, "position": len(QUEUE) + int(WORKER)}
        QUEUE.append((job_id, values, handler))
        launch = not WORKER
        if launch:
            WORKER = True

    def work():
        global WORKER
        while True:
            with LOCK:
                if not QUEUE:
                    WORKER = False
                    return
                current, submitted, action = QUEUE.popleft()
                JOBS[current] = {"status": "running", "job_id": current}
            try:
                result = json.loads(action(submitted))
            except Exception as exc:
                result = {"status": "error", "reason": "execution_error", "note": str(exc)}
            with LOCK:
                JOBS[current] = {"status": "completed", "job_id": current, "result": result}

    if launch:
        try:
            Thread(target=work, name="patchsmith-queue", daemon=True).start()
        except Exception as exc:
            with LOCK:
                QUEUE.clear()
                JOBS.pop(job_id, None)
                WORKER = False
            return {"status": "error", "reason": "job_start_failed", "note": str(exc)}
    return {"status": "queued" if not launch else "running", "job_id": job_id,
            "note": "Poll task_status in this process. Queue and handles expire on restart; keep the host open."}


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
