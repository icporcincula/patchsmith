"""Revise a reviewed proposal in a new isolated coding run."""

import json
from pathlib import Path

from .patches import load_proposal, unchanged
from .tools import Session, clip


def revise(args):
    if not isinstance(args, dict) or set(args) != {"patch_path", "task", "feedback"}:
        raise ValueError("Provide patch_path, the full task and review feedback.")
    if any(not isinstance(args[key], str) or not args[key].strip() for key in args):
        raise ValueError("Revision arguments must be nonempty strings.")
    _, record, payload = load_proposal(args["patch_path"])
    workdir = Path(record["workdir"])
    unchanged(Session(workdir, ""), record)
    from .loop import implement
    task = (args["task"] + "\n\nRevise the previous proposal using this review feedback:\n"
            + args["feedback"] + "\n\nPrevious proposed diff (context only; start from the original checkout):\n"
            + clip(payload.decode("utf-8"), 4000))
    result = implement({"task": task, "workdir": str(workdir), "mode": "propose"})
    result["revised_from"] = args["patch_path"]
    return result


def revise_tool(args, **kwargs):
    try:
        return json.dumps(revise(args))
    except Exception as exc:
        return json.dumps({"status": "error", "reason": "revision_failed", "note": str(exc), "applied": False})
