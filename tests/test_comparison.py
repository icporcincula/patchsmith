from patchsmith_plugin import comparison, loop


def test_two_models_get_separate_proposal_runs(repo, monkeypatch):
    calls = []
    monkeypatch.setattr(loop, "implement", lambda args: calls.append(args) or {"status": "done", "patch_path": args["model"] + ".diff"})
    result = comparison.compare({"task": "Fix app", "workdir": str(repo), "models": ["small", "large"]})
    assert [item["model"] for item in result["comparisons"]] == ["small", "large"]
    assert [item["result"]["patch_path"] for item in result["comparisons"]] == ["small.diff", "large.diff"]
    assert all(call["mode"] == "propose" for call in calls)
