"""Owner-managed settings for individual project checkouts."""

import argparse
import json
import os
from pathlib import Path

from .guards import check_workdir, data_root


def profile_path():
    return data_root() / "profiles.json"


def load(workdir):
    path = profile_path()
    if not path.exists():
        return {}
    if path.is_symlink() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Invalid project profiles file.")
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, dict):
        raise ValueError("Invalid project profiles file.")
    record = records.get(str(Path(workdir).resolve()), {})
    if not isinstance(record, dict):
        raise ValueError("Invalid project profile.")
    return record


def main():
    parser = argparse.ArgumentParser(description="Set owner-managed Patchsmith project settings.")
    parser.add_argument("workdir", type=Path)
    parser.add_argument("--test-command", required=True)
    parser.add_argument("--model")
    args = parser.parse_args()
    root = args.workdir.resolve(strict=True)
    check_workdir(root)
    if not root.is_dir() or not args.test_command.strip():
        parser.error("Use an existing project directory and a nonempty test command.")
    path = profile_path()
    if path.is_symlink() or (path.parent.exists() and path.parent.is_symlink()):
        parser.error("Profile storage must not be a link.")
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    records = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(records, dict):
        parser.error("Invalid project profiles file.")
    records[str(root)] = {"test_command": args.test_command, **({"model": args.model} if args.model else {})}
    temporary = path.with_suffix(".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(records, stream, indent=2)
    os.replace(temporary, path)
    print(f"Saved profile for {root}")


if __name__ == "__main__":
    main()
