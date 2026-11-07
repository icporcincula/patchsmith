import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from patchsmith_plugin import _handle_apply_patch, _handle_implement_task
from patchsmith_plugin import patches
from test_loop import EDIT, FINISH, STATUS, TEST, invoke, scripted, test_command


@pytest.fixture(autouse=True)
def artifact_store(tmp_path, monkeypatch):
    monkeypatch.setattr(patches, "ARTIFACT_ROOT", tmp_path / "artifacts")


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def propose(repo, *steps, **options):
    with scripted(*(steps or (EDIT, FINISH))) as (url, _):
        result = invoke(repo, url, mode="propose", **options)
    assert result["status"] == "done", result
    return result


def apply(result):
    return json.loads(_handle_apply_patch({"patch_path": result["patch_path"]}))


def test_propose_keeps_dirty_checkout_and_git_bytes_identical(repo):
    (repo / "app.py").write_bytes(b"value = 1\r\n# user change\r\n")
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
    (repo / "notes.txt").write_bytes(b"untracked notes")
    (repo / ".gitignore").write_text("ignored.txt\n")
    (repo / "ignored.txt").write_text("private local configuration")
    before = snapshot(repo)
    result = propose(repo)
    assert snapshot(repo) == before
    assert not result["applied"] and result["base_head"]
    patch = Path(result["patch_path"])
    assert patch.is_file() and not patch.is_relative_to(repo)
    assert hashlib.sha256(patch.read_bytes()).hexdigest() == result["patch_sha256"]
    assert not (patch.parent / "checkout").exists()
    assert "+value = 2" in result["diff"]
    applied = apply(result)
    assert applied["status"] == "done" and applied["applied"], applied
    assert (repo / "app.py").read_bytes() == b"value = 2\r\n# user change\r\n"
    assert (repo / "ignored.txt").read_text() == "private local configuration"
    assert (repo / "notes.txt").read_bytes() == b"untracked notes"
    assert not apply(result)["applied"]


def test_propose_runs_tests_in_isolation(repo):
    before = snapshot(repo)
    result = propose(repo, TEST, EDIT, TEST, STATUS,
                     test_command=test_command("-B", "-c", "import app; assert app.value == 2"))
    assert snapshot(repo) == before
    assert result["reason"] == "auto_finish" and not result["applied"]
    records = [json.loads(line) for line in Path(result["transcript_path"]).read_text().splitlines()]
    assert records[-1]["event"] == "proposal"
    assert records[-1]["patch_path"] == result["patch_path"]


def test_apply_refuses_moved_head(repo):
    result = propose(repo)
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=t@example.invalid",
                    "commit", "--allow-empty", "-qm", "Other commit"], cwd=repo, check=True)
    before = snapshot(repo)
    refused = apply(result)
    assert refused["reason"] == "stale_base" and not refused["applied"]
    assert snapshot(repo) == before


@pytest.mark.parametrize("change", ["bytes", "index"])
def test_apply_refuses_same_file_changes(repo, change):
    result = propose(repo)
    if change == "bytes":
        (repo / "app.py").write_bytes(b"value = 3\n")
    else:
        (repo / "app.py").write_bytes(b"value = 3\n")
        subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
        (repo / "app.py").write_bytes(b"value = 1\n")
    before = snapshot(repo)
    refused = apply(result)
    assert refused["reason"] == "files_changed" and not refused["applied"]
    assert snapshot(repo) == before


def test_apply_allows_unrelated_dirty_changes(repo):
    result = propose(repo)
    (repo / "other.py").write_bytes(b"keep this")
    assert apply(result)["applied"]
    assert (repo / "other.py").read_bytes() == b"keep this"


def test_apply_refuses_tampered_patch(repo):
    result = propose(repo)
    path = Path(result["patch_path"])
    path.write_bytes(path.read_bytes().replace(b"value = 2", b"value = 3"))
    before = snapshot(repo)
    refused = apply(result)
    assert refused["reason"] == "hash_mismatch" and not refused["applied"]
    assert snapshot(repo) == before


