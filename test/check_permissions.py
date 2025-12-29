#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权限检查脚本 - 验证系统关键文件和目录的可访问性
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

# ANSI颜色代码
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

class PermissionChecker:
    def __init__(self, base_dir: str = '/home/wave'):
        self.base_dir = Path(base_dir)
        self.errors = []
        self.warnings = []

    def check_file_readable(self, file_path: Path, critical: bool = True) -> bool:
        """检查文件是否可读"""
        try:
            if not file_path.exists():
                msg = f"文件不存在: {file_path}"
                if critical:
                    self.errors.append(msg)
                    return False
                else:
                    self.warnings.append(msg)
                    return True

            if not os.access(file_path, os.R_OK):
                msg = f"无读取权限: {file_path}"
                if critical:
                    self.errors.append(msg)
                else:
                    self.warnings.append(msg)
                return False

            return True
        except Exception as e:
            msg = f"检查失败 {file_path}: {e}"
            self.errors.append(msg)
            return False

    def check_dir_writable(self, dir_path: Path, critical: bool = True) -> bool:
        """检查目录是否可写"""
        try:
            if not dir_path.exists():
                msg = f"目录不存在: {dir_path}"
                if critical:
                    self.errors.append(msg)
                else:
                    self.warnings.append(msg)
                return False

            test_file = dir_path / '.write_test_tmp'
            try:
                test_file.touch()
                test_file.unlink()
                return True
            except PermissionError:
                msg = f"无写入权限: {dir_path}"
                if critical:
                    self.errors.append(msg)
                else:
                    self.warnings.append(msg)
                return False
        except Exception as e:
            msg = f"检查失败 {dir_path}: {e}"
            self.errors.append(msg)
            return False

    def run_checks(self) -> bool:
        """运行所有检查"""
        print(f"{'='*60}")
        print(f"权限检查工具 - 基础目录: {self.base_dir}")
        print(f"当前用户: {os.getenv('USER')} (UID: {os.getuid()})")
        print(f"{'='*60}\n")

        # 关键配置文件
        print("【1. 检查配置文件】")
        config_files = [
            (self.base_dir / '.env', True),
            (self.base_dir / 'config.yaml', True),
            (self.base_dir / 'user.yaml', False),  # user.yaml可能不存在
        ]

        for file_path, critical in config_files:
            result = self.check_file_readable(file_path, critical)
            status = f"{GREEN}✓{RESET}" if result else f"{RED}✗{RESET}"
            print(f"  {status} {file_path.name}")

        # Python可执行脚本
        print("\n【2. 检查Python脚本】")
        script_files = [
            self.base_dir / 'py' / 'ad-back.py',
            self.base_dir / 'py' / 'ad-aka.py',
        ]

        for file_path in script_files:
            readable = self.check_file_readable(file_path, True)
            executable = os.access(file_path, os.X_OK) if file_path.exists() else False

            if readable and executable:
                status = f"{GREEN}✓{RESET}"
            elif readable:
                status = f"{YELLOW}⚠{RESET}"
                self.warnings.append(f"可读但不可执行: {file_path}")
            else:
                status = f"{RED}✗{RESET}"

            print(f"  {status} {file_path.name} (R:{readable}, X:{executable})")

        # 工作目录
        print("\n【3. 检查工作目录】")
        work_dirs = [
            (self.base_dir / 'output', True),
            (self.base_dir / 'temp', True),
            (self.base_dir / 'resource', False),
        ]

        for dir_path, critical in work_dirs:
            result = self.check_dir_writable(dir_path, critical)
            status = f"{GREEN}✓{RESET}" if result else f"{RED}✗{RESET}"
            print(f"  {status} {dir_path.name}/")

        # 输出结果
        print(f"\n{'='*60}")

        if self.errors:
            print(f"{RED}发现 {len(self.errors)} 个错误:{RESET}")
            for error in self.errors:
                print(f"  ✗ {error}")

        if self.warnings:
            print(f"\n{YELLOW}发现 {len(self.warnings)} 个警告:{RESET}")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        if not self.errors and not self.warnings:
            print(f"{GREEN}✓ 所有权限检查通过！{RESET}")

        print(f"{'='*60}\n")

        return len(self.errors) == 0

def main():
    """主函数"""
    checker = PermissionChecker()

    if checker.run_checks():
        print(f"{GREEN}权限检查完成 - 系统就绪{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}权限检查失败 - 请修复上述错误{RESET}")
        sys.exit(1)

if __name__ == '__main__':
    main()
