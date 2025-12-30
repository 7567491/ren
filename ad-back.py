#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API 服务启动入口。

提供统一的 CLI，负责加载 .env、解析运行参数，并以 uvicorn
启动 `py.api_server` 中的 FastAPI 应用。随后可以在此基础上继续
扩展配置校验、日志等阶段 3 任务。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError as exc:  # pragma: no cover
    raise SystemExit("python-dotenv 未安装，请先运行 pip install python-dotenv") from exc

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 18005


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Digital Human API server (FastAPI + uvicorn)"
    )
    parser.add_argument("--host", default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("AD_BACK_PORT", DEFAULT_PORT)),
        help=f"监听端口 (默认: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="可选的 config.yaml 路径，尚未接入可用时将设置到 AD_BACK_CONFIG env",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式 (uvicorn reload & debug logging)",
    )
    return parser.parse_args()


def main() -> int:
    os.chdir(PROJECT_ROOT)
    load_dotenv()

    sys.path.insert(0, str(PROJECT_ROOT))
    from py.function.env_loader import ensure_required_env  # type: ignore

    args = parse_args()
    if args.config:
        resolved = Path(args.config).expanduser().resolve()
        if not resolved.exists():
            print(f"⚠️  指定的配置文件不存在: {resolved}")
            return 1
        os.environ["AD_BACK_CONFIG"] = str(resolved)

    ensure_required_env()

    import uvicorn

    app_path = "py.api_server:app"
    uvicorn_kwargs = {
        "host": args.host,
        "port": args.port,
        "log_level": "debug" if args.debug else "info",
    }
    if args.debug:
        uvicorn_kwargs["reload"] = True

    print("🚀 启动数字人 API 服务 ...")
    print(f"   - Host: {args.host}:{args.port}")
    print(f"   - Swagger: http://{args.host}:{args.port}/docs")

    uvicorn.run(app_path, **uvicorn_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
