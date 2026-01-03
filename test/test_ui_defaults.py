#!/usr/bin/env python3
"""UI默认值测试用例 - TDD测试

测试前端界面与 user.yaml 的默认值配置：
1. 前端需定义10个包含“Akamai推理云”的主题模板，textarea 默认值与第一个模板一致
2. 分辨率默认480p
3. 并发线程默认3
"""

import re
from pathlib import Path


def test_frontend_default_topic():
    """测试前端默认主题与随机主题池"""
    html_file = Path(__file__).parent.parent / 'frontend' / 'index.html'
    content = html_file.read_text(encoding='utf-8')

    topic_pattern = r'<textarea[^>]*id="topic"[^>]*>([^<]*)</textarea>'
    match = re.search(topic_pattern, content)
    assert match is not None, "未找到 topic 输入框"
    default_text = match.group(1).strip()

    suffix_match = re.search(r"const PRESET_TOPIC_SUFFIX\s*=\s*'([^']+)';", content)
    variants_match = re.search(r"const PRESET_TOPIC_VARIANTS\s*=\s*\[(.*?)\];", content, re.DOTALL)
    assert suffix_match, "未找到 PRESET_TOPIC_SUFFIX"
    assert variants_match, "未找到 PRESET_TOPIC_VARIANTS"

    suffix = suffix_match.group(1)
    variants = re.findall(r"'([^']+)'", variants_match.group(1))
    assert len(variants) == 10, f"主题模板数量应为10，当前为{len(variants)}"

    topics = [variant + suffix for variant in variants]
    assert default_text == topics[0], "textarea 默认值应与首个主题模板一致"
    assert all('Akamai推理云' in topic for topic in topics), "所有主题都需包含“Akamai推理云”"
    print("✓ 默认主题与随机主题池配置测试通过")


def test_frontend_default_resolution():
    """测试前端默认分辨率为480p"""
    html_file = Path(__file__).parent.parent / 'frontend' / 'index.html'
    content = html_file.read_text(encoding='utf-8')

    # 查找 resolution 选择框中的默认选项
    # 匹配所有 resolution 的 option 标签
    resolution_section = re.search(r'<select[^>]*id="resolution"[^>]*>(.*?)</select>', content, re.DOTALL)

    assert resolution_section is not None, "未找到 resolution 选择框"

    # 检查480p是否被设置为selected
    options = resolution_section.group(1)

    # 480p 应该有 selected 属性
    assert 'value="480p"' in options, "未找到480p选项"

    # 查找默认选中的选项
    selected_pattern = r'<option[^>]*selected[^>]*>([^<]*)</option>'
    selected_match = re.search(selected_pattern, options)

    if selected_match:
        selected_text = selected_match.group(1)
        assert '480p' in selected_text, f"默认选中的不是480p，而是: {selected_text}"
    else:
        # 如果没有明确的 selected，检查第一个选项是否是480p
        first_option = re.search(r'<option[^>]*value="([^"]*)"', options)
        assert first_option and first_option.group(1) == '480p', "默认选项应该是480p"

    print("✓ 默认分辨率480p测试通过")


def test_frontend_default_concurrent_workers():
    """测试前端默认并发线程数为3"""
    html_file = Path(__file__).parent.parent / 'frontend' / 'index.html'
    content = html_file.read_text(encoding='utf-8')

    # 查找 concurrent_workers 输入框的 value 属性
    pattern = r'<input[^>]*id="concurrent_workers"[^>]*value="(\d+)"[^>]*>'
    match = re.search(pattern, content)

    assert match is not None, "未找到 concurrent_workers 输入框"

    default_value = int(match.group(1))
    expected_value = 3

    assert default_value == expected_value, f"默认并发线程数不匹配。期望: {expected_value}, 实际: {default_value}"
    print("✓ 默认并发线程数3测试通过")


def test_video_model_in_collapsed_section():
    """测试视频模型选择是否在折叠区域内"""
    html_file = Path(__file__).parent.parent / 'frontend' / 'index.html'
    content = html_file.read_text(encoding='utf-8')

    # 查找视频模型选择框
    video_model_pattern = r'<select[^>]*id="video_model"[^>]*>'
    match = re.search(video_model_pattern, content)

    assert match is not None, "未找到 video_model 选择框"

    # 获取视频模型选择框之前的内容
    before_video_model = content[:match.start()]

    # 检查它是否在 accordion-body 内
    # 通过检查最近的一个 accordion-body 开始标签
    accordion_body_pattern = r'<div class="accordion-body">'
    last_accordion_body = before_video_model.rfind(accordion_body_pattern)

    assert last_accordion_body != -1, "视频模型选择框不在折叠区域内"

    # 确认这个 accordion 默认是关闭的（没有 open class）
    # 查找包含视频模型的 accordion-item
    accordion_item_start = before_video_model.rfind('<div class="accordion-item')
    accordion_item_text = content[accordion_item_start:accordion_item_start+100]

    # 默认应该不包含 'open' class（折叠状态）
    assert 'accordion-item open' not in accordion_item_text, "包含视频模型的折叠区域应该默认关闭"

    print("✓ 视频模型在折叠区域测试通过")


def test_user_yaml_defaults():
    """测试 user.yaml 的默认配置"""
    yaml_file = Path(__file__).parent.parent / 'user.yaml'
    content = yaml_file.read_text(encoding='utf-8')

    # 检查关键配置
    assert 'resolution: 1' in content, "user.yaml 中分辨率应该为 1 (480p)"
    assert 'concurrent_workers: 3' in content, "user.yaml 中并发线程数应该为 3"
    assert 'Akamai推理云' in content, "user.yaml 中应包含默认主题文本"

    print("✓ user.yaml 默认配置测试通过")


if __name__ == '__main__':
    print("=" * 60)
    print("运行 UI 默认值测试...")
    print("=" * 60)

    try:
        test_frontend_default_topic()
        test_frontend_default_resolution()
        test_frontend_default_concurrent_workers()
        test_video_model_in_collapsed_section()
        test_user_yaml_defaults()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"❌ 测试失败: {e}")
        print("=" * 60)
        exit(1)
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 测试错误: {e}")
        print("=" * 60)
        exit(1)
