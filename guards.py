"""Host-boundary guards: child environment, working-directory refusal, data location."""

import os
from pathlib import Path

BASE_ENV = ("PATH", "HOME", "USERPROFILE", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP",
            "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "PATHEXT", "COMSPEC")
PASSTHROUGH_VAR = "PS_ENV_PASSTHROUGH"


def child_env(extra: dict | None = None) -> dict:
    """Explicit minimal environment; never the inherited one.

    The owner may name extra variables to forward in PS_ENV_PASSTHROUGH (comma separated).
    """
    names = list(BASE_ENV)
    names += [n.strip() for n in os.environ.get(PASSTHROUGH_VAR, "").split(",") if n.strip()]
    env = {}
    for name in names:
        for key, value in os.environ.items():
            if key.upper() == name.upper():
                env[key] = value
    env.update(extra or {})
    return env


def hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home
        return Path(get_hermes_home())
    except Exception:
        return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")


def data_root() -> Path:
    """Per-profile plugin data directory."""
    if directory := os.environ.get("PS_DATA_DIR"):
        return Path(directory).expanduser()
    return hermes_home() / "plugin-data" / "patchsmith"


def _resolved(path: Path) -> Path:
    try:
        return path.resolve()
    except (OSError, RuntimeError):
        return path.absolute()


def _inside(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents


def check_workdir(root: Path) -> None:
    """Refuse a workdir that is, contains or sits inside the Hermes home, the user home or a root."""
    root = _resolved(root)
    home = _resolved(hermes_home())
    user = _resolved(Path.home())
    if root.parent == root:
        raise ValueError("Refusing a filesystem root as workdir.")
    if root == user:
        raise ValueError("Refusing the user home directory itself as workdir; use a project checkout.")
    if _inside(root, home) or _inside(home, root):
        raise ValueError("Refusing a workdir that is, contains or sits inside the Hermes home.")


def protected_target(relative: Path) -> bool:
    """Write targets Patchsmith never touches: .env* files and anything under .ssh/."""
    parts = [p.casefold() for p in relative.parts]
    return any(p == ".ssh" for p in parts) or (bool(parts) and parts[-1].startswith(".env"))
