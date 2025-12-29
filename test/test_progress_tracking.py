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

    def test_calculate_progress_assets_only(self):
        """测试：资产准备完成，进度应为10%"""
        checkpoint = {'completed_steps': ['assets']}
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == pytest.approx(0.10, rel=0, abs=1e-6)

    def test_calculate_progress_story_stage(self):
        """测试：资产+剧本完成，进度应为20%"""
        checkpoint = {'completed_steps': ['assets', 'story']}
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == pytest.approx(0.20, rel=0, abs=1e-6)

    def test_calculate_progress_story_without_assets_but_character_reference(self):
        """测试：旧checkpoint缺少assets但已完成角色参考，仍应算20%"""
        checkpoint = {
            'completed_steps': ['story'],
            'stages': {'character_reference': True}
        }
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == pytest.approx(0.20, rel=0, abs=1e-6)

    def test_calculate_progress_story_and_images(self):
        """测试：完成图像阶段，进度应为50%"""
        checkpoint = {'completed_steps': ['assets', 'story', 'images']}
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == pytest.approx(0.50, rel=0, abs=1e-6)

    def test_calculate_progress_all_but_composition(self):
        """测试：完成到视频阶段，进度应为90%"""
        checkpoint = {'completed_steps': ['assets', 'story', 'images', 'videos']}
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == pytest.approx(0.90, rel=0, abs=1e-6)

    def test_calculate_progress_complete(self):
        """测试：全部完成，进度应为1.0"""
        checkpoint = {
            'completed_steps': ['assets', 'story', 'images', 'videos', 'audio_subtitle', 'composition']
        }
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == pytest.approx(1.0, rel=0, abs=1e-6)

    def test_calculate_progress_with_details(self):
        """测试：带有详细信息的checkpoint"""
        checkpoint = {
            'completed_steps': ['assets', 'story'],
            'images': {'completed': 3, 'total': 6},
            'videos': {'completed': 0, 'total': 6}
        }
        # 基础进度0.20 + 图像子进度0.30*(3/6) = 0.20 + 0.15 = 0.35
        progress = calculate_progress_from_checkpoint(checkpoint, detailed=True)
        assert 0.34 <= progress <= 0.36

    def test_calculate_progress_invalid_checkpoint(self):
        """测试：无效checkpoint返回0"""
        progress = calculate_progress_from_checkpoint({})
        assert progress == 0.0

    def test_calculate_progress_unknown_steps(self):
        """测试：包含未知步骤的checkpoint"""
        checkpoint = {
            'completed_steps': ['story', 'unknown_step', 'images'],
            'stages': {'character_reference': True}
        }
        # 应该只计数已知步骤: assets(来自stages), story, images
        progress = calculate_progress_from_checkpoint(checkpoint)
        assert progress == pytest.approx(0.50, rel=0, abs=1e-6)


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

        assert ('剧本' in message) or ('故事' in message) or ('story' in message.lower())

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

        assert ('旁白' in message) or ('字幕' in message) or ('audio' in message.lower())

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
