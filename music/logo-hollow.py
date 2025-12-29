#!/usr/bin/env python3
"""
Logo镂空处理脚本
功能：去除背景、添加描边、创建镂空效果
"""

from PIL import Image, ImageDraw, ImageFilter, ImageOps
import os

def remove_white_background(image_path, output_path, threshold=240):
    """去除白色背景，生成透明PNG"""
    img = Image.open(image_path).convert("RGBA")
    data = img.getdata()

    new_data = []
    for item in data:
        # 如果接近白色，设为透明
        if item[0] > threshold and item[1] > threshold and item[2] > threshold:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"✓ 已保存透明背景版本: {output_path}")
    return img

def add_outline(image_path, output_path, outline_width=3, outline_color=(255, 255, 255)):
    """添加描边效果"""
    img = Image.open(image_path).convert("RGBA")

    # 创建描边层
    outline = Image.new('RGBA', (img.width + outline_width*2, img.height + outline_width*2), (0, 0, 0, 0))

    # 在多个位置粘贴原图创建描边效果
    for x in range(-outline_width, outline_width+1):
        for y in range(-outline_width, outline_width+1):
            if x*x + y*y <= outline_width*outline_width:
                temp = Image.new('RGBA', outline.size, (0, 0, 0, 0))
                temp.paste(img, (outline_width+x, outline_width+y))
                # 将非透明区域改为描边颜色
                pixels = temp.load()
                for i in range(temp.width):
                    for j in range(temp.height):
                        if pixels[i, j][3] > 0:
                            pixels[i, j] = (*outline_color, 255)
                outline = Image.alpha_composite(outline, temp)

    # 在描边上方粘贴原图
    outline.paste(img, (outline_width, outline_width), img)
    outline.save(output_path, "PNG")
    print(f"✓ 已保存描边版本: {output_path}")
    return outline

def create_silhouette(image_path, output_path, color=(0, 0, 0)):
    """创建剪影效果"""
    img = Image.open(image_path).convert("RGBA")
    data = img.getdata()

    new_data = []
    for item in data:
        # 保持透明度，但将非透明部分改为指定颜色
        if item[3] > 0:
            new_data.append((*color, item[3]))
        else:
            new_data.append((255, 255, 255, 0))

    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"✓ 已保存剪影版本: {output_path}")
    return img

def create_hollow_effect(image_path, output_path, border_width=5):
    """创建镂空边框效果（只保留边缘）"""
    img = Image.open(image_path).convert("RGBA")

    # 获取边缘
    edges = img.filter(ImageFilter.FIND_EDGES)

    # 增强边缘
    edges = edges.filter(ImageFilter.MaxFilter(border_width))

    edges.save(output_path, "PNG")
    print(f"✓ 已保存镂空边框版本: {output_path}")
    return edges

def main():
    # 输入输出路径
    input_logo = "resource/logo/aka.jpg"
    output_dir = "resource/logo"

    if not os.path.exists(input_logo):
        print(f"❌ 找不到logo文件: {input_logo}")
        return

    os.makedirs(output_dir, exist_ok=True)

    print("=" * 50)
    print("Logo镂空处理开始")
    print("=" * 50)

    # 1. 去除白色背景
    transparent = os.path.join(output_dir, "aka_transparent.png")
    remove_white_background(input_logo, transparent)

    # 2. 添加白色描边（用于深色背景）
    outline_white = os.path.join(output_dir, "aka_outline_white.png")
    add_outline(transparent, outline_white, outline_width=4, outline_color=(255, 255, 255))

    # 3. 添加黑色描边（用于浅色背景）
    outline_black = os.path.join(output_dir, "aka_outline_black.png")
    add_outline(transparent, outline_black, outline_width=4, outline_color=(0, 0, 0))

    # 4. 创建黑色剪影
    silhouette = os.path.join(output_dir, "aka_silhouette.png")
    create_silhouette(transparent, silhouette, color=(0, 0, 0))

    # 5. 创建镂空边框效果
    hollow = os.path.join(output_dir, "aka_hollow_border.png")
    create_hollow_effect(transparent, hollow, border_width=3)

    print("=" * 50)
    print("✅ 所有版本生成完成！")
    print("=" * 50)
    print(f"\n生成的文件：")
    print(f"1. {transparent} - 透明背景版")
    print(f"2. {outline_white} - 白色描边版（适合深色背景）")
    print(f"3. {outline_black} - 黑色描边版（适合浅色背景）")
    print(f"4. {silhouette} - 黑色剪影版")
    print(f"5. {hollow} - 镂空边框版")

if __name__ == "__main__":
    main()
