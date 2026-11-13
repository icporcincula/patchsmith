from patchsmith_plugin import loop
from patchsmith_plugin.tools import Session
from test_loop import test_command


class Client:
    model = "scripted"


def test_verification_distinguishes_unconfigured_and_passed(repo, tmp_path, monkeypatch):
    def finish(session, client, task, turns, budget, log, result):
        session.write_file("app.py", "value = 2\n")
        return "done", None, "Edited."

    monkeypatch.setattr(loop, "run_loop", finish)
    unverified = loop.execute(Session(repo, ""), Client(), "Edit", 2, 1000, False, log_dir=tmp_path)
    assert unverified["verification"]["outcome"] == "not_configured"
    assert unverified["status"] == "done"
    (repo / "app.py").write_text("value = 1\n")
    command = test_command("-B", "-c", "import app; assert app.value == 2")
    verified = loop.execute(Session(repo, command), Client(), "Edit", 2, 1000, False, log_dir=tmp_path)
    assert verified["verification"]["outcome"] == "passed"
    assert verified["verification"]["test_output"].startswith("exit 0")
