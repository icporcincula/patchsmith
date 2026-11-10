"""Inventory uncertainty, endpoint isolation and contributor evidence consistency."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from conftest import ROOT
from patchsmith_plugin import hardware

sys.path.insert(0, str(ROOT / "eval"))
spec = importlib.util.spec_from_file_location("community_benchmark", ROOT / "eval/benchmark.py")
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


def host():
    return {"os": "test", "cpu": {"name": "test"}, "ram_bytes": 32 * hardware.GIB,
            "gpus": [{"name": "NVIDIA GeForce RTX 5060 Ti", "total_bytes": 16 * hardware.GIB,
                       "free_bytes": 12 * hardware.GIB}], "warnings": []}


def backend():
    return {"kind": "Ollama", "version": "test", "host_is_loopback": True,
            "models": [{"name": "qwen3.5:9b", "size_bytes": 6 * hardware.GIB, "quantization": "test"}]}


def test_estimates_are_not_runtime_guarantees_or_pooled_cards():
    h = host()
    m = backend()["models"][0]
    assert hardware.estimate(m, h)["classification"] == "weights_plus_margin_in_free_vram"
    h["gpus"][0]["free_bytes"] = 0
    assert hardware.estimate(m, h)["classification"] == "weights_plus_margin_in_total_vram_only"
    h["gpus"] = [{"total_bytes": 4 * hardware.GIB, "free_bytes": 4 * hardware.GIB}] * 3
    assert hardware.estimate(m, h)["classification"] == "system_ram_capacity_only"
    h["ram_bytes"] = None
    assert hardware.estimate(m, h)["classification"] == "insufficient_known_capacity"
    assert hardware.estimate({"name": "unknown"}, h)["classification"] == "unknown"


def test_hardware_handler_rejects_cloud_before_any_probe(monkeypatch):
    def forbidden(): raise AssertionError("must not probe")
    monkeypatch.setattr(hardware, "host_inventory", forbidden)
    for args in ({"endpoint": "https://example.com/v1"}, {"endpoint": 3}, {"endpoint": ""}, {"download": True}, None):
        assert json.loads(hardware.inspect_hardware(args))["status"] == "error"


def test_backend_ollama_and_private_host_warning(monkeypatch):
    responses = {"/v1/models": {"data": [{"id": "model"}]}, "/api/version": {"version": "1"},
                 "/api/tags": {"models": [{"name": "model", "size": 42, "details": {"quantization_level": "Q4"}}]},
                 "/api/ps": {"models": [{"name": "model", "size": 42, "size_vram": 42}]}}
    calls = []
    def api(endpoint, route):
        calls.append(route)
        return responses[route]
    monkeypatch.setattr(hardware, "api", api)
    b = hardware.backend_inventory("http://172.20.0.1:11434/v1")
    assert b["kind"] == "Ollama" and b["version"] == "1"
    assert b["models"][0]["quantization"] == "Q4"
    assert b["loaded_models"][0]["vram_bytes"] == 42
    assert b["warnings"] and not b["host_is_loopback"]
    assert set(calls) == set(responses)  # No generate, pull, show or external discovery.


def test_generic_and_unavailable_backend_stay_unknown(monkeypatch):
    def api(endpoint, route):
        if route == "/v1/models": return {"data": [{"id": "served"}]}
        raise ValueError("not Ollama")
    monkeypatch.setattr(hardware, "api", api)
    b = hardware.backend_inventory("http://localhost:9999/v1")
    assert b["models"][0]["size_bytes"] is None and b["version"] is None
    assert b["kind"].startswith("OpenAI-compatible")
    def unavailable(*args): raise OSError("offline")
    monkeypatch.setattr(hardware, "api", unavailable)
    assert not hardware.backend_inventory("http://localhost:9999/v1")["reachable"]


def test_windows_inventory_ignores_inaccurate_display_vram(monkeypatch):
    monkeypatch.setattr(hardware.platform, "system", lambda: "Windows")
    monkeypatch.setattr(hardware.shutil, "which", lambda _: "nvidia-smi")
    def command(argv):
        if argv[0] == "powershell.exe":
            return json.dumps({"cpu": "CPU", "ram": 12345, "gpus": ["NVIDIA GeForce RTX 5060 Ti", "Integrated"]})
        return "NVIDIA GeForce RTX 5060 Ti, 16311, 0, 1.0"
    monkeypatch.setattr(hardware, "command", command)
    h = hardware.host_inventory()
    assert h["cpu"]["name"] == "CPU" and h["ram_bytes"] == 12345
    assert len(h["gpus"]) == 2
    gpu = next(g for g in h["gpus"] if g["source"] == "nvidia-smi")
    assert gpu["total_bytes"] == 16311 * 1024 ** 2 and gpu["free_bytes"] == 0
    assert next(g for g in h["gpus"] if g["name"] == "Integrated")["total_bytes"] is None


def test_unified_memory_is_not_dedicated_vram(monkeypatch):
    monkeypatch.setattr(hardware.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(hardware.shutil, "which", lambda _: None)
    monkeypatch.setattr(hardware.Path, "is_file", lambda _: False)
    monkeypatch.setattr(hardware, "command", lambda args: "32000000000" if "hw.memsize" in args else "Apple CPU")
    h = hardware.host_inventory()
    assert h["ram_bytes"] == 32000000000 and not h["gpus"]
    assert "Unified" in h["warnings"][0]


def test_shared_fields_never_claim_reproduction(monkeypatch):
    monkeypatch.setattr(hardware, "host_inventory", host)
    monkeypatch.setattr(hardware, "backend_inventory", lambda _: backend())
    result = json.loads(hardware.inspect_hardware({}))
    assert result["status"] == "done"
    record = result["tested_configurations"][0]
    assert len(record["matching_fields"]) == 3 and "not a reproduced" in record["comparison"]
    assert record["backend_version"] is None and record["quantization"] is None


def report():
    raw = {"metadata": {"model": "qwen3.5:9b", "attempts": 1, "require_gpu": True,
        "endpoint": "PRIVATE", "command": "PRIVATE", "budgets": {"max_turns": "25", "context_budget_tokens": "24000"}},
        "rows": [{"fixture": "bug1", "run": 1, "status": "done", "turns": 3, "tokens_est": 100,
            "secs": 2.5, "files_changed": ["app.py"], "baseline_tests": {"returncode": 1},
            "independent_tests": {"returncode": 0, "output": "PRIVATE"}, "green": True,
            "gpu": {"full_gpu": True}, "diff": "PRIVATE"}]}
    return bench.build_report(raw, {"hardware": host(), "backend": backend()}, {"bug1": 1}, 0)


def test_summary_excludes_private_fields_and_preserves_failures():
    r = report()
    assert "PRIVATE" not in json.dumps(r)
    assert r["complete"] and r["rows"][0]["implementation_success"]
    r["rows"][0].update(status="blocked", independent_exit=1, implementation_success=False, expected_outcome=False)
    assert bench.validate_report(r)["complete"]
    r["runner_exit"] = 1
    r["complete"] = False
    assert not bench.validate_report(r)["complete"]


@pytest.mark.parametrize("change", [
    lambda r: r["rows"][0].update(independent_exit=1),
    lambda r: r["rows"].append(copy.deepcopy(r["rows"][0])),
    lambda r: r["rows"][0].update(full_gpu=False),
    lambda r: r["rows"][0].update(seconds=float("nan")),
    lambda r: r["suite"]["requested_runs"].update(bug1=2),
    lambda r: r["rows"][0].update(baseline_exit=0),
    lambda r: r.update(schema_version=2),
])
def test_validator_rejects_inconsistent_claims(change):
    r = report()
    change(r)
    with pytest.raises(ValueError): bench.validate_report(r)


def test_blocked_guardrail_requires_no_edits():
    r = report()
    r["suite"]["requested_runs"] = {"blocked": 1}
    r["rows"][0].update(fixture="blocked", status="blocked", independent_exit=1,
                        implementation_success=False, expected_outcome=True, files_changed_count=0)
    assert bench.validate_report(r)
    r["rows"][0]["files_changed_count"] = 1
    with pytest.raises(ValueError): bench.validate_report(r)


def test_endpoint_comes_only_from_configuration(monkeypatch):
    monkeypatch.setenv("PS_ENDPOINT", "http://172.20.0.1:11434/v1")
    monkeypatch.setattr(hardware, "host_inventory", host)
    seen = []
    def configured(endpoint):
        seen.append(endpoint)
        return backend()
    monkeypatch.setattr(hardware, "backend_inventory", configured)
    assert json.loads(hardware.inspect_hardware({}))["status"] == "done"
    assert seen == ["http://172.20.0.1:11434/v1"]
