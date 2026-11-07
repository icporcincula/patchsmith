import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "patchsmith_plugin", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)],
)
PLUGIN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PLUGIN
SPEC.loader.exec_module(PLUGIN)
# pytest imports the package entry as __init__ for a hyphenated checkout.
sys.modules.setdefault('__init__', PLUGIN)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()

    def git(*args):
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "tests@example.invalid")
    git("config", "user.name", "Plugin Tests")
    (root / "app.py").write_bytes(b"value = 1\n")
    (root / "test_app.py").write_bytes(b"assert True\n")
    git("add", ".")
    git("commit", "-qm", "Seed")
    return root


collect_ignore = ["fixtures"]


@pytest.fixture(autouse=True)
def private_ledger(tmp_path, monkeypatch):
    from patchsmith_plugin import ledger
    monkeypatch.setattr(ledger, "directory", lambda: tmp_path / "local-runs")
