"""Private local run summaries and the Hermes status command."""

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from threading import Lock
from uuid import uuid4

from .guards import data_root
from .tools import linked

LOCK = Lock()


def directory():
    return data_root() / "runs"


def record(result, seconds, mode):
    """Persist one completed call; never turn a completed edit into an error."""
    try:
        root = directory()
        if linked(root):
            raise OSError("The ledger directory must not be a link.")
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        row = {"version": 1, "completed_at": datetime.now(timezone.utc).isoformat(),
               "status": result["status"], "reason": result.get("reason"),
               "turns": result["turns"], "seconds": seconds,
               "tokens_est": result["tokens_est"], "mode": mode,
               "files_changed": result["files_changed"],
               "patch_path": result.get("patch_path"),
               "transcript_path": result.get("transcript_path")}
        # Unique, exclusive records avoid lost updates across Hermes processes.
        with LOCK:
            path = root / (uuid4().hex + ".tmp")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(row, stream)
            path.replace(path.with_suffix(".json"))
        return None
    except Exception as exc:
        return "Local ledger was not saved: " + str(exc)


def summaries():
    root = directory()
    if linked(root):
        raise OSError("The ledger directory must not be a link.")
    if root.exists() and not root.is_dir():
        raise OSError("The ledger location is not a directory.")
    rows, skipped = [], 0
    with LOCK:
        for path in root.glob("*.json"):
            try:
                if path.is_symlink() or path.stat().st_size > 262144:
                    raise ValueError("Invalid record file.")
                row = json.loads(path.read_text(encoding="utf-8"))
                if (row.get("version") != 1 or row.get("status") not in {"done", "blocked", "error"}
                        or any(type(row.get(k)) is not int or row[k] < 0 for k in ("tokens_est", "turns"))
                        or type(row.get("seconds")) not in (int, float) or not math.isfinite(row["seconds"]) or row["seconds"] < 0
                        or not isinstance(row.get("completed_at"), str)
                        or not isinstance(row.get("files_changed"), list)):
                    raise ValueError("Invalid run summary.")
                rows.append(row)
            except (OSError, ValueError, TypeError, AttributeError):
                skipped += 1
    rows.sort(key=lambda row: row["completed_at"], reverse=True)
    return rows, skipped


def status_command(raw_args="", **kwargs):
    """Hermes command handlers return display text, never raise."""
    if raw_args.strip() not in {"", "status"}:
        return "Usage: /patchsmith status"
    try:
        rows, skipped = summaries()
        total = sum(row["tokens_est"] for row in rows)
        lines = [f"Patchsmith: {len(rows)} recorded runs.",
                 f"{total} tokens of edit-loop work kept on this machine (estimate of local tokens).",
                 "Last five runs:"]
        for row in rows[:5]:
            files = ", ".join(str(name) for name in row["files_changed"]) or "(none)"
            lines.append(f"{row['status']} | {row['turns']} turns | {row['seconds']:.3f}s | files: {files} | patch: {row.get('patch_path') or '(none)'}")
        if not rows:
            lines.append("No recorded runs yet.")
        if skipped:
            lines.append(f"Skipped {skipped} unreadable or invalid records; totals cover readable records only.")
        return "\n".join(lines)
    except Exception as exc:
        return "Patchsmith status unavailable: " + str(exc)
