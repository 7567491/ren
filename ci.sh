#!/bin/bash
# 统一 CI 脚本：执行前端构建 + Python 测试

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTEST_WAVESPEED_MOCK="${PYTEST_WAVESPEED_MOCK:-1}"

exec "${REPO_ROOT}/run_tests.sh" "$@"
