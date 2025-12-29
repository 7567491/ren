#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步入口：解析 CLI 并运行工作流。
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from py.function import cli


def main() -> None:
    asyncio.run(cli.main_async())


if __name__ == "__main__":
    main()
