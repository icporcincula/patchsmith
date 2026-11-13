"""Register the local coding tool with Hermes."""

import json
from pathlib import Path

from .hardware import inspect_hardware
from .ledger import status_command
from .jobs import start, task_status

from .loop import DEFAULT_MODE, implement
from .patches import apply_patch
from .preflight import inspect_tool
from .revision import revise_tool
from .comparison import compare_tool

SCHEMA = {
    "name": "implement_task",
    "description": (
        "Implement one precise coding task using a bounded local model and return its diff. "
        "Tests run only the owner-configured PS_TEST_COMMAND; the endpoint comes only from PS_ENDPOINT."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "Precise coding task."},
            "workdir": {"type": "string", "description": "Existing working directory."},
            "max_turns": {"type": "integer", "minimum": 1, "maximum": 60, "default": 25},
            "context_budget_tokens": {"type": "integer", "minimum": 1, "default": 24000},
            "model": {"type": "string", "description": "Local model identifier."},
            "attempts": {"type": "integer", "minimum": 1, "maximum": 3, "default": 1,
                         "description": "Fresh-context attempts sharing the total turn and token budgets."},
            "fallback_model": {"type": "string", "description": "Local model used only on the last allowed attempt, at the same endpoint."},
            "background": {"type": "boolean", "default": False,
                           "description": "Return a process-local job_id immediately; poll task_status and keep Hermes open."},
            "keep_partial": {"type": "boolean", "default": False},
            "mode": {"type": "string", "enum": ["apply", "propose"], "default": DEFAULT_MODE,
                     "description": "Propose an isolated patch for review by default. Use apply to edit the checkout directly."},
        },
        "required": ["task", "workdir"],
        "additionalProperties": False,
    },
}


def _handle_implement_task(args: dict, **kwargs) -> str:
    try:
        banned = sorted({"endpoint", "test_command"} & set(args))
        if banned:
            raise ValueError(f"{', '.join(banned)} cannot be set per call; the owner configures PS_ENDPOINT and PS_TEST_COMMAND.")
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


HARDWARE_SCHEMA = {
    "name": "inspect_hardware",
    "description": "Read CPU, RAM, GPU/VRAM and configured local model inventory; compare tested evidence and conservative weight-memory estimates. No downloads or uploads.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}

PREFLIGHT_SCHEMA = {
    "name": "task_preflight", "description": "Check checkout, configured tests and local model endpoint before a task; makes no edits.",
    "parameters": {"type": "object", "properties": {"workdir": {"type": "string"}},
                   "required": ["workdir"], "additionalProperties": False},
}

REVISION_SCHEMA = {
    "name": "revise_proposal", "description": "Create a fresh isolated proposal from a saved patch and review feedback; original checkout stays untouched.",
    "parameters": {"type": "object", "properties": {
        "patch_path": {"type": "string"}, "task": {"type": "string"}, "feedback": {"type": "string"}},
        "required": ["patch_path", "task", "feedback"], "additionalProperties": False},
}

COMPARISON_SCHEMA = {
    "name": "compare_models", "description": "Run the same task through two local models sequentially in separate isolated proposals.",
    "parameters": {"type": "object", "properties": {
        "task": {"type": "string"}, "workdir": {"type": "string"},
        "models": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2}},
        "required": ["task", "workdir", "models"], "additionalProperties": False},
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

    ctx.register_tool(name="inspect_hardware", toolset="patchsmith", schema=HARDWARE_SCHEMA, handler=inspect_hardware)
    ctx.register_tool(name="task_preflight", toolset="patchsmith", schema=PREFLIGHT_SCHEMA, handler=inspect_tool)
    ctx.register_tool(name="revise_proposal", toolset="patchsmith", schema=REVISION_SCHEMA, handler=revise_tool)
    ctx.register_tool(name="compare_models", toolset="patchsmith", schema=COMPARISON_SCHEMA, handler=compare_tool)
    ctx.register_skill("hardware", Path(__file__).parent / "skills" / "hardware" / "SKILL.md",
                       description="Inspect local hardware, distinguish tested configurations from memory estimates, and prepare reproducible contributor benchmarks.")
