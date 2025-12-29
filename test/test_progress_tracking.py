"""
测试进度追踪功能
"""
import pytest
import json
import asyncio
from pathlib import Path
from py.api_server import calculate_progress_from_checkpoint


class TestProgressTracking:
    """进度追踪测试套件"""

    def test_calculate_progress_empty_checkpoint(self):
        """测试：空checkpoint返回0进度"""
        checkpoint = {'completed_steps': []}
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == 0.0

    def test_calculate_progress_story_only(self):
        """测试：只完成故事生成，进度应为0.25"""
        checkpoint = {'completed_steps': ['story']}
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == 0.25  # 1/4

    def test_calculate_progress_story_and_images(self):
        """测试：完成故事和图像，进度应为0.5"""
        checkpoint = {'completed_steps': ['story', 'images']}
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == 0.5  # 2/4

    def test_calculate_progress_all_but_composition(self):
        """测试：完成前三步，进度应为0.75"""
        checkpoint = {'completed_steps': ['story', 'images', 'videos']}
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == 0.75  # 3/4

    def test_calculate_progress_complete(self):
        """测试：全部完成，进度应为1.0"""
        checkpoint = {
            'completed_steps': ['story', 'images', 'videos', 'composition']
        }
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == 1.0  # 4/4

    def test_calculate_progress_with_details(self):
        """测试：带有详细信息的checkpoint"""
        checkpoint = {
            'completed_steps': ['story', 'images'],
            'images': {'completed': 3, 'total': 6},
            'videos': {'completed': 0, 'total': 6}
        }
        # 基础进度0.5 + 图像子进度0.5*(3/6) = 0.5 + 0.125 = 0.625
        progress = calculate_progress_from_checkpoint(checkpoint, detailed=True)
        assert 0.60 <= progress <= 0.65

    def test_calculate_progress_invalid_checkpoint(self):
        """测试：无效checkpoint返回0"""
        progress = calculate_progress_from_checkpoint({})
        assert progress == 0.0

    def test_calculate_progress_unknown_steps(self):
        """测试：包含未知步骤的checkpoint"""
        checkpoint = {
            'completed_steps': ['story', 'unknown_step', 'images']
        }
        # 应该只计数已知步骤: story, images
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == 0.5  # 2/4


class TestCheckpointParsing:
    """checkpoint文件解析测试"""

    def test_parse_valid_checkpoint_file(self, tmp_path):
        """测试：解析有效的checkpoint文件"""
        checkpoint_file = tmp_path / "00_checkpoint.json"
        checkpoint_data = {
            'completed_steps': ['story', 'images'],
            'timestamp': '2025-12-27T17:00:00'
        }

        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f)

        from py.api_server import parse_checkpoint_file
        result = parse_checkpoint_file(checkpoint_file)

        assert result is not None
        assert result['completed_steps'] == ['story', 'images']

    def test_parse_nonexistent_checkpoint_file(self, tmp_path):
        """测试：不存在的文件返回None"""
        checkpoint_file = tmp_path / "nonexistent.json"

        from py.api_server import parse_checkpoint_file
        result = parse_checkpoint_file(checkpoint_file)

        assert result is None

    def test_parse_corrupted_checkpoint_file(self, tmp_path):
        """测试：损坏的JSON文件返回None"""
        checkpoint_file = tmp_path / "corrupted.json"

        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            f.write("{ invalid json }")

        from py.api_server import parse_checkpoint_file
        result = parse_checkpoint_file(checkpoint_file)

        assert result is None


class TestProgressMessage:
    """进度消息生成测试"""

    def test_generate_progress_message_story(self):
        """测试：故事生成阶段的消息"""
        from py.api_server import generate_progress_message

        checkpoint = {'completed_steps': ['story']}
        message = generate_progress_message(checkpoint)

        assert '故事' in message or 'story' in message.lower()

    def test_generate_progress_message_images(self):
        """测试：图像生成阶段的消息"""
        from py.api_server import generate_progress_message

        checkpoint = {
            'completed_steps': ['story', 'images'],
            'images': {'completed': 3, 'total': 6}
        }
        message = generate_progress_message(checkpoint)

        assert '图像' in message or 'image' in message.lower()
        assert '3' in message and '6' in message

    def test_generate_progress_message_videos(self):
        """测试：视频生成阶段的消息"""
        from py.api_server import generate_progress_message

        checkpoint = {
            'completed_steps': ['story', 'images', 'videos'],
            'videos': {'completed': 2, 'total': 6}
        }
        message = generate_progress_message(checkpoint)

        assert '视频' in message or 'video' in message.lower()

    def test_generate_progress_message_composition(self):
        """测试：合成阶段的消息"""
        from py.api_server import generate_progress_message

        checkpoint = {
            'completed_steps': ['story', 'images', 'videos', 'composition']
        }
        message = generate_progress_message(checkpoint)

        assert '合成' in message or '完成' in message


@pytest.mark.asyncio
class TestIntegration:
    """集成测试：完整流程"""

    async def test_progress_updates_during_execution(self, tmp_path):
        """测试：执行过程中进度会更新"""
        # 这个测试需要实际运行任务，较为复杂
        # 可以通过模拟checkpoint文件的变化来测试
        pass

    async def test_log_file_updates(self, tmp_path):
        """测试：日志文件会实时更新"""
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
