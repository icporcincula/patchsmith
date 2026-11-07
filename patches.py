"""Isolated proposals and guarded, explicitly requested patch application."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import uuid

from .tools import Jail, Session, capture, clip, linked

ARTIFACT_ROOT = Path.home() / ".patchsmith" / "proposals"


class Refused(ValueError):
    def __init__(self, reason, note):
        super().__init__(note)
        self.reason = reason


def private_directory(path):
    for parent in [*reversed(path.parents), path]:
        if linked(parent):
            raise Jail("Proposal storage must not contain links.")
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    return path.resolve(strict=True)


def fingerprint(state):
    if state is None:
        return None
    if not isinstance(state.data, bytes):
        raise Jail("Proposal files must be regular files, not links.")
    return {"sha256": hashlib.sha256(state.data).hexdigest(), "mode": stat.S_IMODE(state.mode)}


def index_state(session, name):
    return session.git("ls-files", "--stage", "-z", "--", name) if session.is_git else None


def copy_checkout(root, destination):
    # Preserve dirty, ignored and untracked files; never share linked content.
    for directory, dirs, files in os.walk(root):
        base = Path(directory)
        dirs[:] = [name for name in dirs if name not in {".git", ".patchsmith", "__pycache__", ".pytest_cache"}]
        target = destination / base.relative_to(root)
        target.mkdir(parents=True, exist_ok=True)
        for name in dirs + files:
            if name in {".git", ".patchsmith"}:
                continue
            path = base / name
            if linked(path):
                raise Jail("Propose refuses linked checkout content: " + str(path.relative_to(root)))
            if path.is_file():
                if not stat.S_ISREG(path.stat().st_mode):
                    raise Jail("Propose requires regular files.")
                shutil.copy2(path, target / name)


@contextmanager
def isolated_checkout(source, directory):
    sandbox = directory / "checkout"
    if source.is_git:
        if not source.head()[1]:
            raise ValueError("Propose requires an initial Git commit.")
        # Avoid checkout hooks and content filters; populate from the current bytes.
        source.git("worktree", "add", "--detach", "--no-checkout", str(sandbox), "HEAD")
    else:
        sandbox.mkdir()
    try:
        copy_checkout(source.root, sandbox)
        if source.is_git:
            Session(sandbox, "").git("read-tree", "HEAD")
        yield sandbox
    finally:
        if linked(sandbox) or not sandbox.resolve().is_relative_to(directory.resolve()):
            raise Jail("Refused cleanup of a replaced proposal checkout.")
        if source.is_git:
            source.git("worktree", "remove", "--force", str(sandbox))
        else:
            shutil.rmtree(sandbox)


def valid_name(name):
    if (not isinstance(name, str) or not name or name.startswith("/")
            or "\\" in name or any(ord(char) < 32 for char in name)):
        raise Jail("Unsupported patch path.")
    return name


def unchanged(source, record):
    head = source.head()
    if list(head) != record["head"]:
        raise Refused("stale_base", "HEAD or branch moved since this proposal was created.")
    for name, expected in record["files"].items():
        path = source.safe(valid_name(name), write=True)
        if fingerprint(capture(path)) != expected["before"] or index_state(source, name) != expected["index"]:
            raise Refused("files_changed", "A proposed file or its index entry changed: " + name)


def propose(root, client, task, turns, budget, command, keep, execute, **options):
    storage = ARTIFACT_ROOT.resolve()
    if storage.is_relative_to(root):
        raise Jail("Choose a workdir outside the proposal storage directory.")
    storage = private_directory(ARTIFACT_ROOT)
    directory = storage / uuid.uuid4().hex
    directory.mkdir(mode=0o700)
    source = Session(root, "")
    head = source.head()
    record = {"version": 1, "workdir": str(root), "head": list(head), "files": {}}
    result = None
    with isolated_checkout(source, directory) as sandbox:
        session = Session(sandbox, command)
        result = execute(session, client, task, turns, budget, keep, log_dir=directory, **options)
        result.update(patch_path=None, patch_sha256=None, base_head=head[1].strip() or None, applied=False)
        if result["status"] == "done" and result["files_changed"]:
            names, patch = session.patch(limit=None)
            for name in names:
                source.safe(valid_name(name), write=True)
                record["files"][name] = {"before": fingerprint(session.original[name]),
                                         "after": fingerprint(capture(session.safe(name, write=True))),
                                         "index": index_state(source, name)}
            unchanged(source, record)
            payload = patch.encode("utf-8")
            # The stored artifact must be a complete Git-applicable text patch.
            source.git("apply", "--check", "--whitespace=nowarn", input_data=payload)
            record["sha256"] = hashlib.sha256(payload).hexdigest()
            record["base_head"] = result["base_head"]
            (directory / "patch.diff").write_bytes(payload)
            (directory / "manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
            result.update(patch_path=str(directory / "patch.diff"), patch_sha256=record["sha256"])
    with Path(result["transcript_path"]).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"event": "proposal", **result}) + "\n")
    return result


def load_proposal(value):
    if not isinstance(value, str) or not value:
        raise Refused("invalid_patch", "patch_path must name a saved Patchsmith proposal.")
    path = Path(value)
    storage = ARTIFACT_ROOT.resolve()
    if (not path.is_absolute() or path.name != "patch.diff"
            or not re.fullmatch(r"[a-f0-9]{32}", path.parent.name)
            or path.parent.parent != storage):
        raise Refused("invalid_patch", "Patch is outside Patchsmith proposal storage.")
    for parent in [path, *path.parents]:
        if linked(parent):
            raise Refused("invalid_patch", "Linked proposal artifacts are refused.")
    manifest = path.with_name("manifest.json")
    if linked(manifest) or not manifest.is_file() or not path.is_file():
        raise Refused("invalid_patch", "Proposal or provenance record is missing.")
    record = json.loads(manifest.read_text(encoding="utf-8"))
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != record.get("sha256"):
        raise Refused("hash_mismatch", "Patch contents differ from the recorded proposal hash.")
    if record.get("version") != 1 or not isinstance(record.get("files"), dict) or not record["files"]:
        raise Refused("invalid_patch", "Invalid proposal provenance record.")
    return path, record, payload


def apply_patch(args):
    from .loop import ACTIVE, ACTIVE_LOCK
    result = {"status": "blocked", "applied": False, "patch_path": None,
              "patch_sha256": None, "base_head": None, "files_changed": [], "diff": ""}
    try:
        path, record, payload = load_proposal(args.get("patch_path"))
        result.update(patch_path=str(path), patch_sha256=record["sha256"], base_head=record["base_head"])
        root = Path(record["workdir"])
        if not root.is_absolute() or root.resolve(strict=True) != root:
            raise Refused("invalid_patch", "The original workdir moved or became a link.")
        source = Session(root, "")
        with ACTIVE_LOCK:
            if root in ACTIVE:
                raise Refused("busy", "A Patchsmith task is already running in this directory.")
            ACTIVE.add(root)
        try:
            unchanged(source, record)
            for expected in record["files"].values():
                before_mode = expected["before"]["mode"] if expected["before"] else None
                after_mode = expected["after"]["mode"]
                if ((before_mode is not None and after_mode != before_mode)
                        or (before_mode is None and after_mode not in {0o644, 0o666})):
                    raise Refused("invalid_patch", "Proposal file permissions are inconsistent with coding-tool writes.")
            # Ask Git which paths the patch actually changes; do not trust the manifest.
            entries = source.git("apply", "--numstat", "-z", input_data=payload).split("\0")
            actual = []
            for entry in entries:
                if not entry:
                    continue
                fields = entry.split("\t", 2)
                if len(fields) != 3 or not fields[0].isdigit() or not fields[1].isdigit():
                    raise Refused("invalid_patch", "Only ordinary text patches are supported.")
                name = valid_name(fields[2])
                source.safe(name, write=True)
                actual.append(name)
            if len(actual) != len(set(actual)) or set(actual) != set(record["files"]):
                raise Refused("invalid_patch", "Patch paths do not match the recorded proposal.")
            source.git("apply", "--check", "--whitespace=nowarn", input_data=payload)
            unchanged(source, record)
            source.git("apply", "--whitespace=nowarn", input_data=payload)
            result.update(status="done", applied=True, files_changed=actual,
                          diff=clip(payload.decode("utf-8"), 12000), note="Applied the reviewed proposal.")
            for name, expected in record["files"].items():
                file = source.safe(name, write=True)
                actual = fingerprint(capture(file))
                if actual and actual["sha256"] == expected["after"]["sha256"]:
                    # Git rewrites existing files with its own umask; preserve the recorded permissions.
                    file.chmod(expected["after"]["mode"])
                if fingerprint(capture(file)) != expected["after"]:
                    result.update(status="error", reason="verification_error",
                                  note="Patch was applied, but final bytes or mode differ from the proposal: " + name)
                    break
        finally:
            with ACTIVE_LOCK:
                ACTIVE.remove(root)
        with path.with_name("apply.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(result) + "\n")
    except Exception as exc:
        if result["applied"]:
            result.update(status="error", reason="post_apply_error",
                          note="Patch was applied, but final verification or logging failed: " + str(exc))
        else:
            result.update(reason=getattr(exc, "reason", "patch_refused"), note=str(exc))
    return result
