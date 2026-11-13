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
    )]


@server.call_tool()
async def call_tool(name, arguments):
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
