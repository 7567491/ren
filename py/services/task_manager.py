"""
任务管理器 - 负责任务的创建、状态跟踪和持久化
"""
import os
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional


class TaskManager:
    """任务管理器 - 内存 + JSON 持久化"""

    def __init__(self, storage_dir: str = "temp"):
        """
        初始化任务管理器

        Args:
            storage_dir: 存储目录，默认为 temp/
        """
        self.storage_dir = storage_dir
        self.storage_file = os.path.join(storage_dir, "jobs.json")
        self.tasks: Dict[str, dict] = {}
        self.lock = threading.Lock()

        # 确保存储目录存在
        os.makedirs(storage_dir, exist_ok=True)

        # 加载现有任务
        self._load_tasks()

    def create_task(
        self,
        preset_name: Optional[str] = None,
        num_shots: int = 5,
        resolution: str = "720p",
        user_yaml: Optional[str] = None,
        resume_id: Optional[str] = None,
        no_auto_resume: bool = False
    ) -> str:
        """
        创建新任务

        Args:
            preset_name: 预设风格名称
            num_shots: 镜头数
            resolution: 分辨率
            user_yaml: 用户自定义配置（YAML 文本）
            resume_id: 恢复的任务 ID
            no_auto_resume: 禁用自动恢复

        Returns:
            job_id: 任务 ID（格式：aka-{mmddhhmm}）
        """
        with self.lock:
            # 生成 job_id（格式：aka-{mmddhhmm}）
            job_id = self._generate_job_id()

            # 创建任务记录
            task = {
                'job_id': job_id,
                'status': 'queued',  # queued, running, succeeded, failed
                'message': '任务已创建，等待执行',
                'progress': 0.0,
                'result_path': None,
                'log_path': f'output/{job_id}/log.txt',
                'created_at': datetime.now().isoformat(),
                'preset_name': preset_name,
                'num_shots': num_shots,
                'resolution': resolution,
                'user_yaml': user_yaml,
                'resume_id': resume_id,
                'no_auto_resume': no_auto_resume
            }

            self.tasks[job_id] = task
            self._save_tasks()

            return job_id

    def get_task(self, job_id: str) -> Optional[dict]:
        """
        获取任务详情

        Args:
            job_id: 任务 ID

        Returns:
            任务详情字典，不存在则返回 None
        """
        with self.lock:
            return self.tasks.get(job_id)

    def update_status(self, job_id: str, status: str, message: str = ""):
        """
        更新任务状态

        Args:
            job_id: 任务 ID
            status: 新状态 (queued/running/succeeded/failed)
            message: 状态消息
        """
        with self.lock:
            if job_id in self.tasks:
                self.tasks[job_id]['status'] = status
                self.tasks[job_id]['message'] = message
                self._save_tasks()

    def update_progress(self, job_id: str, progress: float, message: str = ""):
        """
        更新任务进度

        Args:
            job_id: 任务 ID
            progress: 进度值 (0.0 - 1.0)
            message: 进度消息
        """
        with self.lock:
            if job_id in self.tasks:
                self.tasks[job_id]['progress'] = progress
                if message:
                    self.tasks[job_id]['message'] = message
                self._save_tasks()

    def set_result_path(self, job_id: str, result_path: str):
        """
        设置任务结果路径

        Args:
            job_id: 任务 ID
            result_path: 结果文件路径
        """
        with self.lock:
            if job_id in self.tasks:
                self.tasks[job_id]['result_path'] = result_path
                self._save_tasks()

    def list_tasks(self) -> List[dict]:
        """
        列出所有任务

        Returns:
            任务列表（按创建时间倒序）
        """
        with self.lock:
            tasks = list(self.tasks.values())
            # 按创建时间倒序排序
            tasks.sort(key=lambda x: x['created_at'], reverse=True)
            return tasks

    def _generate_job_id(self) -> str:
        """
        生成唯一的任务 ID

        格式：aka-{mmddhhmm}-{seq}
        例如：aka-12221430-01

        Returns:
            job_id
        """
        now = datetime.now()
        base_id = f"aka-{now.strftime('%m%d%H%M')}"

        # 如果同一分钟内有多个任务，添加序号
        seq = 1
        job_id = base_id
        while job_id in self.tasks:
            job_id = f"{base_id}-{seq:02d}"
            seq += 1

        return job_id

    def _load_tasks(self):
        """从文件加载任务"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # 非空文件
                        self.tasks = json.loads(content)
                    else:  # 空文件
                        self.tasks = {}
            except (json.JSONDecodeError, IOError):
                # 文件损坏或无法读取，初始化为空
                self.tasks = {}
        else:
            self.tasks = {}

    def _save_tasks(self):
        """保存任务到文件"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except IOError as e:
            # 保存失败不应中断程序，记录错误
            print(f"警告：任务保存失败 - {e}")
