"""FastAPI 应用入口：仅暴露数字人相关接口。"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from py.api.routes_digital_human import (
    register_exception_handlers,
    router as digital_human_router,
)

app = FastAPI(
    title="Digital Human API",
    description="WaveSpeed 数字人生成服务",
    version="1.0.0",
)
app.include_router(digital_human_router)
register_exception_handlers(app)


class LegacyCORSHeaderMiddleware(BaseHTTPMiddleware):
    """沿用旧版 CORS 策略，兼容移动端本地调试。"""

    async def dispatch(self, request, call_next):
        if request.method == "OPTIONS":
            from starlette.responses import PlainTextResponse

            response = PlainTextResponse("OK", status_code=200)
        else:
            response = await call_next(request)

        response.headers["access-control-allow-origin"] = "*"
        response.headers["access-control-allow-methods"] = (
            "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
        )
        response.headers["access-control-allow-headers"] = "*"
        response.headers["access-control-max-age"] = "600"
        response.headers["access-control-allow-credentials"] = "false"
        return response


app.add_middleware(LegacyCORSHeaderMiddleware)


@app.get("/api/health")
async def health_check():
    """最小化健康检查接口，方便 Nginx/监控探活。"""
    return JSONResponse({"status": "ok"})


RESOURCE_PIC_DIR = Path(
    os.getenv("CHARACTER_STORAGE_DIR")
    or Path(__file__).parent.parent / "resource" / "pic"
)
if RESOURCE_PIC_DIR.exists():
    app.mount(
        "/resource/pic",
        StaticFiles(directory=str(RESOURCE_PIC_DIR)),
        name="resource-pic",
    )
