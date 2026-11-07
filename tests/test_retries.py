"""Retry isolation, shared resource limits and factual failure results."""
import json
from pathlib import Path
import pytest
from patchsmith_plugin import loop, patches
from test_loop import scripted, invoke, EDIT, FINISH, STATUS, TEST, test_command

BLOCK = ("finish", {"status": "blocked", "note": "Need a different approach."})


def test_retry_restores_dirty_bytes_and_uses_fresh_messages(repo):
    (repo / "app.py").write_bytes(b"value = 1\n# dirty\n")
    with scripted(EDIT, BLOCK, EDIT, FINISH) as (url, seen):
        result = invoke(repo, url, attempts=3)
    assert result["status"] == "done" and result["turns"] == 4
    assert len(result["attempt_history"]) == 2
    assert len(seen[2]["messages"]) == 2
    assert "Previous attempt facts" in seen[2]["messages"][1]["content"]
    assert (repo / "app.py").read_bytes() == b"value = 2\n# dirty\n"
    assert result["handback"] is None


def test_total_turns_shared(repo):
    with scripted(BLOCK, STATUS) as (url, seen):
        result = invoke(repo, url, attempts=3, max_turns=2)
    assert len(seen) == result["turns"] == 2
    assert result["reason"] == "max_turns"
    assert len(result["attempt_history"]) == 2


def test_total_tokens_shared(repo, monkeypatch):
    seen = []
    def complete(self, messages, tools, max_tokens):
        seen.append(messages)
        return {"role": "assistant", "tool_calls": [{"id": "one", "type": "function",
                "function": {"name": "finish", "arguments": json.dumps(BLOCK[1])}}]}, {
                    "prompt_tokens": 2000, "completion_tokens": 100}
    monkeypatch.setattr(loop.LocalModel, "complete", complete)
    result = invoke(repo, "http://localhost:11434/v1", attempts=3, context_budget_tokens=2600)
    assert len(seen) == 1
    assert result["reason"] == "context_budget"
    assert result["tokens_est"] == 2100
    assert sum(r["tokens_est"] for r in result["attempt_history"]) == result["tokens_est"]


def test_failed_tests_retry_and_factual_handback(repo):
    command = test_command("-B", "-c", "print('expected value 3'); raise SystemExit(1)")
    with scripted(EDIT, FINISH, EDIT, FINISH) as (url, _):
        result = invoke(repo, url, attempts=2, test_command=command)
    assert result["reason"] == "tests_failed"
    assert (repo / "app.py").read_bytes() == b"value = 1\n"
    back = result["handback"]
    assert set(back) == {"what_was_tried", "last_failure", "files_touched", "suggested_next"}
    assert back["files_touched"] == ["app.py"]
    assert "expected value 3" in back["last_failure"]
    assert "Attempt 2" in back["what_was_tried"]
    assert "implementation file" in back["suggested_next"]


def test_fallback_only_final_attempt(repo):
    with scripted(BLOCK, BLOCK, FINISH) as (url, seen):
        result = invoke(repo, url, attempts=3, model="small", fallback_model="large")
    assert result["status"] == "done"
    assert [r["model"] for r in seen] == ["small", "small", "large"]


def test_proposal_retry_stays_isolated(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(patches, "ARTIFACT_ROOT", tmp_path / "artifacts")
    with scripted(EDIT, BLOCK, EDIT, FINISH) as (url, _):
        result = invoke(repo, url, attempts=2, mode="propose")
    assert result["status"] == "done" and result["patch_path"]
    assert not result["applied"]
    assert (repo / "app.py").read_bytes() == b"value = 1\n"


@pytest.mark.parametrize("options", [{"attempts": 0}, {"attempts": 4}, {"attempts": True}, {"fallback_model": ""}])
def test_invalid_retry_options(repo, options):
    with scripted() as (url, seen):
        result = invoke(repo, url, **options)
    assert result["reason"] == "invalid_input" and not seen
    assert result["handback"]["files_touched"] == []
    assert result["attempt_history"] == []


def test_failed_rollback_stops_retry(repo, monkeypatch):
    monkeypatch.setattr(loop.Session, "rollback", lambda self: ["app.py: changed externally"])
    with scripted(EDIT, BLOCK) as (url, seen):
        result = invoke(repo, url, attempts=3)
    assert len(seen) == 2
    assert result["reason"] == "rollback_failed"
    assert "changed externally" in result["handback"]["last_failure"]


def test_early_success_skips_fallback(repo):
    with scripted(FINISH) as (url, seen):
        result = invoke(repo, url, attempts=3, model="small", fallback_model="large")
    assert result["status"] == "done" and len(seen) == 1
    assert seen[0]["model"] == "small"


def test_keep_partial_applies_only_to_final_attempt(repo):
    final_edit = ("edit_file", {"path": "app.py", "old": "1", "new": "3"})
    with scripted(EDIT, BLOCK, final_edit, BLOCK) as (url, _):
        result = invoke(repo, url, attempts=2, keep_partial=True)
    assert result["status"] == "blocked" and result["applied"]
    assert (repo / "app.py").read_bytes() == b"value = 3\n"
    assert "Need a different approach" not in result["handback"]["last_failure"]


def test_failed_test_then_recovery(repo):
    command = test_command("-B", "-c", "import app; assert app.value == 3, 'expected value 3'")
    fix = ("edit_file", {"path": "app.py", "old": "1", "new": "3"})
    with scripted(EDIT, FINISH, fix, FINISH) as (url, _):
        result = invoke(repo, url, attempts=2, test_command=command)
    assert result["status"] == "done" and result["handback"] is None
    assert [r["status"] for r in result["attempt_history"]] == ["blocked", "done"]
    assert result["attempt_history"][0]["test_output"].startswith("exit 1")
    assert result["attempt_history"][1]["test_output"].startswith("exit 0")
