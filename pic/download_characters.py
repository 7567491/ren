#!/usr/bin/env python3
"""
自动下载角色照片脚本
使用Bing Images搜索（通过icrawler）- 比Google更稳定
"""

from icrawler.builtin import BingImageCrawler
import os
import shutil

# 定义角色和搜索关键词
characters = {
    'sakuragi': '灌篮高手 樱木花道',
    'guanyu': '三国演义 陆树铭 关羽',
    'huanzhu': '还珠格格 小燕子 赵薇',
    'mickey': 'Mickey Mouse Disney character',
    'leon': 'Leon Kennedy Resident Evil',
    'terminator': 'Terminator T-800 Arnold Schwarzenegger',
    'leijun': '雷军',
    'tom_leighton': 'Tom Leighton Akamai CEO',
    'einstein': 'Albert Einstein portrait',
    'musk': 'Elon Musk portrait'
}

temp_dir = './temp_downloads'
output_dir = './resource/pic'

os.makedirs(output_dir, exist_ok=True)

print("开始从Bing Images下载角色照片...\n")

for char_name, search_query in characters.items():
    print(f"正在下载: {char_name} ({search_query})")

    # 为每个角色创建临时目录
    char_temp_dir = os.path.join(temp_dir, char_name)

    try:
        # 下载3张图片供选择
        bing_crawler = BingImageCrawler(
            storage={'root_dir': char_temp_dir}
        )

        bing_crawler.crawl(
            keyword=search_query,
            max_num=3,
            min_size=(800, 800),  # 最小尺寸要求
            file_idx_offset=0
        )

        # 检查下载的图片
        if os.path.exists(char_temp_dir):
            files = sorted([f for f in os.listdir(char_temp_dir)
                          if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])

            if files:
                # 选择第一张
                source = os.path.join(char_temp_dir, files[0])
                ext = os.path.splitext(files[0])[1]
                dest = os.path.join(output_dir, f"{char_name}{ext}")
                shutil.copy2(source, dest)
                print(f"  ✓ 已保存: {dest}")
            else:
                print(f"  ✗ 未找到图片")
        else:
            print(f"  ✗ 下载失败")

    except Exception as e:
        print(f"  ✗ 错误: {str(e)}")

    print()

print(f"\n下载完成！图片保存在: {output_dir}")
print(f"临时文件保存在: {temp_dir}（可查看所有下载的图片）")
print("\n建议：检查图片质量，如需替换可从temp_downloads中选择其他图片")
