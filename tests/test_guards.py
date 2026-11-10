"""Host-boundary guards requested in catalog review."""
import json
from pathlib import Path

import pytest

from patchsmith_plugin import SCHEMA, _handle_implement_task, guards
from patchsmith_plugin.llm import local_url
from patchsmith_plugin.tools import Jail, Session


def test_child_env_is_minimal(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("PS_ENV_PASSTHROUGH", "KEEP_ME")
    monkeypatch.setenv("KEEP_ME", "1")
    env = guards.child_env()
    assert "OPENAI_API_KEY" not in env and env["KEEP_ME"] == "1"
    assert "PATH" in {k.upper() for k in env}


def test_run_tests_does_not_inherit_secrets(repo, monkeypatch):
    import sys, subprocess
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    code = "import os,sys; sys.exit(7 if 'OPENAI_API_KEY' in os.environ else 0)"
    session = Session(repo, subprocess.list2cmdline([sys.executable, "-c", code]) if sys.platform == "win32"
                      else __import__("shlex").join([sys.executable, "-c", code]))
    assert session.run_tests().startswith("exit 0")


def test_workdir_refusals(tmp_path, monkeypatch):
    home = tmp_path / "hh"
    (home / "sub").mkdir(parents=True)
    user = tmp_path / "user"
    user.mkdir()
    monkeypatch.setattr(guards, "hermes_home", lambda: home)
    monkeypatch.setenv("USERPROFILE", str(user))
    monkeypatch.setenv("HOME", str(user))
    for bad in (home, home / "sub", tmp_path, user, Path(tmp_path.anchor)):
        with pytest.raises(ValueError):
            guards.check_workdir(bad)
    ok = user / "proj"
    ok.mkdir()
    guards.check_workdir(ok)


def test_env_and_ssh_targets_refused(repo):
    s = Session(repo, "")
    for name in (".env", ".env.local", "cfg/.ENV.prod", ".ssh/id_rsa", "x/.ssh/config"):
        with pytest.raises(Jail):
            s.safe(name, write=True)
    s.safe("environment.py", write=True)


def test_endpoint_and_test_command_refused_per_call(repo):
    assert not {"endpoint", "test_command"} & set(SCHEMA["parameters"]["properties"])
    for key in ("endpoint", "test_command"):
        out = json.loads(_handle_implement_task({"task": "x", "workdir": str(repo), key: "a"}))
        assert out["reason"] == "invalid_input"


def test_link_local_endpoints_refused():
    for url in ("http://169.254.169.254/v1", "http://[fe80::1]/v1"):
        with pytest.raises(ValueError):
            local_url(url)


def test_data_root_is_per_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(guards, "hermes_home", lambda: tmp_path / "p")
    assert guards.data_root() == tmp_path / "p" / "plugin-data" / "patchsmith"
