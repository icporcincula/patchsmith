"""Read-only readiness checks before starting a coding task."""

import json
import os
from pathlib import Path
import shlex
import shutil
import socket
from urllib.parse import urlsplit

from .guards import check_workdir
from .llm import local_url
from .profiles import load as load_profile


def inspect(workdir):
    root = Path(workdir).resolve(strict=True)
    check_workdir(root)
    if not root.is_dir():
        raise ValueError("workdir must be a project directory.")
    profile = load_profile(root)
    command = os.environ.get("PS_TEST_COMMAND", profile.get("test_command", ""))
    endpoint = os.environ.get("PS_ENDPOINT") or "http://127.0.0.1:11434/v1"
    local_url(endpoint)
    parsed = urlsplit(endpoint)
    checks = {"checkout": True, "test_configured": bool(command.strip()), "test_executable_found": False,
              "endpoint_reachable": False}
    if command.strip():
        argv = shlex.split(command, posix=os.name != "nt")
        executable = argv[0].strip('"') if argv else ""
        checks["test_executable_found"] = bool(shutil.which(executable))
    try:
        with socket.create_connection((parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)), timeout=2):
            checks["endpoint_reachable"] = True
    except OSError:
        pass
    return {"status": "ready" if all(checks.values()) else "needs_setup", "workdir": str(root),
            "model": os.environ.get("PS_MODEL", profile.get("model", "qwen3.5:9b")),
            "checks": checks, "test_command": command or None}


def inspect_tool(args, **kwargs):
    try:
        if not isinstance(args, dict) or set(args) != {"workdir"}:
            raise ValueError("Provide only workdir.")
        return json.dumps(inspect(args["workdir"]))
    except Exception as exc:
        return json.dumps({"status": "error", "reason": "invalid_input", "note": str(exc)})
