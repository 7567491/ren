"""
手动测试进度追踪功能
"""
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from py.api_server import (
    calculate_progress_from_checkpoint,
    generate_progress_message,
    parse_checkpoint_file
)


def test_calculate_progress():
    """测试进度计算"""
    print("=" * 60)
    print("测试：进度计算")
    print("=" * 60)

    # 测试1：空checkpoint
    print("\n测试1：空checkpoint")
    checkpoint = {'completed_steps': []}
    progress = calculate_progress_from_checkpoint(checkpoint)
    print(f"  完成步骤: []")
    print(f"  进度: {progress} (期望: 0.0)")
    assert progress == 0.0, f"失败：期望0.0，得到{progress}"
    print("  ✅ 通过")

    # 测试2：只完成故事
    print("\n测试2：只完成故事生成")
    checkpoint = {'completed_steps': ['story']}
    progress = calculate_progress_from_checkpoint(checkpoint)
    print(f"  完成步骤: ['story']")
    print(f"  进度: {progress} (期望: 0.25)")
    assert progress == 0.25, f"失败：期望0.25，得到{progress}"
    print("  ✅ 通过")

    # 测试3：完成故事和图像
    print("\n测试3：完成故事和图像")
    checkpoint = {'completed_steps': ['story', 'images']}
    progress = calculate_progress_from_checkpoint(checkpoint)
    print(f"  完成步骤: ['story', 'images']")
    print(f"  进度: {progress} (期望: 0.5)")
    assert progress == 0.5, f"失败：期望0.5，得到{progress}"
    print("  ✅ 通过")

    # 测试4：完成三步
    print("\n测试4：完成前三步")
    checkpoint = {'completed_steps': ['story', 'images', 'videos']}
    progress = calculate_progress_from_checkpoint(checkpoint)
    print(f"  完成步骤: ['story', 'images', 'videos']")
    print(f"  进度: {progress} (期望: 0.75)")
    assert progress == 0.75, f"失败：期望0.75，得到{progress}"
    print("  ✅ 通过")

    # 测试5：全部完成
    print("\n测试5：全部完成")
    checkpoint = {
        'completed_steps': ['story', 'images', 'videos', 'composition']
    }
    progress = calculate_progress_from_checkpoint(checkpoint)
    print(f"  完成步骤: ['story', 'images', 'videos', 'composition']")
    print(f"  进度: {progress} (期望: 1.0)")
    assert progress == 1.0, f"失败：期望1.0，得到{progress}"
    print("  ✅ 通过")

    # 测试6：带有详细进度
    print("\n测试6：带有详细进度（正在生成图像）")
    checkpoint = {
        'completed_steps': ['story'],
        'images': {'completed': 3, 'total': 6},
        'videos': {'completed': 0, 'total': 6}
    }
    progress = calculate_progress_from_checkpoint(checkpoint, detailed=True)
    print(f"  完成步骤: ['story']")
    print(f"  图像进度: 3/6")
    print(f"  进度: {progress} (期望: 0.25 + 0.125 = 0.375)")
    assert 0.37 <= progress <= 0.38, f"失败：期望约0.375，得到{progress}"
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("✅ 所有进度计算测试通过！")
    print("=" * 60)


def test_generate_message():
    """测试消息生成"""
    print("\n" + "=" * 60)
    print("测试：进度消息生成")
    print("=" * 60)

    # 测试1：故事生成阶段
    print("\n测试1：故事生成阶段")
    checkpoint = {'completed_steps': []}
    message = generate_progress_message(checkpoint)
    print(f"  消息: {message}")
    assert '故事' in message or '脚本' in message
    print("  ✅ 通过")

    # 测试2：图像生成阶段
    print("\n测试2：图像生成阶段")
    checkpoint = {
        'completed_steps': ['story'],
        'images': {'completed': 3, 'total': 6}
    }
    message = generate_progress_message(checkpoint)
    print(f"  消息: {message}")
    assert '图像' in message and '3' in message
    print("  ✅ 通过")

    # 测试3：视频生成阶段
    print("\n测试3：视频生成阶段")
    checkpoint = {
        'completed_steps': ['story', 'images'],
        'videos': {'completed': 2, 'total': 6}
    }
    message = generate_progress_message(checkpoint)
    print(f"  消息: {message}")
    assert '视频' in message and '2' in message
    print("  ✅ 通过")

    # 测试4：合成阶段
    print("\n测试4：合成阶段")
    checkpoint = {
        'completed_steps': ['story', 'images', 'videos', 'composition']
    }
    message = generate_progress_message(checkpoint)
    print(f"  消息: {message}")
    assert '完成' in message or '合成' in message
    print("  ✅ 通过")

    print("\n" + "=" * 60)
    print("✅ 所有消息生成测试通过！")
    print("=" * 60)


def test_parse_checkpoint():
    """测试checkpoint文件解析"""
    print("\n" + "=" * 60)
    print("测试：checkpoint文件解析")
    print("=" * 60)

    # 测试实际的checkpoint文件
    checkpoint_file = Path('/home/wave/output/aka-12271701/00_checkpoint.json')

    if checkpoint_file.exists():
        print(f"\n测试：解析真实checkpoint文件")
        print(f"  文件: {checkpoint_file}")

        checkpoint = parse_checkpoint_file(checkpoint_file)
        if checkpoint:
            print(f"  ✅ 解析成功")
            print(f"  完成步骤: {checkpoint.get('completed_steps', [])}")

            progress = calculate_progress_from_checkpoint(checkpoint, detailed=True)
            message = generate_progress_message(checkpoint)

            print(f"  进度: {progress}")
            print(f"  消息: {message}")
        else:
            print(f"  ❌ 解析失败")
    else:
        print(f"\n跳过：checkpoint文件不存在 ({checkpoint_file})")

    print("\n" + "=" * 60)
    print("✅ checkpoint文件解析测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    try:
        test_calculate_progress()
        test_generate_message()
        test_parse_checkpoint()

        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 运行错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
