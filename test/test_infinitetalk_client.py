"""
InfiniteTalkClient 测试用例

测试 Infinitetalk 唇同步客户端的功能
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from test.test_helpers import (
    assert_valid_url,
    assert_valid_duration,
    assert_valid_cost,
    assert_valid_infinitetalk_response
)


@pytest.mark.digital_human
@pytest.mark.unit
class TestInfiniteTalkClient:
    """InfiniteTalkClient 单元测试"""

    @pytest.fixture
    def client(self, api_keys):
        """创建 InfiniteTalkClient 实例"""
        from py.function.infinitetalk_client import InfiniteTalkClient
        return InfiniteTalkClient(api_key=api_keys["wavespeed"])

    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """测试客户端初始化"""
        assert client is not None
        assert hasattr(client, "api_key")
        assert hasattr(client, "base_url")
        assert client.base_url == "https://api.wavespeed.ai/api/v3"
        assert hasattr(client, "endpoint")
        assert client.endpoint == "wavespeed-ai/infinitetalk"

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_video_success(
        self,
        client,
        mock_infinitetalk_submit_response,
        mock_infinitetalk_status_response,
        mock_http_client
    ):
        """测试生成视频成功流程"""
        # 设置 mock 响应
        mock_http_client.set_response(
            "infinitetalk",
            mock_infinitetalk_submit_response
        )
        mock_http_client.set_response(
            "infinitetalk-task-789",
            mock_infinitetalk_status_response
        )

        # Mock submit 和 wait_for_result 方法
        with patch.object(client, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch.object(client, 'wait_for_result', new_callable=AsyncMock) as mock_wait, \
             patch.object(client, 'download', new_callable=AsyncMock) as mock_download:

            mock_submit.return_value = "infinitetalk-task-789"
            mock_wait.return_value = mock_infinitetalk_status_response["output"]
            mock_download.return_value = "/test/output/digital_human.mp4"

            # 调用生成视频方法
            result = await client.generate_video(
                image_url="https://example.com/avatar.png",
                audio_url="https://example.com/speech.mp3",
                resolution="720p",
                seed=42
            )

            # 验证结果
            assert "task_id" in result
            assert result["task_id"] == "infinitetalk-task-789"

            assert "video_url" in result
            assert_valid_url(result["video_url"])

            assert "video_path" in result
            assert "digital_human.mp4" in result["video_path"]
            assert "infinitetalk-task-789" in result["video_path"]

            assert "duration" in result
            assert_valid_duration(result["duration"])

            assert "cost" in result
            assert_valid_cost(result["cost"])

            # 验证调用参数
            mock_submit.assert_called_once()
            call_args = mock_submit.call_args
            assert call_args[0][0] == "wavespeed-ai/infinitetalk"
            payload = call_args[0][1]
            assert payload["image_url"] == "https://example.com/avatar.png"
            assert payload["audio_url"] == "https://example.com/speech.mp3"
            assert payload["resolution"] == "720p"
            assert payload["seed"] == 42

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_video_with_optional_params(self, client):
        """测试带可选参数的视频生成"""
        with patch.object(client, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch.object(client, 'wait_for_result', new_callable=AsyncMock) as mock_wait, \
             patch.object(client, 'download', new_callable=AsyncMock) as mock_download:

            mock_submit.return_value = "task-123"
            mock_wait.return_value = {
                "video_url": "https://example.com/video.mp4",
                "duration": 10.0
            }
            mock_download.return_value = "/test/output/video.mp4"

            # 调用带可选参数
            result = await client.generate_video(
                image_url="https://example.com/avatar.png",
                audio_url="https://example.com/speech.mp3",
                resolution="1080p",
                seed=100,
                mask_image="https://example.com/mask.png",
                prompt="高质量数字人"
            )

            # 验证 payload 包含可选参数
            payload = mock_submit.call_args[0][1]
            assert payload["resolution"] == "1080p"
            assert payload["seed"] == 100
            assert payload["mask_image"] == "https://example.com/mask.png"
            assert payload["prompt"] == "高质量数字人"

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_video_timeout(self, client):
        """测试视频生成超时"""
        with patch.object(client, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch.object(client, 'wait_for_result', new_callable=AsyncMock) as mock_wait:

            mock_submit.return_value = "task-timeout"
            # 模拟超时异常
            mock_wait.side_effect = TimeoutError("任务超时")

            # 应该抛出 TimeoutError
            with pytest.raises(TimeoutError):
                await client.generate_video(
                    image_url="https://example.com/avatar.png",
                    audio_url="https://example.com/speech.mp3"
                )

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_video_api_error(self, client):
        """测试 API 错误处理"""
        with patch.object(client, 'submit', new_callable=AsyncMock) as mock_submit:
            # 模拟 API 错误
            mock_submit.side_effect = Exception("API Error: 500 Internal Server Error")

            # 应该抛出异常
            with pytest.raises(Exception) as exc_info:
                await client.generate_video(
                    image_url="https://example.com/avatar.png",
                    audio_url="https://example.com/speech.mp3"
                )

            assert "API Error" in str(exc_info.value)

    def test_calculate_cost_720p(self, client):
        """测试 720p 成本计算"""
        # 60秒视频 @ 720p = 60 * $0.06 = $3.60
        cost = client._calculate_cost(duration=60.0, resolution="720p")
        assert cost == pytest.approx(3.60, rel=0.01)

        # 10秒视频
        cost = client._calculate_cost(duration=10.0, resolution="720p")
        assert cost == pytest.approx(0.60, rel=0.01)

    def test_calculate_cost_1080p(self, client):
        """测试 1080p 成本计算"""
        # 60秒视频 @ 1080p = 60 * $0.12 = $7.20
        cost = client._calculate_cost(duration=60.0, resolution="1080p")
        assert cost == pytest.approx(7.20, rel=0.01)

        # 10秒视频
        cost = client._calculate_cost(duration=10.0, resolution="1080p")
        assert cost == pytest.approx(1.20, rel=0.01)

    def test_calculate_cost_default(self, client):
        """测试默认分辨率成本计算"""
        # 未知分辨率应使用 720p 费率
        cost = client._calculate_cost(duration=10.0, resolution="unknown")
        assert cost == pytest.approx(0.60, rel=0.01)

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_submit_calls_correct_endpoint(self, client):
        """测试 submit 调用正确的端点"""
        with patch.object(client, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch.object(client, 'wait_for_result', new_callable=AsyncMock) as mock_wait, \
             patch.object(client, 'download', new_callable=AsyncMock) as mock_download:

            mock_submit.return_value = "task-123"
            mock_wait.return_value = {
                "video_url": "https://example.com/video.mp4",
                "duration": 10.0
            }
            mock_download.return_value = "/test/output/digital_human.mp4"

            await client.generate_video(
                image_url="https://example.com/avatar.png",
                audio_url="https://example.com/speech.mp3"
            )

            # 验证调用了正确的端点
            assert mock_submit.called
            endpoint = mock_submit.call_args[0][0]
            assert endpoint == "wavespeed-ai/infinitetalk"

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_wait_for_result_polling(self, client):
        """测试轮询等待结果"""
        with patch.object(client, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch.object(client, 'wait_for_result', new_callable=AsyncMock) as mock_wait, \
             patch.object(client, 'download', new_callable=AsyncMock):

            mock_submit.return_value = "task-polling"
            mock_wait.return_value = {"video_url": "https://example.com/video.mp4", "duration": 10.0}

            await client.generate_video(
                image_url="https://example.com/avatar.png",
                audio_url="https://example.com/speech.mp3"
            )

            # 验证 wait_for_result 被调用
            mock_wait.assert_called_once()
            call_args = mock_wait.call_args
            assert call_args[0][0] == "task-polling"
            # 验证超时参数
            assert "max_wait" in call_args[1]
            assert call_args[1]["max_wait"] == 600  # 10分钟
            assert "poll_interval" in call_args[1]
            assert call_args[1]["poll_interval"] == 5  # 5秒

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_download_video(self, client):
        """测试下载视频"""
        with patch.object(client, 'submit', new_callable=AsyncMock) as mock_submit, \
             patch.object(client, 'wait_for_result', new_callable=AsyncMock) as mock_wait, \
             patch.object(client, 'download', new_callable=AsyncMock) as mock_download:

            mock_submit.return_value = "task-download"
            mock_wait.return_value = {
                "video_url": "https://example.com/test-video.mp4",
                "duration": 12.5
            }
            expected_path = "/test/output/task-download/digital_human.mp4"
            mock_download.return_value = expected_path

            result = await client.generate_video(
                image_url="https://example.com/avatar.png",
                audio_url="https://example.com/speech.mp3"
            )

            # 验证 download 被调用
            mock_download.assert_called_once()
            call_args = mock_download.call_args
            assert call_args[0][0] == "https://example.com/test-video.mp4"
            # 验证目标路径格式（第二个位置参数）
            target_path = call_args[0][1] if len(call_args[0]) > 1 else None
            assert target_path is not None
            assert "digital_human.mp4" in str(target_path)

            # 验证返回的路径（download 返回的是 Path 对象的字符串形式）
            assert "digital_human.mp4" in result["video_path"]


@pytest.mark.digital_human
@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.slow
class TestInfiniteTalkClientRealAPI:
    """InfiniteTalkClient 真实 API 集成测试

    这些测试会调用真实的 WaveSpeed API，需要:
    1. 设置环境变量 WAVESPEED_API_KEY
    2. 设置环境变量 PYTEST_WAVESPEED_MOCK=0
    3. 准备好真实的 image_url 和 audio_url

    运行方式:
    PYTEST_WAVESPEED_MOCK=0 pytest test/test_infinitetalk_client.py -m real_api
    """

    @pytest.fixture
    def real_client(self, api_keys, use_mock):
        """创建真实 API 客户端"""
        if use_mock:
            pytest.skip("跳过真实 API 测试（PYTEST_WAVESPEED_MOCK=1）")

        from py.function.media_clients import InfiniteTalkClient
        return InfiniteTalkClient(api_key=api_keys["wavespeed"])

    @pytest.mark.asyncio
    async def test_real_api_generate_video(self, real_client):
        """测试真实 API 生成视频

        注意: 这个测试会产生实际费用（约 $0.60 for 10秒）
        """
        # 需要真实的图像和音频 URL
        # 这里使用 placeholder，实际测试时需要替换
        pytest.skip("需要真实的 image_url 和 audio_url")

        result = await real_client.generate_video(
            image_url="https://your-real-image-url.png",
            audio_url="https://your-real-audio-url.mp3",
            resolution="720p",
            seed=42
        )

        # 验证结果
        assert_valid_infinitetalk_response({
            "state": "completed",
            "output": {
                "video_url": result["video_url"],
                "duration": result["duration"]
            }
        })