@pytest.mark.parametrize("target", ["test_app.py", "src/x.spec.tsx", "../escape.py", ".git/config", "node_modules/x.js"])
def test_actual_patch_paths_are_jailed_even_with_matching_hash(repo, target):
    result = propose(repo)
    path = Path(result["patch_path"])
    payload = path.read_bytes().replace(b"a/app.py", ("a/" + target).encode()).replace(b"b/app.py", ("b/" + target).encode())
    path.write_bytes(payload)
    manifest_path = path.with_name("manifest.json")
    record = json.loads(manifest_path.read_text())
    record["sha256"] = hashlib.sha256(payload).hexdigest()
    manifest_path.write_text(json.dumps(record))
    before = snapshot(repo)
    refused = apply(result)
    assert refused["status"] == "blocked" and not refused["applied"]
    assert snapshot(repo) == before
    assert not (repo.parent / "escape.py").exists()


def test_apply_refuses_unregistered_patch(repo):
    path = repo / "foreign.diff"
    path.write_text("untrusted")
    result = json.loads(_handle_apply_patch({"patch_path": str(path)}))
    assert result["reason"] == "invalid_patch" and not result["applied"]


def test_failed_propose_leaves_no_checkout_edits_or_usable_patch(repo):
    before = snapshot(repo)
    with scripted(EDIT) as (url, _):
        result = invoke(repo, url, mode="propose", max_turns=1, keep_partial=True)
    assert result["status"] == "blocked" and not result["applied"]
    assert result["patch_path"] is None and snapshot(repo) == before
    assert not list(patches.ARTIFACT_ROOT.glob("*/checkout"))


def test_non_git_propose_and_apply(tmp_path):
    repo = tmp_path / "plain"
    repo.mkdir()
    (repo / "app.py").write_bytes(b"value = 1\n")
    before = snapshot(repo)
    result = propose(repo)
    assert result["base_head"] is None and snapshot(repo) == before
    applied = apply(result)
    assert applied["applied"], applied
    assert (repo / "app.py").read_bytes() == b"value = 2\n"


def test_full_patch_saved_even_when_returned_diff_is_clipped(repo):
    content = "\n".join(f"new line {n}" for n in range(1800)) + "\n"
    result = propose(repo, ("write_file", {"path": "large.txt", "content": content}), FINISH)
    path = Path(result["patch_path"])
    assert path.stat().st_size > 12000 and len(result["diff"]) <= 12000
    applied = apply(result)
    assert applied["applied"], applied
    assert (repo / "large.txt").read_text() == content


def test_unknown_mode_never_contacts_model(repo):
    with scripted() as (url, seen):
        result = invoke(repo, url, mode="other")
    assert result["reason"] == "invalid_input" and not seen and not result["applied"]


def test_handlers_never_raise_on_bad_input():
    for handler in (_handle_apply_patch, _handle_implement_task):
        result = json.loads(handler(None))
        assert result["status"] in {"error", "blocked"} and not result["applied"]


def test_apply_preserves_original_permission_bits(repo):
    import stat
    path = repo / "app.py"
    path.chmod(0o777)
    original_mode = stat.S_IMODE(path.stat().st_mode)
    result = propose(repo)
    applied = apply(result)
    assert applied["status"] == "done" and applied["applied"], applied
    assert stat.S_IMODE(path.stat().st_mode) == original_mode


def test_storage_inside_checkout_refused_without_creating_files(repo, monkeypatch):
    storage = repo / ".patchsmith" / "proposals"
    monkeypatch.setattr(patches, "ARTIFACT_ROOT", storage)
    before = snapshot(repo)
    with scripted() as (url, seen):
        result = invoke(repo, url, mode="propose")
    assert result["status"] == "error" and not result["applied"] and not seen
    assert not storage.exists() and snapshot(repo) == before


def test_post_apply_exception_reports_error_with_applied_true(repo, monkeypatch):
    result = propose(repo)
    original = Path.chmod
    def refuse(path, mode, *args, **kwargs):
        if path == repo / "app.py":
            raise PermissionError("Permission restore denied")
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "chmod", refuse)
    applied = apply(result)
    assert applied["status"] == "error" and applied["applied"]
    assert applied["reason"] == "post_apply_error"
    assert (repo / "app.py").read_text().splitlines() == ["value = 2"]
