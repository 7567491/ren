#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行上下文定义。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from .config_loader import LoadedConfig
from .logger import setup_logger


def _gen_session_id(prefix: str = "aka") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@dataclass
class RunContext:
    config: LoadedConfig
    session_id: str = field(default_factory=_gen_session_id)
    work_dir: Path = Path("./output")
    log_file: Optional[Path] = None
    logger: Any = None
    state: Dict[str, Any] = field(default_factory=dict)
    assets: Dict[str, Any] = field(default_factory=dict)
    limiters: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    clients: Dict[str, Any] = field(default_factory=dict)

    def init_paths(self, output_base: Optional[Path] = None) -> None:
        base = output_base or self.work_dir
        self.work_dir = Path(base) / self.session_id
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.work_dir / "run.log"
        self.logger = setup_logger(self.log_file)
        self.logger.info(f"工作目录: {self.work_dir}")
        self.logger.info(f"日志文件: {self.log_file}")


__all__ = ["RunContext", "_gen_session_id"]
