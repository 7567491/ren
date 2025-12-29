#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TDD测试用例：验证手机端前端问题
测试前后端集成，识别根本原因
"""

import pytest
import requests
import json
from pathlib import Path

# 测试配置
API_BASE_URL = "http://localhost:18000"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


class TestBackendAPIIntegration:
    """测试后端API集成问题"""

    def test_backend_accepts_wavespeed_api_key(self):
        """
        测试1：验证后端是否接受wavespeed_api_key参数

        预期：后端应该接受并处理wavespeed_api_key
        实际：后端JobCreateRequest模型缺少该字段
        """
        # 构造前端实际发送的请求体
        request_data = {
            "topic": "测试主题",
            "preset_name": "科技",
            "num_shots": 3,
            "shot_duration": 5,
            "resolution": "480p",
            "llm_provider": 1,
            "image_model": 4,
            "video_model": 1,
            "voice": 1,
            "concurrent_workers": 3,
            "wavespeed_api_key": "test-api-key-12345"  # 关键参数
        }

        # 发送请求
        response = requests.post(
            f"{API_BASE_URL}/api/jobs",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )

        print(f"\n状态码: {response.status_code}")
        print(f"响应体: {response.text[:500]}")

        # 验证
        assert response.status_code in [200, 201], \
            f"后端应该接受请求，实际状态码: {response.status_code}"

        # 检查是否有任务创建
        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data, "响应应该包含job_id"
            print(f"✅ 任务创建成功: {data['job_id']}")
        else:
            pytest.fail(f"后端拒绝请求: {response.text}")

    def test_backend_returns_proper_error_for_invalid_request(self):
        """
        测试2：验证后端对无效请求的错误处理

        预期：返回清晰的错误消息
        """
        request_data = {
            "topic": "",  # 空主题
            "num_shots": 100,  # 超出范围
            "resolution": "invalid"  # 无效分辨率
        }

        response = requests.post(
            f"{API_BASE_URL}/api/jobs",
            json=request_data
        )

        print(f"\n状态码: {response.status_code}")
        print(f"错误消息: {response.text[:500]}")

        # 应该返回4xx错误
        assert response.status_code >= 400, \
            "后端应该拒绝无效请求"

    def test_cors_headers_present(self):
        """
        测试3：验证CORS头是否正确配置（移动端跨域问题）

        预期：OPTIONS请求应该返回正确的CORS头
        """
        response = requests.options(
            f"{API_BASE_URL}/api/jobs",
            headers={
                "Origin": "http://mobile-device:8080",
                "Access-Control-Request-Method": "POST"
            }
        )

        print(f"\n状态码: {response.status_code}")
        print(f"CORS头: {dict(response.headers)}")

        # 验证CORS头
        assert "access-control-allow-origin" in response.headers, \
            "缺少CORS头"
        assert response.headers["access-control-allow-origin"] == "*", \
            f"CORS配置错误: {response.headers['access-control-allow-origin']}"


class TestFrontendConfiguration:
    """测试前端配置问题"""

    def test_api_base_configuration(self):
        """
        测试4：检查前端API_BASE配置

        预期：应该有明确的后端地址或环境配置
        实际：API_BASE为空字符串，依赖nginx
        """
        index_file = FRONTEND_DIR / "index.html"
        assert index_file.exists(), "前端文件不存在"

        content = index_file.read_text(encoding='utf-8')

        # 检查API_BASE配置
        assert "const API_BASE = '';" in content, \
            "API_BASE应该被明确定义"

        # 检查是否有注释说明
        if "nginx代理" in content:
            print("⚠️  警告：前端依赖nginx代理，移动端可能无法访问")

        # 建议：应该支持环境变量或配置文件
        print("\n建议：添加环境变量支持，如：")
        print("const API_BASE = window.ENV?.API_BASE || 'http://localhost:18000';")

    def test_error_handling_in_frontend(self):
        """
        测试5：检查前端错误处理

        预期：应该有console.error输出和UI错误提示
        实际：只有alert()，移动端可能被拦截
        """
        index_file = FRONTEND_DIR / "index.html"
        content = index_file.read_text(encoding='utf-8')

        # 检查是否有console.error
        has_console_error = "console.error" in content
        has_alert = "alert(" in content

        print(f"\n是否使用console.error: {has_console_error}")
        print(f"是否使用alert: {has_alert}")

        if not has_console_error:
            print("⚠️  警告：缺少console.error，调试困难")

        if has_alert and not has_console_error:
            print("⚠️  警告：仅使用alert()，移动端可能无法看到错误")


class TestMobileCompatibility:
    """测试移动端兼容性"""

    def test_responsive_design(self):
        """
        测试6：检查响应式设计

        预期：应该有移动端适配
        """
        index_file = FRONTEND_DIR / "index.html"
        content = index_file.read_text(encoding='utf-8')

        # 检查viewport meta标签
        assert 'name="viewport"' in content, \
            "缺少viewport meta标签"

        # 检查媒体查询
        has_media_queries = "@media" in content
        print(f"\n是否有媒体查询: {has_media_queries}")

        if has_media_queries:
            print("✅ 前端支持响应式设计")

    def test_touch_event_support(self):
        """
        测试7：检查移动端触摸事件

        预期：按钮应该支持触摸事件
        """
        index_file = FRONTEND_DIR / "index.html"
        content = index_file.read_text(encoding='utf-8')

        # 检查是否有触摸事件优化
        has_touch_action = "touch-action" in content or "ontouchstart" in content

        print(f"\n是否有触摸事件优化: {has_touch_action}")

        if not has_touch_action:
            print("ℹ️  建议：添加触摸事件优化，如 touch-action: manipulation")


def test_integration_scenario():
    """
    测试8：端到端集成测试
    模拟手机端用户点击"开始生成"的完整流程
    """
    print("\n" + "="*60)
    print("模拟手机端用户操作流程")
    print("="*60)

    # 步骤1：用户填写表单
    print("\n步骤1: 用户填写表单")
    form_data = {
        "topic": "一个银行客户经理遇到问题",
        "preset_name": "3D",
        "num_shots": 3,
        "shot_duration": 5,
        "resolution": "480p",
        "llm_provider": 1,
        "image_model": 4,
        "video_model": 1,
        "voice": 1,
        "concurrent_workers": 3,
        "wavespeed_api_key": "sk-test-123456"
    }
    print(f"表单数据: {json.dumps(form_data, indent=2, ensure_ascii=False)}")

    # 步骤2：发送POST请求（模拟fetch）
    print("\n步骤2: 发送API请求")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/jobs",
            json=form_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )

        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应体: {response.text[:500]}")

        # 步骤3：检查响应
        if response.status_code == 200:
            data = response.json()
            job_id = data.get("job_id")
            print(f"\n✅ 任务创建成功！Job ID: {job_id}")

            # 步骤4：轮询任务状态（模拟前端轮询）
            print("\n步骤4: 轮询任务状态")
            status_response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id}")
            print(f"任务状态: {status_response.json()}")

            # 步骤5：获取日志
            print("\n步骤5: 获取任务日志")
            log_response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id}/log")
            log_data = log_response.json()
            print(f"日志行数: {log_data.get('total_lines', 0)}")

            if log_data.get('lines'):
                print("前3行日志:")
                for line in log_data['lines'][:3]:
                    print(f"  {line}")
        else:
            print(f"\n❌ 任务创建失败: {response.text}")
            pytest.fail(f"API请求失败: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到后端服务器")
        print(f"请确保API服务器运行在 {API_BASE_URL}")
        pytest.skip("后端服务器未运行")

    except requests.exceptions.Timeout:
        print("\n❌ 请求超时")
        pytest.fail("API请求超时")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
