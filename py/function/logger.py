#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日志封装：控制台颜色 + 文件输出。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional


ANSI_COLORS = {
    "INFO": "\033[94m",  # 蓝
    "WARNING": "\033[93m",  # 黄
    "ERROR": "\033[91m",  # 红
    "SUCCESS": "\033[92m",  # 绿
}

RESET = "\033[0m"
ANSI_PATTERN = re.compile(r"\033\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_PATTERN.sub("", text)


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        base_msg = super().format(record)
        color = ANSI_COLORS.get(record.levelname, "")
        if record.levelname == "SUCCESS":
            color = ANSI_COLORS["SUCCESS"]
        if color:
            return f"{color}{base_msg}{RESET}"
        return base_msg


def setup_logger(log_file: Optional[Path] = None) -> logging.Logger:
    logger = logging.getLogger("ad_workflow")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # 清理旧 handler，避免重复输出
    if logger.handlers:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = ColorFormatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # 为成功日志增加自定义 level
    if not hasattr(logging, "SUCCESS"):
        logging.SUCCESS = 25  # type: ignore[attr-defined]
        logging.addLevelName(logging.SUCCESS, "SUCCESS")

        def success(self, message, *args, **kwargs):  # type: ignore[override]
            if self.isEnabledFor(logging.SUCCESS):
                self._log(logging.SUCCESS, message, args, **kwargs)

        logging.Logger.success = success  # type: ignore[assignment]

    return logger


__all__ = ["setup_logger", "strip_ansi"]
