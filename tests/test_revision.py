from patchsmith_plugin import loop, revision


def test_revision_starts_fresh_proposal_with_feedback(repo, monkeypatch):
    monkeypatch.setattr(revision, "load_proposal", lambda path: (path, {"workdir": str(repo)}, b"diff --git a/app.py b/app.py"))
    monkeypatch.setattr(revision, "unchanged", lambda session, record: None)
    seen = []
    monkeypatch.setattr(loop, "implement", lambda args: seen.append(args) or {"status": "done", "patch_path": "new.diff"})
    result = revision.revise({"patch_path": "old.diff", "task": "Fix app.", "feedback": "Keep the API."})
    assert result["revised_from"] == "old.diff"
    assert seen[0]["mode"] == "propose" and seen[0]["workdir"] == str(repo)
    assert "Keep the API." in seen[0]["task"] and "diff --git" in seen[0]["task"]
