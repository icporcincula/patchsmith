import json

from patchsmith_plugin.profiles import load, main, profile_path


def test_project_profile_is_private_and_checkout_specific(repo, tmp_path, monkeypatch):
    monkeypatch.setenv("PS_DATA_DIR", str(tmp_path / "private"))
    monkeypatch.setattr("sys.argv", ["profile_cli.py", str(repo), "--test-command", "python -m pytest", "--model", "local-model"])
    main()
    assert load(repo) == {"test_command": "python -m pytest", "model": "local-model"}
    assert load(tmp_path / "other") == {}
    assert not (repo / ".patchsmith.json").exists()
    assert json.loads(profile_path().read_text())[str(repo)]["model"] == "local-model"
