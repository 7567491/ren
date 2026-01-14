#!/bin/bash
# 数字人 10 秒冒烟脚本
#
# 作用：
#   1. 加载 .env 并调用 py/test_network.py --digital-human
#   2. 统一设置 10 秒左右的中文文案，控制成本 < 0.1 USD
#   3. 将产物落在 output/smoke/aka-test-*/ 下，方便回归与日志归档
#
# 使用示例：
#   ./test/smoke_digital_human.sh
#   ./test/smoke_digital_human.sh --resolution 1080p
#
# 需要环境变量：
#   WAVESPEED_API_KEY, MINIMAX_API_KEY (默认共用同一 key)
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT"

SMOKE_TEXT=${SMOKE_TEXT:-"大家好，这是一段 10 秒数字人冒烟测试文案，用于验证接口连通性。"}
OUTPUT_DIR=${OUTPUT_DIR:-"$REPO_ROOT/output/smoke"}
TEMP_DIR=${TEMP_DIR:-"$REPO_ROOT/temp/smoke"}
PUBLIC_URL_OVERRIDE=${PUBLIC_URL_OVERRIDE:-""}

CMD=(
  python3 "$REPO_ROOT/py/test_network.py"
  --digital-human
  --speech-text "$SMOKE_TEXT"
  --output-dir "$OUTPUT_DIR"
  --temp-dir "$TEMP_DIR"
)

if [[ -n "$PUBLIC_URL_OVERRIDE" ]]; then
  CMD+=(--public-url "$PUBLIC_URL_OVERRIDE")
fi

CMD+=("$@")

echo "==> 运行数字人冒烟脚本"
echo "    文案长度: ${#SMOKE_TEXT} 字"
echo "    输出目录: $OUTPUT_DIR"
echo "    临时目录: $TEMP_DIR"

"${CMD[@]}"
