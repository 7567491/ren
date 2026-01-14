#!/bin/bash
# 运行前端构建 + 后端测试的统一脚本

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$REPO_ROOT/frontend" ]; then
  echo "frontend/ 不存在，跳过前端构建"
else
  echo "==> 构建前端 (frontend/)"
  pushd "$REPO_ROOT/frontend" >/dev/null
  if [ ! -d node_modules ]; then
    npm ci
  else
    npm install
  fi
  npm run build
  popd >/dev/null
fi

echo "==> 运行 Python 测试"
export PYTHONPATH="$REPO_ROOT"
source "$REPO_ROOT/venv/bin/activate"
pytest "$@"
