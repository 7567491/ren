#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API限流管理器
支持每分钟和每天的请求频率控制
"""

import time
import threading
from typing import Optional


class RateLimiter:
    """
    API限流器，控制API请求频率

    支持:
    - 每分钟请求数限制 (max_requests_per_minute)
    - 每天请求数限制 (max_requests_per_day)
    - 自动计算最小请求间隔
    - 线程安全
    """

    def __init__(
        self,
        max_requests_per_minute: Optional[int] = None,
        max_requests_per_day: Optional[int] = None,
        name: str = "API"
    ):
        """
        初始化限流器

        Args:
            max_requests_per_minute: 每分钟最大请求数，None表示不限制
            max_requests_per_day: 每天最大请求数，None表示不限制
            name: 限流器名称（用于日志输出）
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_day = max_requests_per_day
        self.name = name
        self.request_times = []
        self.lock = threading.Lock()

        # 计算最小请求间隔（秒）
        if max_requests_per_minute and max_requests_per_minute > 0:
            self.min_delay = 60.0 / max_requests_per_minute
        else:
            self.min_delay = 0

    def acquire(self):
        """
        获取API调用权限

        如果超过限流阈值，会自动等待直到可以调用
        线程安全，可在多线程环境中使用
        """
        # 如果没有设置任何限制，直接返回
        if not self.max_requests_per_minute and not self.max_requests_per_day:
            return

        with self.lock:
            current_time = time.time()

            # 清理过期的请求记录
            if self.max_requests_per_day:
                # 保留最近24小时的记录
                self.request_times = [t for t in self.request_times if current_time - t < 86400]
            elif self.max_requests_per_minute:
                # 只保留最近60秒的记录
                self.request_times = [t for t in self.request_times if current_time - t < 60]

            # 检查每天限制
            if self.max_requests_per_day and self.max_requests_per_day > 0:
                daily_requests = [t for t in self.request_times if current_time - t < 86400]

                if len(daily_requests) >= self.max_requests_per_day:
                    oldest_request = daily_requests[0]
                    wait_time = 86400 - (current_time - oldest_request)

                    if wait_time > 0:
                        hours = wait_time / 3600
                        print(f"⏰ [{self.name}] 达到每日限制 ({self.max_requests_per_day}次/天)，等待 {hours:.1f} 小时...")
                        time.sleep(wait_time)
                        current_time = time.time()
                        # 重新清理
                        self.request_times = [t for t in self.request_times if current_time - t < 86400]

            # 检查每分钟限制
            if self.max_requests_per_minute and self.max_requests_per_minute > 0:
                minute_requests = [t for t in self.request_times if current_time - t < 60]

                if len(minute_requests) >= self.max_requests_per_minute:
                    oldest_request = minute_requests[0]
                    wait_time = 60 - (current_time - oldest_request)

                    if wait_time > 0:
                        print(f"⏰ [{self.name}] 达到每分钟限制 ({self.max_requests_per_minute}次/分)，等待 {wait_time:.1f} 秒...")
                        time.sleep(wait_time)
                        current_time = time.time()
                        # 重新清理
                        if self.max_requests_per_day:
                            self.request_times = [t for t in self.request_times if current_time - t < 86400]
                        else:
                            self.request_times = [t for t in self.request_times if current_time - t < 60]

                # 确保最小请求间隔
                if self.request_times and self.min_delay > 0:
                    last_request = self.request_times[-1]
                    time_since_last = current_time - last_request

                    if time_since_last < self.min_delay:
                        wait_time = self.min_delay - time_since_last
                        time.sleep(wait_time)
                        current_time = time.time()

            # 记录本次请求
            self.request_times.append(current_time)

    def get_stats(self) -> dict:
        """
        获取限流统计信息

        Returns:
            dict: 包含当前请求统计的字典
        """
        with self.lock:
            current_time = time.time()
            minute_requests = [t for t in self.request_times if current_time - t < 60]
            daily_requests = [t for t in self.request_times if current_time - t < 86400]

            return {
                "name": self.name,
                "requests_last_minute": len(minute_requests),
                "requests_last_day": len(daily_requests),
                "max_per_minute": self.max_requests_per_minute,
                "max_per_day": self.max_requests_per_day,
                "min_delay": self.min_delay
            }
