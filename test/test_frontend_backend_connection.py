#!/usr/bin/env python3
"""
测试前端与后端的连接
验证修复后的前端配置是否正确
"""

import requests
import sys
from pathlib import Path

# 后端API配置（应与frontend/config.js中的配置一致）
BACKEND_API = "http://139.162.52.158:18000"

def test_health_endpoint():
    """测试健康检查端点"""
    print("🔍 测试1: 健康检查端点")
    print(f"   URL: {BACKEND_API}/health")

    try:
        response = requests.get(f"{BACKEND_API}/health", timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 连接成功")
            print(f"   📊 服务器状态: {data.get('status')}")
            print(f"   🏃 运行任务数: {data.get('running_tasks', 0)}")
            return True
        else:
            print(f"   ❌ 失败: HTTP {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"   ❌ 连接失败: 无法连接到服务器")
        print(f"   💡 请确保后端服务正在运行: python3 py/api_server.py")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ 连接超时")
        return False
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return False

def test_jobs_endpoint():
    """测试任务列表端点"""
    print("\n🔍 测试2: 任务列表端点")
    print(f"   URL: {BACKEND_API}/api/jobs")

    try:
        response = requests.get(f"{BACKEND_API}/api/jobs", timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 连接成功")
            print(f"   📋 任务数量: {len(data.get('jobs', []))}")
            return True
        else:
            print(f"   ❌ 失败: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return False

def verify_config_js():
    """验证config.js配置文件"""
    print("\n🔍 测试3: 验证config.js配置")

    config_path = Path(__file__).parent.parent / "frontend" / "config.js"

    if not config_path.exists():
        print(f"   ❌ config.js 不存在: {config_path}")
        return False

    content = config_path.read_text()

    if BACKEND_API in content:
        print(f"   ✅ config.js 包含正确的后端API地址")
        print(f"   📍 API地址: {BACKEND_API}")
        return True
    else:
        print(f"   ❌ config.js 不包含正确的后端API地址")
        print(f"   预期: {BACKEND_API}")
        return False

def verify_index_html():
    """验证index.html是否正确引入config.js"""
    print("\n🔍 测试4: 验证index.html配置")

    index_path = Path(__file__).parent.parent / "frontend" / "index.html"

    if not index_path.exists():
        print(f"   ❌ index.html 不存在: {index_path}")
        return False

    content = index_path.read_text()

    # 检查是否引入了config.js
    if '<script src="config.js"></script>' in content:
        print(f"   ✅ 正确引入了config.js")
    else:
        print(f"   ❌ 未引入config.js")
        return False

    # 检查是否移除了用户配置后端API的界面
    if '后端API配置' in content or 'api_base_url' in content:
        print(f"   ⚠️  仍包含用户配置后端API的界面（可能有残留）")
        # 不算失败，只是警告
    else:
        print(f"   ✅ 已移除用户配置后端API的界面")

    # 检查是否使用了APP_CONFIG.API_BASE
    if 'APP_CONFIG.API_BASE' in content:
        print(f"   ✅ 正确使用了APP_CONFIG.API_BASE")
        return True
    else:
        print(f"   ❌ 未使用APP_CONFIG.API_BASE")
        return False

def main():
    print("="*60)
    print("🧪 前端与后端连接测试")
    print("="*60)

    results = []

    # 执行测试
    results.append(("健康检查", test_health_endpoint()))
    results.append(("任务列表", test_jobs_endpoint()))
    results.append(("config.js配置", verify_config_js()))
    results.append(("index.html配置", verify_index_html()))

    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)

    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {name}: {status}")

    # 总体评估
    all_passed = all(result[1] for result in results)

    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过！前端配置正确！")
        print("="*60)
        print("\n✨ 下一步操作：")
        print("   1. 在手机浏览器中访问: http://139.162.52.158/（如果有nginx配置）")
        print("   2. 或直接访问: frontend/index.html")
        print("   3. 点击'开始生成'测试完整流程")
        return 0
    else:
        print("❌ 部分测试失败，请检查配置")
        print("="*60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
