#!/usr/bin/env python3
"""
批量去除图片背景脚本
使用rembg进行AI抠图
"""

from rembg import remove
from PIL import Image
import os
import glob

# 配置
input_dir = './resource/pic'
output_dir = './resource/pic/nobg'  # 去背景后的图片保存目录

# 创建输出目录
os.makedirs(output_dir, exist_ok=True)

# 需要处理的角色图片
character_images = [
    'sakuragi.jpg',
    'guanyu.jpg',
    'huanzhu.jpg',
    'mickey.jpg',
    'leon.jpg',
    'terminator.jpg',
    'leijun.jpg',
    'tom_leighton.jpg',
    'einstein.jpg',
    'musk.jpg'
]

print("开始批量去除背景...\n")
print("模型首次运行会自动下载（约176MB），请稍候...\n")

success_count = 0
total_count = len(character_images)

for img_name in character_images:
    input_path = os.path.join(input_dir, img_name)

    # 输出为PNG格式（支持透明背景）
    output_name = os.path.splitext(img_name)[0] + '.png'
    output_path = os.path.join(output_dir, output_name)

    if not os.path.exists(input_path):
        print(f"⚠️  {img_name} - 文件不存在，跳过")
        continue

    print(f"处理中: {img_name}...", end=' ')

    try:
        # 读取原图
        with open(input_path, 'rb') as input_file:
            input_data = input_file.read()

        # AI去背景
        output_data = remove(input_data)

        # 保存为PNG
        with open(output_path, 'wb') as output_file:
            output_file.write(output_data)

        # 获取文件大小
        size_kb = os.path.getsize(output_path) / 1024
        print(f"✓ 完成 ({size_kb:.1f}KB)")
        success_count += 1

    except Exception as e:
        print(f"✗ 失败: {str(e)}")

print(f"\n{'='*50}")
print(f"处理完成！成功: {success_count}/{total_count}")
print(f"去背景图片保存在: {output_dir}")
print(f"{'='*50}\n")

# 显示文件列表
print("生成的文件：")
for f in sorted(glob.glob(os.path.join(output_dir, '*.png'))):
    size_kb = os.path.getsize(f) / 1024
    print(f"  - {os.path.basename(f)} ({size_kb:.1f}KB)")
