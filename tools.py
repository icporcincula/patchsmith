"""Fixed tools, file protection and rollback."""

from __future__ import annotations

import difflib
import fnmatch
import hashlib
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import tempfile
from dataclasses import dataclass

from .guards import child_env, protected_target

OUT_LIMIT = 6000
TRANSCRIPTS = ".patchsmith"
HIDDEN = {".git", "node_modules", ".ship", TRANSCRIPTS}
TEST_FILE_RE = re.compile(
    r"(?:test_.+|.+_test|conftest)\.py|.+_test\.go|.*\.(?:test|spec)\.[cm]?[jt]sx?",
    re.I,
)
TEST_DIRS = {"test", "tests", "__tests__"}


class Jail(ValueError):
    pass


def clip(text: str, limit: int = OUT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    marker = "\n... output clipped ...\n"
    head = (limit - len(marker)) // 2
    tail = limit - len(marker) - head
    return text[:head] + marker + text[-tail:]


@dataclass(frozen=True)
class FileState:
    data: bytes | str
    mode: int

    def fingerprint(self):
        data = os.fsencode(self.data) if isinstance(self.data, str) else self.data
        return hashlib.sha1(data).digest(), self.mode


def capture(path: Path) -> FileState | None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(mode):
        return FileState(os.readlink(path), mode)
    if not stat.S_ISREG(mode):
        raise Jail(f"Expected a regular file: {path.name}")
    return FileState(path.read_bytes(), mode)


def replace_file(path: Path, state: FileState | None) -> None:
    if state is None:
        path.unlink(missing_ok=True)
    elif isinstance(state.data, str):
        path.unlink(missing_ok=True)
        path.symlink_to(state.data)
    else:
        fd, name = tempfile.mkstemp(prefix=".ps-", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(state.data)
            temporary.chmod(stat.S_IMODE(state.mode))
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def hidden(path: Path) -> bool:
    return any(part.casefold() in HIDDEN for part in path.parts)


def test_path(path: Path) -> bool:
    return any(part.casefold() in TEST_DIRS for part in path.parts) or bool(
        TEST_FILE_RE.fullmatch(path.name)
    )


def linked(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


class Session:
    def __init__(self, root: Path, command: str):
        self.root = root
        self.argv = shlex.split(command, posix=os.name != "nt")
        if os.name == "nt" and self.argv:
            executable = self.argv[0].strip('"')
            suffix = Path(executable).suffix.lower()
            if suffix not in {"", ".exe", ".com"}:
                raise ValueError("Use a native executable for the test command on Windows.")
            self.argv = command
        self.is_git = (root / ".git").exists()
        self.original: dict[str, FileState | None] = {}
        self.written: dict[str, FileState] = {}
        self.created_dirs: list[Path] = []
        self.green = False
        self.finished: tuple[str, str] | None = None

    def path(self, name: str) -> Path:
        supplied = Path(name)
        if supplied.drive and not supplied.is_absolute():
            raise Jail(f"Path outside workdir: {name}")
        raw = self.root / supplied
        try:
            relative = raw.relative_to(self.root)
        except ValueError:
            raise Jail(f"Path outside workdir: {name}") from None
        if ".." in relative.parts or hidden(relative):
            raise Jail(f"Protected path: {name}")
        if os.name == "nt" and any(":" in p or p.endswith((".", " "))
                                   for p in relative.parts):
            raise Jail(f"Unsupported Windows path: {name}")
        return raw

    def safe(self, name: str, *, write: bool = False) -> Path:
        raw = self.path(name)
        try:
            resolved = raw.resolve()
            relative = resolved.relative_to(self.root)
        except (ValueError, OSError, RuntimeError):
            raise Jail(f"Path outside workdir: {name}") from None
        if hidden(relative):
            raise Jail(f"Protected path: {name}")
        if write:
            if resolved == self.root:
                raise Jail("Expected a file path.")
            raw_relative = raw.relative_to(self.root)
            if protected_target(raw_relative) or protected_target(relative):
                raise Jail(f"Protected write target (.env* and .ssh/ are never written): {name}")
            if test_path(raw_relative) or test_path(relative):
                raise Jail(f"Test files are read-only: {name}")
            self.check_parents(raw)
            if linked(raw):
                raise Jail(f"Writing through a link is refused: {name}")
        return resolved

    def check_parents(self, path: Path) -> None:
        for parent in path.parents:
            if parent == self.root:
                return
            if linked(parent):
                raise Jail(f"Writing through a linked directory is refused: {parent.name}")

    def git(self, *args: str, optional: bool = False, input_data: bytes | None = None) -> str:
        env = child_env()
        env.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0",
                   GIT_ALLOW_PROTOCOL="")
        result = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
             "-c", "core.autocrlf=false",
             "--literal-pathspecs", *args], cwd=self.root, env=env, capture_output=True, input=input_data,
            stdin=subprocess.DEVNULL if input_data is None else None,
            timeout=30, check=False,
        )
        if result.returncode and not optional:
            raise RuntimeError(result.stderr.decode("utf-8", "replace").strip() or "Git command failed.")
        return os.fsdecode(result.stdout)

    def head(self):
        if not (self.root / ".git").exists():
            return False, "", ""
        return (True, self.git("rev-parse", "--verify", "HEAD", optional=True),
                self.git("symbolic-ref", "-q", "HEAD", optional=True))

    def walk_files(self):
        for directory, dirs, files in os.walk(self.root):
            base = Path(directory)
            dirs[:] = [name for name in dirs if not hidden(Path(name)) and not linked(base / name)]
            for name in files:
                relative = (base / name).relative_to(self.root)
                if not hidden(relative):
                    yield relative.as_posix()

    def visible_files(self):
        if self.is_git:
            names = self.git("ls-files", "-z", "-c", "-o", "--exclude-standard").split("\0")
            return sorted({name for name in names if name and not hidden(Path(name))})
        return sorted(self.walk_files())

    def test_snapshot(self):
        snapshot = {}
        for name in self.walk_files():
            if test_path(Path(name)):
                state = capture(self.root / name)
                if state is not None:
                    snapshot[name] = state
        return snapshot

    def restore_tests(self, before):
        after = self.test_snapshot()
        changed = [name for name in sorted(before.keys() | after.keys())
                   if name not in before or name not in after
                   or before[name].fingerprint() != after[name].fingerprint()]
        failures = []
        for name in changed:
            try:
                path = self.path(name)
                self.check_parents(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                replace_file(path, before.get(name))
            except (OSError, Jail) as exc:
                failures.append(f"{name}: {exc}")
        return changed, failures

    def read_file(self, path: str, start: int = 1, end: int | None = None) -> str:
        if start < 1 or (end is not None and end < start):
            raise ValueError("Use one-based line numbers with end at or after start.")
        file = self.safe(path)
        if not file.is_file():
            raise Jail(f"Expected a regular file: {path}")
        stop = min(end if end is not None else start + 399, start + 399)
        lines = []
        with file.open(encoding="utf-8", errors="replace") as stream:
            for number, line in enumerate(stream, 1):
                if number > stop:
                    break
                if number >= start:
                    lines.append(f"{number}\t{line.rstrip(chr(10))}")
                    if sum(map(len, lines)) >= 2 * OUT_LIMIT:
                        break
        return clip(f"[{path}]\n" + "\n".join(lines))

    def grep(self, pattern: str, path: str = ".") -> str:
        base = self.safe(path).relative_to(self.root)
        expression = re.compile(pattern)
        matches = []
        for name in self.visible_files():
            if not Path(name).is_relative_to(base):
                continue
            try:
                file = self.safe(name)
                if not file.is_file() or file.stat().st_size > 2 * 1024 * 1024:
                    continue
                data = file.read_bytes()
            except (Jail, OSError):
                continue
            if b"\0" in data:
                continue
            for number, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
                if expression.search(line):
                    matches.append(f"{name}:{number}:{line}")
                    if sum(map(len, matches)) >= OUT_LIMIT:
                        return clip("\n".join(matches))
        return "\n".join(matches) or "(no matches)"

    def glob(self, pattern: str) -> str:
        pattern = pattern.strip().replace("\\", "/")
        prefix = self.root.as_posix().rstrip("/") + "/"
        if pattern.startswith(prefix):
            pattern = pattern[len(prefix):]  # models often pass absolute patterns inside the workdir
        while pattern.startswith("./"):
            pattern = pattern[2:]
        variants = {pattern, pattern.replace("**/", "")}  # "**/" also matches zero directories
        hits = [name for name in self.visible_files() if any(fnmatch.fnmatchcase(name, p) for p in variants)]
        return clip("\n".join(hits[:200]) or "(no files)")

    def git_status(self) -> str:
        if not self.is_git:
            return "(no Git repository at workdir)"
        return clip(self.git("status", "--short", "--ignore-submodules=all") or "(clean)")

    def git_diff(self, path: str = "") -> str:
        name = self.safe(path or ".").relative_to(self.root).as_posix()
        if not self.is_git:
            return self.patch(name)[1] or "(no diff)"
        target = ["HEAD"] if self.head()[1] else []
        tracked = self.git("diff", "--no-ext-diff", "--no-textconv", "--ignore-submodules=all",
                           *target, "--", name)
        return clip(tracked or self.patch(name)[1] or "(no diff)")

    def _write(self, file: Path, content: bytes) -> None:
        name = file.relative_to(self.root).as_posix()
        current = capture(file)
        if name in self.written and current != self.written[name]:
            raise Jail(f"File changed outside the tool: {name}")
        if current is not None and current.data == content:
            return
        self.original.setdefault(name, current)
        for parent in reversed(file.parents):
            if parent != self.root and parent.is_relative_to(self.root) and not parent.exists():
                parent.mkdir()
                self.created_dirs.append(parent)
        state = FileState(content, current.mode if current else stat.S_IFREG | 0o644)
        replace_file(file, state)
        self.written[name] = state
        self.written[name] = capture(file)
        self.green = False

    def write_file(self, path: str, content: str) -> str:
        self._write(self.safe(path, write=True), content.encode("utf-8"))
        return f"Wrote {path}."

    def edit_file(self, path: str, old: str, new: str) -> str:
        file = self.safe(path, write=True)
        current = capture(file)
        if current is None:
            raise ValueError(f"File does not exist: {path}")
        text = current.data.decode("utf-8")
        if old not in text and "\r\n" in text:
            old = old.replace("\n", "\r\n")
            new = new.replace("\n", "\r\n")
        count = text.count(old)
        if not old or count != 1:
            raise ValueError(f"old must occur exactly once (found {count}).")
        self._write(file, text.replace(old, new).encode("utf-8"))
        return f"Edited {path}."

    def run_tests(self) -> str:
        self.green = False
        if not self.argv:
            return "No test command configured."
        with tempfile.TemporaryFile() as output:
            try:
                result = subprocess.run(self.argv, cwd=self.root, env=child_env(), stdout=output,
                                        stdin=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                                        timeout=300, shell=False, check=False)
            except subprocess.TimeoutExpired:
                return "Test command timed out after 300 seconds."
            size = output.tell()
            output.seek(0)
            body = output.read(OUT_LIMIT)
            if size > OUT_LIMIT:
                output.seek(-OUT_LIMIT // 2, os.SEEK_END)
                body = body[:OUT_LIMIT // 2] + b"\n...\n" + output.read()
        self.green = result.returncode == 0 and bool(self.written)
        return clip(f"exit {result.returncode}\n" + body.decode("utf-8", "replace"))

    def finish(self, status: str, note: str) -> str:
        if status not in {"done", "blocked"}:
            raise ValueError("Use done or blocked.")
        self.finished = status, " ".join(note.split())[:300]
        return "Finished."

    def patch(self, scope: str = ".", limit: int | None = 12000):
        files, patches = [], []
        for name in sorted(self.written):
            if not Path(name).is_relative_to(Path(scope)):
                continue
            before = self.original[name]
            after = capture(self.safe(name, write=True))
            if before == after:
                continue
            files.append(name)
            try:
                old = (before.data if before else b"").decode("utf-8").splitlines(keepends=True)
                new = (after.data if after else b"").decode("utf-8").splitlines(keepends=True)
            except UnicodeError:
                patches.append(f"Binary file changed: {name}\n")
                continue
            diff = difflib.unified_diff(old, new, f"a/{name}" if before else "/dev/null",
                                       f"b/{name}" if after else "/dev/null")
            patches.extend(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                           for line in diff)
            if not old and not new:
                patches.append(f"Empty file changed: {name}\n")
        return files, "".join(patches) if limit is None else clip("".join(patches), limit)

    def rollback(self):
        failures = []
        for name, expected in self.written.items():
            try:
                path = self.safe(name, write=True)
                current = capture(path)
                if current == self.original[name]:
                    continue
                if current != expected:
                    raise Jail("File changed outside the tool.")
                replace_file(path, self.original[name])
            except (OSError, Jail) as exc:
                failures.append(f"{name}: {exc}")
        for parent in reversed(self.created_dirs):
            try:
                self.check_parents(parent)
                parent.rmdir()
            except (OSError, Jail):
                pass
        return failures
