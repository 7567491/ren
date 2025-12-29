"""Project package init with compatibility shim for pytest's `py.path`."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_external_py_path():
    current_file = Path(__file__).resolve()
    candidates = []
    for search in list(sys.path):
        try:
            base = Path(search)
        except Exception:  # noqa: BLE001
            continue
        candidate = base / "py" / "__init__.py"
        try:
            if candidate.resolve() == current_file:
                continue
        except Exception:  # noqa: BLE001
            continue
        if candidate.exists():
            candidates.append(candidate)

    for candidate in candidates:
        # 临时移除当前模块，确保能加载外部 py 包
        saved = sys.modules.pop("py", None)
        saved_path = list(sys.path)
        try:
            sys.path.insert(0, str(candidate.parent.parent))
            ext_spec = importlib.util.find_spec("py")
            if not ext_spec or not ext_spec.loader:
                continue
            ext_mod = importlib.util.module_from_spec(ext_spec)
            sys.modules["py"] = ext_mod
            ext_spec.loader.exec_module(ext_mod)  # type: ignore[arg-type]
            return getattr(ext_mod, "path", None)
        except Exception:  # noqa: BLE001
            continue
        finally:
            # 恢复自身模块注册
            sys.modules["py"] = saved or sys.modules.get(__name__, None) or sys.modules.setdefault("py", sys.modules[__name__])
            sys.path = saved_path
    return None


# 尝试为 pytest 提供 py.path 兼容
try:
    path = _load_external_py_path()
except Exception:  # noqa: BLE001
    path = None

if path is None:
    from pathlib import Path as _Path

    class _PyPathLocal(_Path):
        def __new__(cls, *args, **kwargs):
            return _Path.__new__(cls, *args, **kwargs)

    class _PyPathModule:
        local = _PyPathLocal

    path = _PyPathModule()

__all__ = ["path"]
