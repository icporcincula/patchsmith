"""Benchmark claims require independent tests and full GPU evidence."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location("benchmark", Path(__file__).resolve().parents[1] / "eval" / "run_eval.py")
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


@pytest.mark.parametrize("status,green,expected", [("done", False, False), ("done", True, True),
                                                   ("error", True, False), ("blocked", False, False)])
def test_done_requires_independent_green(status, green, expected):
    assert benchmark.outcome_ok({"fixture": "bug1", "status": status, "green": green}) == expected


@pytest.mark.parametrize("status,green,files,expected", [
    ("blocked", False, [], True), ("done", False, [], False),
    ("blocked", True, [], False), ("blocked", False, ["answer.py"], False)])
def test_expected_block_requires_untouched_failing_fixture(status, green, files, expected):
    row = {"fixture": "blocked", "status": status, "green": green, "files_changed": files}
    assert benchmark.outcome_ok(row) == expected


@pytest.mark.parametrize("size,vram,expected", [(100, 100, True), (100, 50, False), (0, 0, False)])
def test_partial_cpu_offload_cannot_count_as_full_gpu(monkeypatch, size, vram, expected):
    monkeypatch.setattr(benchmark, "local_api", lambda *args: {
        "models": [{"name": "model", "size": size, "size_vram": vram}]})
    assert benchmark.gpu_evidence("http://localhost:11434/v1", "model")["full_gpu"] == expected


def test_runner_checks_tests_even_if_plugin_claims_done():
    class PretendSuccess:
        @staticmethod
        def _handle_implement_task(call):
            return json.dumps({"status": "done", "turns": 1, "tokens_est": 1,
                               "files_changed": [], "diff": ""})
    args = SimpleNamespace(model="fake", endpoint="http://localhost:11434/v1", require_gpu=False, out=None)
    row = benchmark.one(PretendSuccess(), "bug1", args, 1)
    assert row["baseline_tests"]["returncode"] != 0
    assert row["independent_tests"]["returncode"] != 0
    assert not row["green"] and not row["expected_outcome"]
