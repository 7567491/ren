#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""环境变量加载与校验工具。"""

from __future__ import annotations

import os
from typing import Iterable, List

REQUIRED_ENV_KEYS = ["WAVESPEED_API_KEY", "MINIMAX_API_KEY", "STORAGE_BUCKET_URL"]


def ensure_required_env(required_keys: Iterable[str] | None = None) -> None:
    """确保关键环境变量存在，否则抛出 RuntimeError。"""
    keys = list(required_keys or REQUIRED_ENV_KEYS)
    missing: List[str] = [name for name in keys if not os.getenv(name)]
    if not missing:
        return

    checklist = "\n".join(f"  - {name}" for name in missing)
    raise RuntimeError(
        "缺少必要的环境变量，请在 .env 或运行环境中设置：\n"
        f"{checklist}\n\n"
        "可以参考仓库中的 .env.example 填写对应的 API Key、存储地址等。"
    )


__all__ = ["ensure_required_env", "REQUIRED_ENV_KEYS"]
