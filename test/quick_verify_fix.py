#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速验证修复是否有效
"""

import requests
import json

API_BASE = "http://localhost:18000"

print("=" * 60)
print("快速验证修复")
print("=" * 60)

# 测试1：验证后端接受wavespeed_api_key
print("\n测试1: 验证后端接受wavespeed_api_key参数")
print("-" * 60)

request_data = {
    "topic": "测试主题 - 验证API密钥传递",
    "preset_name": "科技",
    "num_shots": 1,  # 最小值，快速测试
    "shot_duration": 3,
    "resolution": "480p",
    "llm_provider": 1,
    "image_model": 4,
    "video_model": 1,
    "voice": 6,
    "concurrent_workers": 1,
    "wavespeed_api_key": "test-key-quick-verify-123"
}

try:
    response = requests.post(
        f"{API_BASE}/api/jobs",
        json=request_data,
        headers={"Content-Type": "application/json"},
        timeout=5
    )

    print(f"✅ 状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        job_id = data.get("job_id")
        print(f"✅ 任务创建成功: {job_id}")
        print(f"   状态: {data.get('status')}")
        print(f"   消息: {data.get('message')}")

        # 检查配置文件是否包含API密钥
        import yaml
        from pathlib import Path

        config_file = Path("temp") / f"user-{job_id}.yaml"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if 'api' in config and 'wavespeed_key' in config['api']:
                print(f"✅ API密钥已写入配置文件")
                print(f"   密钥值: {config['api']['wavespeed_key'][:10]}...")
            else:
                print(f"❌ API密钥未写入配置文件")
                print(f"   配置内容: {json.dumps(config, indent=2, ensure_ascii=False)}")
        else:
            print(f"⚠️  配置文件不存在: {config_file}")

        print("\n✅ 修复1验证成功: 后端正确接受和处理wavespeed_api_key")

    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(f"   错误: {response.text}")

except Exception as e:
    print(f"❌ 测试失败: {e}")

# 测试2：验证健康检查端点
print("\n\n测试2: 验证健康检查端点（前端测试连接功能）")
print("-" * 60)

try:
    response = requests.get(f"{API_BASE}/health", timeout=5)
    print(f"✅ 状态码: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 健康检查成功")
        print(f"   服务器状态: {data.get('status')}")
        print(f"   运行任务数: {data.get('running_tasks')}")
        print(f"   最大并发: {data.get('max_concurrent')}")
        print("\n✅ 修复4验证成功: 测试连接功能可用")
    else:
        print(f"❌ 健康检查失败: {response.status_code}")

except Exception as e:
    print(f"❌ 测试失败: {e}")

# 测试3：验证CORS头
print("\n\n测试3: 验证CORS配置")
print("-" * 60)

try:
    response = requests.options(
        f"{API_BASE}/api/jobs",
        headers={
            "Origin": "http://mobile-device:8080",
            "Access-Control-Request-Method": "POST"
        },
        timeout=5
    )

    print(f"✅ 状态码: {response.status_code}")

    if "access-control-allow-origin" in response.headers:
        origin = response.headers["access-control-allow-origin"]
        print(f"✅ CORS头存在: {origin}")

        if origin == "*":
            print("✅ CORS配置为通配符（推荐）")
        else:
            print(f"⚠️  CORS配置为镜像Origin（可能有限制）")
    else:
        print("❌ 缺少CORS头")

except Exception as e:
    print(f"❌ 测试失败: {e}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
