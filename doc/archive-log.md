# 归档记录

## 2025-12-31 清理

本次仅保留 README 中定义的核心目录/文件（ad-back.py、frontend/、py/、doc/ 等），其余辅助脚本与临时产物统一移动到 `archive/2025-02-cleanup/`，需要恢复时将对应目录/文件 `mv` 回项目根目录即可。

| 原路径 | 归档路径 | 归档原因 |
| --- | --- | --- |
| `auto/` | `archive/2025-02-cleanup/auto/` | 自动化代理脚本，仅调试时使用 |
| `auto-ccp-backup/` | `archive/2025-02-cleanup/auto-ccp-backup/` | 历史自动化备份 |
| `codex-0.65.0/` | `archive/2025-02-cleanup/codex-0.65.0/` | 旧版工具链 |
| `logs/` | `archive/2025-02-cleanup/logs/` | 运行日志，可按需查阅 |
| `music/` | `archive/2025-02-cleanup/music/` | 音乐资源脚本，非数字人核心链路 |
| `pic/` | `archive/2025-02-cleanup/pic/` | 图片批处理脚本，仅用于素材管理 |
| `ref/` | `archive/2025-02-cleanup/ref/` | 参考资料 |
| `temp/` | `archive/2025-02-cleanup/temp/` | 临时文件 |
| `temp_ad-back_backup.py` | `archive/2025-02-cleanup/temp_ad-back_backup.py` | 历史备份脚本 |
| `venv/` | `archive/2025-02-cleanup/venv/` | 可重新运行 `python3 -m venv` 创建 |
| `workflow.html` | `archive/2025-02-cleanup/workflow.html` | 文档展示 |
| `output/`（历史产物） | `archive/2025-02-cleanup/output-2025-02-14/` | 生成视频、冒烟记录；项目根已重建空 `output/` |

> 恢复示例：`mv archive/2025-02-cleanup/auto ./auto`

如需再次归档/恢复，请更新本文件，确保可以追溯。
