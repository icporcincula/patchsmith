"""Register the local coding tool with Hermes."""

import json
from pathlib import Path

from .ledger import status_command
from .jobs import start, task_status

from .loop import implement
from .patches import apply_patch

SCHEMA = {
    "name": "implement_task",
    "description": (
        "Implement one precise coding task using a bounded local model and return its diff. "
        "Pass only a test command the user has authorized to execute in this checkout."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "Precise coding task."},
            "workdir": {"type": "string", "description": "Existing working directory."},
            "max_turns": {"type": "integer", "minimum": 1, "maximum": 60, "default": 25},
            "test_command": {"type": "string", "description": "User-authorized command line."},
            "context_budget_tokens": {"type": "integer", "minimum": 1, "default": 24000},
            "model": {"type": "string", "description": "Local model identifier."},
            "endpoint": {"type": "string", "description": "Local HTTP API base ending in /v1."},
            "attempts": {"type": "integer", "minimum": 1, "maximum": 3, "default": 1,
                         "description": "Fresh-context attempts sharing the total turn and token budgets."},
            "fallback_model": {"type": "string", "description": "Local model used only on the last allowed attempt, at the same endpoint."},
            "background": {"type": "boolean", "default": False,
                           "description": "Return a process-local job_id immediately; poll task_status and keep Hermes open."},
            "keep_partial": {"type": "boolean", "default": False},
            "mode": {"type": "string", "enum": ["apply", "propose"], "default": "apply",
                     "description": "Use propose to return an isolated patch for review without editing the checkout."},
        },
        "required": ["task", "workdir"],
        "additionalProperties": False,
    },
}


def _handle_implement_task(args: dict, **kwargs) -> str:
    try:
        background = args.get("background", False)
        if type(background) is not bool:
            raise ValueError("background must be a boolean.")
        if background:
            return json.dumps(start(args, _handle_implement_task))
        return json.dumps(implement(args))
    except Exception as exc:
        return json.dumps({
            "status": "error", "reason": "invalid_input", "note": str(exc),
            "turns": 0, "tokens_est": 0, "files_changed": [], "diff": "",
            "transcript_path": None, "patch_path": None, "patch_sha256": None,
            "base_head": None, "applied": False, "attempt_history": [],
            "handback": {"what_was_tried": "No coding attempt started.",
                         "last_failure": str(exc)[:2000], "files_touched": [],
                         "suggested_next": "Correct the input arguments and retry the bounded task."},
        })


APPLY_SCHEMA = {
    "name": "apply_patch",
    "description": "Apply a saved Patchsmith proposal only after the user approves its returned diff. Refuses stale or tampered patches.",
    "parameters": {"type": "object", "properties": {
        "patch_path": {"type": "string", "description": "Exact patch_path returned by implement_task in propose mode."}},
        "required": ["patch_path"], "additionalProperties": False},
}


def _handle_apply_patch(args: dict, **kwargs) -> str:
    try:
        return json.dumps(apply_patch(args))
    except Exception as exc:
        return json.dumps({"status": "error", "reason": "invalid_input", "note": str(exc),
                           "patch_path": None, "base_head": None, "applied": False, "files_changed": []})


STATUS_SCHEMA = {
    "name": "task_status", "description": "Poll a Patchsmith background job in the same Hermes process; completed jobs include the full result.",
    "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}},
                   "required": ["job_id"], "additionalProperties": False},
}


def register(ctx) -> None:
    ctx.register_tool(
        name="implement_task", toolset="patchsmith", schema=SCHEMA,
        handler=_handle_implement_task,
    )

    ctx.register_tool(
        name="apply_patch", toolset="patchsmith", schema=APPLY_SCHEMA, handler=_handle_apply_patch,
    )

    ctx.register_tool(name="task_status", toolset="patchsmith", schema=STATUS_SCHEMA, handler=task_status)
    ctx.register_command("patchsmith", status_command,
                         description="Show recent Patchsmith runs and estimated local tokens.", args_hint="status")
    ctx.register_skill("delegate", Path(__file__).parent / "skills" / "delegate" / "SKILL.md",
                       description="Delegate a bounded, test-verified coding change to the configured local Patchsmith model.")
