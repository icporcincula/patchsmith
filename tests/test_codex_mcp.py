import asyncio
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from test_loop import EDIT, FINISH, scripted, test_command


def test_codex_stdio_proposes_verified_patch_without_editing_checkout(repo, tmp_path):
    data = tmp_path / "codex-data"

    async def call_server(endpoint):
        params = StdioServerParameters(
            command=sys.executable,
            args=["-B", str(Path(__file__).resolve().parents[1] / "codex_mcp.py")],
            env={
                **os.environ,
                "PS_ENDPOINT": endpoint,
                "PS_TEST_COMMAND": test_command("-B", "-c", "import app; assert app.value == 2"),
                "PS_DATA_DIR": str(data),
            },
        )
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                assert [tool.name for tool in (await session.list_tools()).tools] == ["implement_task", "recent_runs", "inspect_hardware", "task_preflight", "revise_proposal"]
                arguments = {"task": "Make the value 2.", "workdir": str(repo)}
                refused = await session.call_tool("implement_task", {**arguments, "mode": "apply"})
                assert refused.isError
                result = await session.call_tool("implement_task", arguments)
                assert not result.isError, result
                return result.structuredContent

    with scripted(EDIT, FINISH) as (endpoint, _):
        result = asyncio.run(asyncio.wait_for(call_server(endpoint), timeout=30))

    assert result["status"] == "done", result
    assert "exit 0" in result["attempt_history"][0]["test_output"]
    assert result["applied"] is False and "+value = 2" in result["diff"]
    assert Path(result["patch_path"]).is_relative_to(data)
    assert (repo / "app.py").read_bytes() == b"value = 1\n"
