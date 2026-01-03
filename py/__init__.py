"""Project package init with a tiny `py.path` shim for pytest compatibility."""

from __future__ import annotations

from pathlib import Path as _Path


class _PyPathLocal(_Path):
    """Minimal replacement for pytest's py.path.local."""

    if hasattr(_Path, "_flavour"):
        _flavour = type(_Path())._flavour  # type: ignore[attr-defined]

    def __new__(cls, *args, **kwargs):
        if args and isinstance(args[0], _Path):
            return args[0]
        return super().__new__(cls, *args, **kwargs)


class _PyPathModule:
    local = _PyPathLocal


path = _PyPathModule()

__all__ = ["path"]
