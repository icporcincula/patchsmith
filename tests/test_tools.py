from pathlib import Path

import pytest

from patchsmith_plugin.tools import Jail, Session, clip


@pytest.mark.parametrize("path", ["../outside", ".git/config", "node_modules/a", ".ship/a",
                                  ".patchsmith/a", "test_app.py", "src/x.spec.tsx",
                                  "lib/tests/helper.py", "x/__tests__/fixture.json"])
def test_refused_write(repo, path):
    with pytest.raises(Jail):
        Session(repo, "").write_file(path, "bad")


def test_absolute_outside(repo):
    with pytest.raises(Jail):
        Session(repo, "").read_file(str(repo.parent / "outside"))


def test_symlink_escape_and_test_alias(repo):
    outside = repo.parent / "outside"
    outside.write_text("outside")
    try:
        (repo / "alias").symlink_to(outside)
        (repo / "test-alias").symlink_to(repo / "test_app.py")
    except OSError as exc:
        pytest.skip(f"Symbolic links unavailable: {exc}")
    session = Session(repo, "")
    with pytest.raises(Jail):
        session.read_file("alias")
    with pytest.raises(Jail):
        session.write_file("alias", "bad")
    with pytest.raises(Jail):
        session.write_file("test-alias", "bad")
    assert outside.read_text() == "outside"


def test_clip(repo):
    value = "first" + "x" * 12000 + "last"
    assert len(clip(value)) == 6000
    assert clip(value).startswith("first") and clip(value).endswith("last")
    (repo / "long.txt").write_text(value)
    assert len(Session(repo, "").read_file("long.txt")) == 6000


def test_glob_and_grep_respect_git_visibility(repo):
    (repo / ".gitignore").write_text("ignored.txt\n")
    for name in ("visible.txt", "ignored.txt", ".patchsmith/run.jsonl"):
        file = repo / name
        file.parent.mkdir(exist_ok=True)
        file.write_text("needle")
    session = Session(repo, "")
    assert session.glob("*.txt") == "visible.txt"
    assert session.glob("**/*.txt") == "visible.txt"
    assert session.glob(session.root.as_posix() + "/**/*.txt") == "visible.txt"
    assert session.glob("./*.txt") == "visible.txt"
    assert session.grep("needle") == "visible.txt:1:needle"


def test_crlf_edit_and_exact_rollback(repo):
    path = repo / "app.py"
    original = b"# User change\r\nvalue = 1\r\n"
    path.write_bytes(original)
    session = Session(repo, "")
    session.edit_file("app.py", "value = 1\n", "value = 2\n")
    assert path.read_bytes() == b"# User change\r\nvalue = 2\r\n"
    session.write_file("new/folder/file.py", "hello")
    assert session.rollback() == []
    assert path.read_bytes() == original
    assert not (repo / "new").exists()


def test_concurrent_edit_preserved(repo):
    session = Session(repo, "")
    session.write_file("app.py", "value = 2\n")
    (repo / "app.py").write_text("external")
    assert session.rollback()
    assert (repo / "app.py").read_text() == "external"
