# 数字人端到端测试指引

本文记录数字人流水线最小化验证方法，覆盖“头像→语音→唇同步→发布”全链路。所有步骤均默认在仓库根目录执行。

---

## 1. 冒烟测试（10 秒）

1. 准备环境变量：在 `.env` 中填好 `WAVESPEED_API_KEY`、`MINIMAX_API_KEY`、`STORAGE_BUCKET_URL`。
2. 运行冒烟脚本（默认 10 秒以内文案，成本 < \$0.1）：

   ```bash
   ./test/smoke_digital_human.sh
   # 可按需覆盖参数，例如：
   SMOKE_TEXT="欢迎体验数字人" ./test/smoke_digital_human.sh --resolution 1080p
   ```

3. 脚本会调用 `py/test_network.py --digital-human`，产物（avatar.png、speech.mp3、digital_human.mp4、task.json、log.txt）将写入 `output/smoke/aka-test-*/`。
4. 控制台将打印头像/语音/视频 URL、成本估算与阶段状态；若 `--json`，可直接存档。

验证点：
- `task.json` 中 `status=finished`、`trace_id` 以 `trace-` 开头、`config_hash` 与当前配置一致。
- `log.txt` 含结构化记录：`[timestamp][LEVEL][trace=...]`，三阶段均应出现 `completed` 文案。
- `/mnt/www/.../digital_human.mp4`（如配置）可直接在浏览器播放。

---

## 2. 自动化回归

1. 开发阶段可运行 mock + 构建测试：

   ```bash
   PYTEST_WAVESPEED_MOCK=1 ./run_tests.sh
   ```

   该脚本会 `npm run build` + `pytest`，验证：
   - TaskRunner 状态流转、成本统计、config_hash 校验；
   - StorageService 发布/日志追加；
   - API 路由的参数校验与异常处理（含 trace_id）。

2. 如需真实联调，请务必手动执行第 1 节冒烟脚本并记录成本。

---

## 3. 输出目录清理

- `output/` 下的 `aka-*`、`smoke/aka-*` 已写入 `.gitignore`，可定期清理：

  ```bash
  find output -maxdepth 1 -type d -name 'aka-*' -mtime +7 -print -exec rm -rf {} +
  find output/smoke -maxdepth 1 -type d -name 'aka-*' -mtime +3 -print -exec rm -rf {} +
  ```

- 保留最近一次冒烟产物（含 `log.txt`）作为回归证据，并在 `logs/` 或项目文档中记录成本。

---

## 4. 常见问题

| 问题 | 处理建议 |
|------|----------|
| `ExternalAPIError` 或 429 限流 | 查看响应中的 `trace_id`，如需申诉可附 `log.txt` 中同样的 trace；等待 1-2 分钟再重试。 |
| `config_hash mismatch` | 说明 `config.yaml/user.yaml` 已变更，请重新创建任务（旧任务不可恢复）。 |
| 日志缺少阶段记录 | 确认 `output/<job_id>/log.txt` 是否存在；若任务未创建成功，可能是环境变量缺失。 |

---

## 5. 最近冒烟记录

| 日期 | 命令 | 产物目录 | 备注 |
|------|------|----------|------|
| 2025-12-30 | `./test/smoke_digital_human.sh --json` | `output/smoke/aka-test-202512301330/` | 视频发布到 `https://s.linapp.fun/ren/ren_12310639/digital_human.mp4`，trace 见该目录 `task.json/log.txt`。 |

> 新的冒烟/回归结果请追加到此表，确保每次上线都有可追溯记录（含 job_id、trace_id、video_url、成本）。

---

若有新的验证脚本或额外的联调注意事项，请在此文档直接追加，以保持单一可信来源。
