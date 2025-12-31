# 仪表盘上线 Checklist（2025-12-31）

## 1. 上线前必做
1. **确认分支**：`git status` 必须干净，仅包含本次仪表盘改动（多卡片、移动抽屉、文档）。  
2. **配置核对**：
   - `.env`：确保存在 `WAVESPEED_API_KEY`、`MINIMAX_KEY`、`INFINITETALK_KEY`，未提交到 Git；
   - `config.yaml`：`bucket_root=/mnt/www`、`bucket_user_dir=ren`，供素材卡片映射；
   - Nginx：`client_max_body_size 200m`、`/output/` alias `/home/ren/output/`，并将 `/frontend/dist` 作为根目录。
3. **构建命令**（严格顺序）：
   ```bash
   npm install
   npm run lint --if-present
   npm run test
   npm run build
   PYTEST_WAVESPEED_MOCK=1 ./run_tests.sh
   ```
   - 如需最小成本验证，再跑 `python3 py/test_network.py --digital-human --mock` 并记录 job_id。
4. **设计评审反馈已落地**：底部抽屉、任务顺序、余额刷新提示三项均在 `frontend/src/App.vue` 生效；评审纪要见 `doc/ui.md`。
5. **接口确认**：与后端核实 `/api/tasks/<job_id>` 字段（`assets.local_video_url`、`audio_local_path` 等），任何字段调整需同步 `doc/工作流.md`。
6. **演示录像**：录制 30 秒屏幕视频（桌面 + iPhone 模拟器），上传至 `/output/aka-demo/ui-drawer.mp4` 供运维培训。

## 2. 自测结果

| 项目 | 时间 | 结果 | 备注 |
|------|------|------|------|
| `npm run test` | 2025-12-31 20:25 | ✅ | 包含新增移动抽屉 e2e 用例 |
| `PYTEST_WAVESPEED_MOCK=1 ./run_tests.sh` | 2025-12-31 20:36 | ✅ | Mock 模式，后端无回归 |
| `python3 py/test_network.py --digital-human --mock` | 2025-12-31 20:45 | ✅ | job_id=aka-drawer-001，trace=trace-61a2b，与 `/home/wave` 输出一致 |
| 移动端实机演示 | 2025-12-31 21:10 | ✅ | 详单见 `doc/ui.md#移动端实机演示与问题记录` |

Bug List：仅遗留“抽屉关闭后 body 滚动未恢复”问题，已通过 `watch(mobileDrawerPanel)` 修复并回归。

## 3. 上线后监控

- **实时监控**：
  - `TaskResponse.assets.local_video_url` 日志中缺失率 < 1%，通过 `test/test_digital_human_storage_flow.py` 反向验证；
  - Pinia `processedAnalytics`（抽屉打开埋点）每 5 分钟发送心跳，Prometheus 指标 `ui_drawer_open_total`；
  - `output/<job_id>/log.txt` 自动上传到 Loki，搜索 `[trace=xxx] mobile drawer` 关键字即可定位。
- **报警阈值**：
  1. 抽屉打开率 < 50%（说明用户找不到入口）；
  2. 素材卡片“路径异常”错误累计 5 次/小时；
  3. `TaskResponse.assets.local_video_url` 缺失率 > 5%。
  报警渠道：钉钉群 #digital-human-ui。
- **反馈收集**：上线 48 小时内通过飞书问卷（链接见群公告）收集运维/运营意见，每条至少包含 job_id + trace_id。

## 4. 回滚预案

1. `git tag ui-dashboard-<date>` 后再部署；
2. 若出现 P0，执行 `./restart_api_server.sh --from-tag ui-dashboard-<prev>` 回滚（脚本会拉取上一个 tag 并重启 uvicorn）；
3. Nginx 静态资源回滚：直接切换到备份目录 `/home/ren/frontend-release/<prev>/dist`；
4. 回滚后通知产品/设计并同步 `doc/ui.md` 状态。

## 5. 可选演进（非阻塞）

- 抽屉内容支持“任务列表”第三个入口，用于快速切换 job_id；
- 素材卡片引入文件大小、修改时间，方便排查大文件；
- `MaterialPanel` 挂载播放器时动态加载 `video.js`，减少首屏体积；
- 通过 PWA manifest 把仪表盘封装成桌面图标，方便移动端内测。
