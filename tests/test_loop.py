from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import shlex
import socket
import subprocess
import sys
from threading import Thread

import pytest

from li_plugin import _handle_implement_task

FINISH = ("finish", {"status": "done", "note": "Implemented."})
STATUS = ("git_status", {})
EDIT = ("edit_file", {"path": "app.py", "old": "1", "new": "2"})
TEST = ("run_tests", {})


@contextmanager
def scripted(*steps):
    plan = iter(steps)
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            assert self.path == "/v1/chat/completions"
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(request)
            step = next(plan)
            if step is None:
                self.connection.shutdown(socket.SHUT_RDWR)
                return
            name, args = step
            payload = {"choices": [{"message": {"role": "assistant", "tool_calls": [{
                "id": f"call-{len(seen)}", "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }]}}]}
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/v1", seen
        finally:
            server.shutdown()
            worker.join()


def invoke(root, endpoint, **options):
    return json.loads(_handle_implement_task({
        "task": "Make the value 2.", "workdir": str(root), "endpoint": endpoint, **options,
    }))


def test_command(*args):
    words = [sys.executable, *args]
    return subprocess.list2cmdline(words) if sys.platform == "win32" else shlex.join(words)


test_command.__test__ = False


def test_finish_and_transcript(repo):
    refuse = ("write_file", {"path": "test_app.py", "content": "bad"})
    with scripted(refuse, EDIT, FINISH) as (url, requests):
        result = invoke(repo, url)
    assert result["status"] == "done"
    assert result["turns"] == 3 and result["tokens_est"] > 0
    assert result["files_changed"] == ["app.py"]
    assert "+value = 2" in result["diff"]
    assert requests[1]["messages"][-1]["content"].startswith("REFUSED:")
    log = Path(result["transcript_path"])
    assert log.parent == repo / ".local-implementer"
    records = [json.loads(line) for line in log.read_text().splitlines()]
    assert records[-1]["status"] == "done"


@pytest.mark.parametrize("keep", [False, True])
def test_turn_cap_rollback(repo, keep):
    (repo / "app.py").write_bytes(b"value = 1\n# Existing dirty edit\n")
    with scripted(EDIT) as (url, _):
        result = invoke(repo, url, max_turns=1, keep_partial=keep)
    assert (result["status"], result["reason"]) == ("blocked", "max_turns")
    assert (repo / "app.py").read_bytes() == (b"value = 2\n" if keep else b"value = 1\n") + b"# Existing dirty edit\n"
    assert result["files_changed"] == (["app.py"] if keep else [])


def test_context_cap(repo):
    with scripted() as (url, requests):
        result = invoke(repo, url, context_budget_tokens=10)
    assert result["reason"] == "context_budget" and not requests


def test_repeat_guard(repo):
    with scripted(STATUS, STATUS, STATUS) as (url, _):
        result = invoke(repo, url)
    assert result["reason"] == "loop_detected" and result["turns"] == 3


def test_auto_finish(repo):
    command = test_command("-c", "import app; assert app.value == 2")
    with scripted(TEST, EDIT, TEST, STATUS) as (url, _):
        result = invoke(repo, url, test_command=command)
    assert (result["status"], result["reason"]) == ("done", "auto_finish")
    assert "+value = 2" in result["diff"]


def test_endpoint_unreachable(repo):
    with socket.socket() as stopped:
        stopped.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{stopped.getsockname()[1]}/v1"
        result = invoke(repo, url)
    assert result["status"] == "error" and url in result["note"]


def test_connection_dropped_mid_run(repo):
    with scripted(EDIT, None) as (url, _):
        result = invoke(repo, url)
    assert result["status"] == "error" and url in result["note"]
    assert (repo / "app.py").read_bytes() == b"value = 1\n"


def test_bad_directory_and_nonlocal_endpoint(repo):
    assert invoke(repo / "missing", "http://localhost:11434/v1")["reason"] == "invalid_input"
    result = invoke(repo, "https://8.8.8.8/v1")
    assert result["status"] == "error" and "private network" in result["note"]


def test_restores_tampered_tests(repo):
    command = test_command(
        "-c", "from pathlib import Path; Path('test_app.py').write_text('changed'); "
        "Path('test_new.py').write_text('new')",
    )
    with scripted(EDIT, TEST, FINISH) as (url, _):
        result = invoke(repo, url, test_command=command)
    assert result["reason"] == "test_files_modified"
    assert (repo / "test_app.py").read_bytes() == b"assert True\n"
    assert not (repo / "test_new.py").exists()
    assert (repo / "app.py").read_bytes() == b"value = 1\n"


def test_branch_change_blocks(repo):
    command = "git switch -c test-branch"
    with scripted(EDIT, TEST, FINISH) as (url, _):
        result = invoke(repo, url, test_command=command)
    assert result["reason"] == "git_state_changed"
    assert (repo / "app.py").read_bytes() == b"value = 1\n"
