from patchsmith_plugin.preflight import inspect


def test_preflight_reports_missing_setup(repo, monkeypatch):
    monkeypatch.delenv("PS_TEST_COMMAND", raising=False)
    monkeypatch.setenv("PS_ENDPOINT", "http://127.0.0.1:1/v1")
    result = inspect(repo)
    assert result["status"] == "needs_setup"
    assert not result["checks"]["test_configured"]
    assert not result["checks"]["endpoint_reachable"]
