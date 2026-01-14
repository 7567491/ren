# 数字人运维手册

面向运维/值班人员，涵盖常见应急操作、扩容策略与故障排查。

## 1. 快速查表

| 操作 | 命令 | 说明 |
|------|------|------|
| 查看服务状态 | `systemctl status ren-digital-human.service` | systemd 监控的 FastAPI 服务 |
| 热重启 API | `./restart_api_server.sh` | 自动加载 `.env`，优雅停止旧 uvicorn 并拉起新进程 |
| 运行冒烟 | `./test/smoke_digital_human.sh --json` | 10 秒文案，产物写入 `output/smoke/aka-*` |
| 查看最近任务 | `ls -lt output | head` | 任务按时间排序；`log.txt` 记录 trace_id |
| 查看健康状态 | `curl http://127.0.0.1:18005/health` | 返回版本/依赖加载状态 |

## 2. 常见告警与处理

### WaveSpeed 429/5xx
1. 通过 `/api/tasks/<job_id>` 或 `output/<job_id>/log.txt` 获取 `trace_id`。
2. 查 `log.txt` 是否有指数退避记录；若多次失败，等待 1-2 分钟后重试。
3. 必要时将 `trace_id` + 请求参数发给 WaveSpeed 支持。

### 视频生成长时间卡在 `video_rendering`
1. 查看 `output/<job_id>/log.txt` 是否持续更新；若停滞，检查 Infinitetalk API 轮询日志。
2. 手动调用 `python3 py/test_network.py --digital-human --avatar-upload <已有图>` 验证链路。
3. 若多任务积压，可在 `config.yaml` 中降低并发并重启服务。

### API 502/504
1. `journalctl -u ren-digital-human.service -f` 查看实时日志。
2. 确认 `restart_api_server.sh` 是否被执行、虚拟环境依赖是否齐全。
3. 检查 Nginx `proxy_read_timeout` 是否 ≥120s，避免唇同步超时。

## 3. 扩容与限流

- **Seedream 并发**：`config.yaml -> tasks.max_avatar_workers`，建议 ≤2；修改后执行 `./restart_api_server.sh`。
- **Infinitetalk 串行**：默认单线程，若需要并行需申请更高 QPS 并扩展 TaskRunner 调度逻辑。
- **任务队列**：可在 `TaskManager`/`task_runner` 外层增加简单排队（待 backlog 实现）。

## 4. 输出目录治理

```bash
# 正式任务保留 7 天
find /home/ren/output -maxdepth 1 -type d -name 'aka-*' -mtime +7 -print -exec rm -rf {} +
# 冒烟任务保留 3 天
find /home/ren/output/smoke -maxdepth 1 -type d -name 'aka-*' -mtime +3 -print -exec rm -rf {} +
```

`task.json` + `log.txt` 是排障依据，删除前请确认无未结工单。

## 5. 回归与记录

- **冒烟**：每次上线/配置变更后，运行 `./test/smoke_digital_human.sh --json`，将输出中的 `job_id`、`trace_id`、`video_url`、成本记录到 `test/test-digital-human.md`。
- **自动化**：`PYTEST_WAVESPEED_MOCK=1 ./run_tests.sh`。CI 可直接调用 `./run_tests.sh` 或 `./ci.sh`（见根目录脚本）。

## 6. FAQ

| 问题 | 排查步骤 |
|------|----------|
| `.env` 修改后无效 | 通过 `./restart_api_server.sh` 重启，脚本会重新加载 `.env` 并写入日志。 |
| 上传图片报 413 | 检查 Nginx `client_max_body_size`（需 ≥5M），确认前端是否压缩。 |
| `config_hash mismatch` | 用户使用旧任务/断点续传；需要重新创建任务，或清除 `output/<job_id>/task.json`。 |

---

更多架构细节见 `doc/部署配置.md` 与 `doc/工作流.md`；如需新增运维流程，请补充本手册并在 `doc/plan.md` 更新状态。EOF
