#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载测试生成的所有图像和视频到本地
"""

import os
import json
import requests
from urllib.parse import urlparse
from pathlib import Path

def download_file(url: str, save_dir: str, prefix: str = "") -> str:
    """下载文件到指定目录"""
    try:
        # 解析文件扩展名
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix or ".mp4"

        # 生成本地文件名
        filename = f"{prefix}{ext}"
        filepath = os.path.join(save_dir, filename)

        # 如果已存在，跳过
        if os.path.exists(filepath):
            print(f"⏭️  已存在: {filename}")
            return filepath

        # 下载文件
        print(f"⬇️  下载中: {filename}...")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        # 保存文件
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # 获取文件大小
        file_size = os.path.getsize(filepath)
        size_mb = file_size / (1024 * 1024)

        print(f"✅ 完成: {filename} ({size_mb:.2f}MB)")
        return filepath

    except Exception as e:
        print(f"❌ 下载失败: {url}")
        print(f"   错误: {e}")
        return None

def process_results_file(json_file: str, output_dir: str):
    """处理结果JSON文件并下载所有媒体"""
    print(f"\n{'='*60}")
    print(f"处理文件: {json_file}")
    print(f"{'='*60}")

    # 读取JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 统计信息
    total_files = 0
    downloaded_files = 0

    # 处理所有测试结果
    all_tests = []

    # 检查不同的数据结构
    if 'text_to_image_tests' in data:
        all_tests.extend(data.get('text_to_image_tests', []))
    if 'image_to_video_tests' in data:
        all_tests.extend(data.get('image_to_video_tests', []))
    if 'tests' in data:
        all_tests.extend(data.get('tests', []))

    # 下载每个测试的输出
    for i, test in enumerate(all_tests, 1):
        if test.get('status') != 'success':
            continue

        outputs = test.get('outputs', [])
        if not outputs:
            continue

        test_name = test.get('test_name', f'test_{i}')
        model = test.get('model', 'unknown')

        print(f"\n📦 {i}. {test_name}")
        print(f"   模型: {model}")

        for j, url in enumerate(outputs, 1):
            total_files += 1

            # 生成文件前缀
            # 清理文件名中的特殊字符
            safe_name = test_name.replace(' ', '_').replace('/', '-')
            prefix = f"{i:02d}_{safe_name}_{j}"

            # 下载文件
            result = download_file(url, output_dir, prefix)
            if result:
                downloaded_files += 1

    print(f"\n{'='*60}")
    print(f"✅ 下载完成")
    print(f"   总文件数: {total_files}")
    print(f"   下载成功: {downloaded_files}")
    print(f"   保存位置: {output_dir}")
    print(f"{'='*60}")

def main():
    """主函数"""
    print("🎬 开始下载所有测试生成的图像和视频\n")

    # 定义输出目录
    output_base = "./test/outputs"

    # 处理所有结果文件
    result_files = [
        ("./test/test-wave-results.json", f"{output_base}/initial-test"),
        ("./test/test-extended-results.json", f"{output_base}/extended-test")
    ]

    total_downloaded = 0

    for json_file, output_dir in result_files:
        if os.path.exists(json_file):
            process_results_file(json_file, output_dir)

            # 统计下载的文件
            if os.path.exists(output_dir):
                files = os.listdir(output_dir)
                total_downloaded += len(files)
        else:
            print(f"⚠️  文件不存在: {json_file}")

    print(f"\n🎉 所有任务完成！")
    print(f"   总下载文件: {total_downloaded}个")
    print(f"   保存目录: {output_base}/")

    # 显示目录结构
    print(f"\n📁 目录结构:")
    os.system(f"tree {output_base} 2>/dev/null || find {output_base} -type f 2>/dev/null")

if __name__ == "__main__":
    main()
