"""Hermes registrations, summary accounting and background completion."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
import json

from conftest import PLUGIN, ROOT
from patchsmith_plugin import jobs, ledger, patches
from test_loop import scripted, invoke, EDIT, FINISH


def row(tokens=10):
    return {"status": "done", "turns": 2, "tokens_est": tokens,
            "files_changed": ["app.py"], "patch_path": None, "transcript_path": "run.jsonl"}


def test_empty_and_usage():
    assert "No recorded runs" in ledger.status_command("status")
    assert "Usage:" in ledger.status_command("wrong")


def test_concurrent_records_no_lost_totals_and_last_five():
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(lambda n: ledger.record(row(n), n, "propose"), range(1, 9))) == [None] * 8
    records, skipped = ledger.summaries()
    assert len(records) == 8 and skipped == 0
    assert sum(r["tokens_est"] for r in records) == 36
    text = ledger.status_command("status")
    assert "36 tokens of edit-loop work" in text
    assert text.count("| patch:") == 5
    assert "estimate of local tokens" in text


def test_malformed_summary_is_reported():
    ledger.record(row(), 1, "apply")
    (ledger.directory() / "bad.json").write_text("{broken", encoding="utf-8")
    (ledger.directory() / "wrong.json").write_text("[]", encoding="utf-8")
    assert "Skipped 2" in ledger.status_command()
    assert "10 tokens" in ledger.status_command()


def test_ledger_failure_does_not_change_result(repo, monkeypatch):
    bad = ledger.directory()
    bad.write_text("not a directory", encoding="utf-8")
    with scripted(EDIT, FINISH) as (url, _):
        result = invoke(repo, url)
    assert result["status"] == "done" and result["applied"]
    assert "ledger_warning" in result
    assert "unavailable" in ledger.status_command()


def test_default_proposal_recorded_once_with_final_path(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(patches, "ARTIFACT_ROOT", tmp_path / "proposals")
    with scripted(EDIT, FINISH) as (url, _):
        result = invoke(repo, url, mode=None)
    rows, _ = ledger.summaries()
    assert PLUGIN.SCHEMA["parameters"]["properties"]["mode"]["default"] == "propose"
    assert result["status"] == "done" and not result["applied"] and result["patch_path"]
    assert len(rows) == 1
    assert rows[0]["mode"] == "propose"
    assert rows[0]["patch_path"] == result["patch_path"]
    assert rows[0]["tokens_est"] == result["tokens_est"]
    assert rows[0]["seconds"] == result["seconds"]
    assert (repo / "app.py").read_bytes() == b"value = 1\n"


def test_registrations_and_packaged_skill():
    class Context:
        def __init__(self): self.tools, self.commands, self.skills = {}, {}, {}
        def register_tool(self, **kw): self.tools[kw["name"]] = kw
        def register_command(self, name, handler, **kw): self.commands[name] = handler
        def register_skill(self, name, path, **kw): self.skills[name] = path
    ctx = Context()
    PLUGIN.register(ctx)
    assert set(ctx.tools) == {"implement_task", "apply_patch", "task_status", "inspect_hardware", "task_preflight"}
    assert set(ctx.commands) == {"patchsmith"}
    assert ctx.commands["patchsmith"]("status").startswith("Patchsmith:")
    assert set(ctx.skills) == {"delegate", "hardware"}
    assert ctx.skills["hardware"].is_file()
    assert ctx.skills["delegate"].is_file()
    assert ctx.skills["delegate"].is_relative_to(ROOT)


def test_background_nonblocking_busy_completion_and_repeat_poll():
    entered, release, finished = Event(), Event(), Event()
    def handler(args):
        assert "background" not in args
        entered.set()
        assert release.wait(3)
        finished.set()
        return json.dumps(row())
    result = jobs.start({"background": True}, handler)
    try:
        assert result["status"] == "running" and entered.wait(1)
        assert jobs.start({}, handler)["reason"] == "job_busy"
        assert json.loads(jobs.task_status({"job_id": result["job_id"]}))["status"] == "running"
    finally:
        release.set()
    assert finished.wait(2)
    # Joining the named worker establishes completion without polling sleeps.
    import threading
    for worker in threading.enumerate():
        if worker.name == "patchsmith-" + result["job_id"]: worker.join(2)
    poll = json.loads(jobs.task_status({"job_id": result["job_id"]}))
    assert poll["status"] == "completed" and poll["result"]["tokens_est"] == 10
    assert json.loads(jobs.task_status({"job_id": result["job_id"]})) == poll


def test_bad_job_and_handler_input():
    assert json.loads(jobs.task_status({"job_id": "../bad"}))["reason"] == "invalid_input"
    assert json.loads(jobs.task_status({"job_id": "0" * 32}))["reason"] == "unknown_job"
    assert json.loads(PLUGIN._handle_implement_task({"background": "yes"}))["reason"] == "invalid_input"


def test_background_handler_runs_loop_and_records_once(repo, tmp_path, monkeypatch):
    import threading
    monkeypatch.setattr(patches, "ARTIFACT_ROOT", tmp_path / "proposals")
    with scripted(EDIT, FINISH) as (url, _):
        monkeypatch.setenv("PS_ENDPOINT", url)
        job = json.loads(PLUGIN._handle_implement_task({
            "task": "Set app.py value to 2", "workdir": str(repo),
            "model": "scripted", "background": True,
        }))
        assert job["status"] == "running"
        for worker in threading.enumerate():
            if worker.name == "patchsmith-" + job["job_id"]: worker.join(5)
        result = json.loads(jobs.task_status({"job_id": job["job_id"]}))
    assert result["status"] == "completed"
    assert result["result"]["status"] == "done", result["result"]
    records, skipped = ledger.summaries()
    assert len(records) == 1 and skipped == 0
    assert records[0]["tokens_est"] == result["result"]["tokens_est"]
    assert not result["result"]["applied"] and result["result"]["patch_path"]
    assert records[0]["mode"] == "propose"
    assert (repo / "app.py").read_bytes() == b"value = 1\n"
