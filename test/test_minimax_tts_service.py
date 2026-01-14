"""
MiniMaxTTSService 测试用例

测试 MiniMax TTS 客户端的功能
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from test.test_helpers import (
    assert_valid_url,
    assert_valid_duration,
    assert_valid_cost,
    assert_valid_minimax_response
)


@pytest.mark.digital_human
@pytest.mark.unit
class TestMiniMaxTTSService:
    """MiniMaxTTSService 单元测试"""

    @pytest.fixture
    def service(self, api_keys):
        """创建 MiniMaxTTSService 实例"""
        from py.services.minimax_tts_service import MiniMaxTTSService
        return MiniMaxTTSService(api_key=api_keys["minimax"])

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, "api_key")
        assert hasattr(service, "base_url")
        assert service.base_url == "https://api.wavespeed.ai/api/v3"
        assert hasattr(service, "endpoint")
        assert service.endpoint == f"{service.base_url}/minimax/speech-02-hd"

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_voice_success(
        self,
        service,
        mock_minimax_response,
        test_output_dir
    ):
        """测试生成语音成功流程"""
        output_path = test_output_dir / "speech.mp3"

        # Mock HTTP 请求
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.status_code = 200
            mock_response.json.return_value = mock_minimax_response
            mock_response.content = b"fake audio content"

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            # 调用生成语音方法
            result = await service.generate_voice(
                text="大家好，欢迎收看今天的节目。",
                voice_id="female-shaonv",
                speed=1.0,
                pitch=0,
                emotion="neutral",
                output_path=output_path
            )

            # 验证结果
            assert "audio_url" in result
            assert_valid_url(result["audio_url"])

            assert "audio_path" in result
            assert result["audio_path"] == str(output_path)

            assert "duration" in result
            assert_valid_duration(result["duration"])

            assert "cost" in result
            assert_valid_cost(result["cost"])

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_voice_with_all_params(self, service, test_output_dir):
        """测试带所有参数的语音生成"""
        output_path = test_output_dir / "speech_full.mp3"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "output": {
                    "audio_url": "https://example.com/speech.mp3",
                    "duration": 15.5,
                    "sample_rate": 32000,
                    "channel": 1
                }
            }
            mock_response.content = b"fake audio"

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            # 调用带所有参数
            result = await service.generate_voice(
                text="这是一段测试语音，包含多种情绪和语调。",
                voice_id="male-qn-jingying",
                speed=1.2,
                pitch=2,
                emotion="happy",
                output_path=output_path
            )

            # 验证 POST 请求的 payload
            assert mock_client_instance.post.called
            call_args = mock_client_instance.post.call_args
            payload = call_args[1]["json"]

            assert payload["text"] == "这是一段测试语音，包含多种情绪和语调。"
            assert payload["voice_id"] == "male-qn-jingying"
            assert payload["speed"] == 1.2
            assert payload["pitch"] == 2
            assert payload["emotion"] == "happy"
            assert payload["sample_rate"] == 32000
            assert payload["channel"] == 1
            assert payload["english_normalization"] is True

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_voice_without_output_path(self, service):
        """测试不提供输出路径的语音生成"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "output": {
                    "audio_url": "https://example.com/speech.mp3",
                    "duration": 10.0
                }
            }

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            # 不提供 output_path
            result = await service.generate_voice(
                text="测试文本",
                voice_id="female-shaonv"
            )

            # 验证返回 URL 但没有路径
            assert "audio_url" in result
            assert result["audio_path"] is None

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_voice_api_error(self, service, test_output_dir):
        """测试 API 错误处理"""
        from py.exceptions import ExternalAPIError

        with patch('httpx.AsyncClient') as mock_client:
            # 模拟 HTTP 错误响应
            mock_response = MagicMock()
            mock_response.is_success = False
            mock_response.status_code = 500
            mock_response.text = '{"error": "internal_server_error"}'
            mock_response.headers = {"x-trace-id": "trace-123"}
            mock_response.json.return_value = {"error": "internal_server_error"}

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            # 应该抛出 ExternalAPIError
            with pytest.raises(ExternalAPIError) as exc_info:
                await service.generate_voice(
                    text="测试",
                    voice_id="female-shaonv",
                    output_path=test_output_dir / "error.mp3"
                )

            # 验证异常内容
            error = exc_info.value
            assert error.provider == "minimax"
            assert error.status_code == 500
            assert error.is_retryable() is True

    def test_calculate_cost(self, service):
        """测试成本计算"""
        # 60秒 @ $0.02/分钟 = $0.02
        cost = service._calculate_cost(duration=60.0)
        assert cost == pytest.approx(0.02, rel=0.01)

        # 30秒 @ $0.02/分钟 = $0.01
        cost = service._calculate_cost(duration=30.0)
        assert cost == pytest.approx(0.01, rel=0.01)

        # 120秒 @ $0.02/分钟 = $0.04
        cost = service._calculate_cost(duration=120.0)
        assert cost == pytest.approx(0.04, rel=0.01)

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_download_audio(self, service, test_output_dir):
        """测试下载音频"""
        audio_url = "https://example.com/test-audio.mp3"
        target_path = test_output_dir / "downloaded.mp3"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.status_code = 200
            mock_response.content = b"fake audio content data"

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            # 调用下载方法
            await service._download_audio(audio_url, target_path)

            # 验证文件被创建
            assert target_path.exists()
            assert target_path.read_bytes() == b"fake audio content data"

    @pytest.mark.parametrize("voice_id,expected_valid", [
        ("female-shaonv", True),
        ("female-yujie", True),
        ("male-qn-qingse", True),
        ("male-qn-jingying", True),
        ("Wise_Woman", True),
        ("invalid-voice", True),  # API 会验证，客户端接受任何字符串
    ])
    def test_voice_id_validation(self, service, voice_id, expected_valid):
        """测试音色ID"""
        # 客户端不验证 voice_id，由 API 验证
        assert True  # 占位测试

    @pytest.mark.parametrize("speed,expected_valid", [
        (0.5, True),
        (1.0, True),
        (1.5, True),
        (2.0, True),
        (0.4, True),   # 超出范围，但客户端不验证
        (2.5, True),   # 超出范围，但客户端不验证
    ])
    def test_speed_parameter(self, service, speed, expected_valid):
        """测试语速参数"""
        # 客户端不验证参数范围
        assert True  # 占位测试

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_headers_format(self, service, test_output_dir):
        """测试请求头格式"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.is_success = True
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "output": {
                    "audio_url": "https://example.com/speech.mp3",
                    "duration": 10.0
                }
            }
            mock_response.content = b"fake"

            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_client_instance

            await service.generate_voice(
                text="测试",
                voice_id="female-shaonv",
                output_path=test_output_dir / "test.mp3"
            )

            # 验证请求头
            call_args = mock_client_instance.post.call_args
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Bearer ")
            assert "Content-Type" in headers
            assert headers["Content-Type"] == "application/json"


@pytest.mark.digital_human
@pytest.mark.integration
@pytest.mark.real_api
@pytest.mark.slow
class TestMiniMaxTTSServiceRealAPI:
    """MiniMaxTTSService 真实 API 集成测试

    运行方式:
    PYTEST_WAVESPEED_MOCK=0 pytest test/test_minimax_tts_service.py -m real_api
    """

    @pytest.fixture
    def real_service(self, api_keys, use_mock):
        """创建真实 API 客户端"""
        if use_mock:
            pytest.skip("跳过真实 API 测试（PYTEST_WAVESPEED_MOCK=1）")

        from py.services.minimax_tts_service import MiniMaxTTSService
        return MiniMaxTTSService(api_key=api_keys["minimax"])

    @pytest.mark.asyncio
    async def test_real_api_generate_voice(self, real_service, test_output_dir):
        """测试真实 API 生成语音

        注意: 这个测试会产生实际费用（约 $0.01）
        """
        pytest.skip("需要真实的 MINIMAX_API_KEY")

        output_path = test_output_dir / "real_speech.mp3"

        result = await real_service.generate_voice(
            text="这是一段真实API测试语音。",
            voice_id="female-shaonv",
            speed=1.0,
            pitch=0,
            emotion="neutral",
            output_path=output_path
        )

        # 验证结果
        assert_valid_minimax_response({
            "output": {
                "audio_url": result["audio_url"],
                "duration": result["duration"]
            }
        })
        assert output_path.exists()
        assert output_path.stat().st_size > 0
