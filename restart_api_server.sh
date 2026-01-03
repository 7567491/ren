#!/bin/bash
# 数字人 API 重启脚本
#
# - 读取 .env 并注入环境变量
# - 优雅停止现有 uvicorn/py.api_server 进程
# - 使用 uvicorn 启动 FastAPI（默认 0.0.0.0:18005）

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_MODULE=${APP_MODULE:-py.api_server:app}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-18005}
LOG_DIR="${REPO_ROOT}/logs"
LOG_FILE="${LOG_DIR}/api-server.log"
VENV_ACTIVATE="${REPO_ROOT}/venv/bin/activate"

echo "==> 重启数字人 API (${APP_MODULE})"

if [ ! -f "${VENV_ACTIVATE}" ]; then
  echo "❌ 未找到虚拟环境：${VENV_ACTIVATE}"
  exit 1
fi

# 加载 .env（若存在）
if [ -f "${REPO_ROOT}/.env" ]; then
  echo "   - 载入 .env"
  set -a
  # shellcheck disable=SC1090
  source "${REPO_ROOT}/.env"
  set +a
fi

source "${VENV_ACTIVATE}"
mkdir -p "${LOG_DIR}"

# 停止旧进程
echo "   - 停止旧进程 (pattern: ${APP_MODULE})"
OLD_PIDS=$(pgrep -f "${APP_MODULE}" || true)
if [ -z "${OLD_PIDS}" ]; then
  OLD_PIDS=$(pgrep -f "py/api_server.py" || true)
fi
if [ -n "${OLD_PIDS}" ]; then
  if echo "${OLD_PIDS}" | xargs -r kill; then
    :
  else
    echo "   ! 无法结束部分进程（可能权限不足），继续尝试..."
  fi
  sleep 2
  if ps -p ${OLD_PIDS} >/dev/null 2>&1; then
    echo "   - 强制结束残留进程"
    if echo "${OLD_PIDS}" | xargs -r kill -9; then
      :
    else
      echo "   ! 仍无法结束进程，请确认权限或手动处理"
    fi
  fi
else
  echo "   - 未发现运行中的 API 进程"
fi

# 启动新实例
echo "   - 启动 uvicorn @ ${HOST}:${PORT}"
nohup uvicorn "${APP_MODULE}" --host "${HOST}" --port "${PORT}" > "${LOG_FILE}" 2>&1 &
NEW_PID=$!
sleep 2

echo "✅ API 已启动 (PID: ${NEW_PID})"
echo "   - 日志: ${LOG_FILE}"
echo "   - 健康检查: http://${HOST}:${PORT}/health"
