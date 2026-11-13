"""Local stdio entry point for the Codex plugin."""

import asyncio
import importlib.util
import os
from pathlib import Path
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

server = Server(
    "patchsmith",
    instructions=(
        "Use implement_task for one bounded coding task in the user's selected checkout. "
        "Show the proposed diff for review and get explicit approval before applying it separately. "
        "If the diff is clipped, read the saved patch before presenting or applying it."
    ),
)


@server.list_tools()
async def list_tools():
    return [Tool(
        name="implement_task",
        description=(
            "Run a local model on one coding task in an isolated checkout. "
            "Returns a proposed diff, verification status and saved patch path for review."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task": {"type": "string", "minLength": 1},
                "workdir": {"type": "string", "description": "Absolute path to the project checkout."},
            },
            "required": ["task", "workdir"],
            "additionalProperties": False,
        },
    ), Tool(
        name="recent_runs",
        description="Read the last five local Patchsmith run summaries and estimated token total.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ), Tool(
        name="inspect_hardware",
        description="Inspect local hardware and configured model inventory without downloading anything.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ), Tool(
        name="task_preflight",
        description="Check project, test command and local endpoint readiness without editing files.",
        inputSchema={"type": "object", "properties": {"workdir": {"type": "string"}},
                     "required": ["workdir"], "additionalProperties": False},
    ), Tool(
        name="revise_proposal",
        description="Create a new isolated proposal from a saved patch, full task and review feedback.",
        inputSchema={"type": "object", "properties": {
            "patch_path": {"type": "string"}, "task": {"type": "string"}, "feedback": {"type": "string"}},
            "required": ["patch_path", "task", "feedback"], "additionalProperties": False},
    )]


@server.call_tool()
async def call_tool(name, arguments):
    if name == "task_preflight":
        from patchsmith_codex.preflight import inspect
        return await asyncio.to_thread(inspect, arguments["workdir"])
    if name == "revise_proposal":
        from patchsmith_codex.revision import revise
        return await asyncio.to_thread(revise, arguments)
    if name == "recent_runs":
        from patchsmith_codex.ledger import summaries
        rows, skipped = await asyncio.to_thread(summaries)
        return {"runs": rows[:5], "total_tokens_est": sum(row["tokens_est"] for row in rows), "skipped": skipped}
    if name == "inspect_hardware":
        import json
        from patchsmith_codex.hardware import inspect_hardware
        return json.loads(await asyncio.to_thread(inspect_hardware, {}))
    if name != "implement_task":
        raise ValueError(f"Unknown Patchsmith tool: {name}")
    if not Path(arguments["workdir"]).is_absolute():
        raise ValueError("workdir must be an absolute path to the project checkout.")
    from patchsmith_codex.loop import implement

    return await asyncio.to_thread(implement, {
        "task": arguments["task"],
        "workdir": arguments["workdir"],
        "mode": "propose",
    })


async def main():
    # A Codex cache may name the package directory 'local' or use a version number.
    root = Path(__file__).resolve().parent
    os.environ.setdefault("PS_DATA_DIR", str(Path.home() / ".patchsmith"))
    spec = importlib.util.spec_from_file_location(
        "patchsmith_codex", root / "__init__.py", submodule_search_locations=[str(root)],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
