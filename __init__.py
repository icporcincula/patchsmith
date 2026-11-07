"""Register the local coding tool with Hermes."""

import json

from .loop import implement

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
            "keep_partial": {"type": "boolean", "default": False},
        },
        "required": ["task", "workdir"],
        "additionalProperties": False,
    },
}


def _handle_implement_task(args: dict, **kwargs) -> str:
    try:
        return json.dumps(implement(args))
    except Exception as exc:
        return json.dumps({
            "status": "error", "reason": "invalid_input", "note": str(exc),
            "turns": 0, "tokens_est": 0, "files_changed": [], "diff": "",
            "transcript_path": None,
        })


def register(ctx) -> None:
    ctx.register_tool(
        name="implement_task", toolset="patchsmith", schema=SCHEMA,
        handler=_handle_implement_task,
    )
