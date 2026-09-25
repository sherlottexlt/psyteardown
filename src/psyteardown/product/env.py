"""Small, dependency-free loader for the local Product Studio environment.

The project keeps secrets in a gitignored ``.env.local`` file.  That file is
written as shell assignments (``export NAME=value``), while Python processes
do not source shell files automatically.  Product Studio reads only the
configuration keys it needs and never logs their values.
"""

from __future__ import annotations

import os
import shlex
from pathlib import Path

_ENV_FILE = ".env.local"


def _candidate_files() -> tuple[Path, ...]:
    configured = os.environ.get("PSYTEARDOWN_ENV_FILE")
    candidates: list[Path] = []
    if configured:
        path = Path(configured).expanduser()
        return (path if path.name == _ENV_FILE else path / _ENV_FILE,)
    current = Path.cwd().resolve()
    candidates.extend((current / _ENV_FILE, *current.parents))
    candidates = [path if path.name == _ENV_FILE else path / _ENV_FILE for path in candidates]
    seen: set[Path] = set()
    return tuple(path for path in candidates if not (path in seen or seen.add(path)))


def _read_file(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        if "=" not in stripped:
            continue
        name, raw_value = stripped.split("=", 1)
        name = name.strip()
        if not name or not name.replace("_", "a").isalnum() or name[0].isdigit():
            continue
        try:
            parsed = shlex.split(raw_value, comments=True, posix=True)
        except ValueError:
            continue
        if parsed:
            values[name] = parsed[0]
    return values


def _project_value(name: str) -> str | None:
    for path in _candidate_files():
        value = _read_file(path).get(name)
        if value is not None:
            return value
    return None


def get_env(name: str, default: str | None = None) -> str | None:
    """Read the process environment, preserving normal Python semantics."""

    return os.environ.get(name, default)


def get_project_env(name: str, default: str | None = None) -> str | None:
    """Read repository-local config before the process environment.

    Product Studio uses this for its opt-in model providers so a gitignored
    project configuration can replace a stale user-level key. Explicit
    constructor arguments remain higher priority than this function.
    """

    return _project_value(name) or os.environ.get(name, default)
