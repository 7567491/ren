"""
DigitalHumanService 测试用例

测试数字人服务编排的完整流程
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from test.test_helpers import (
    assert_valid_url,
    assert_valid_duration,
    assert_valid_cost
)


@pytest.mark.digital_human
@pytest.mark.unit
class TestDigitalHumanService:
    """DigitalHumanService 单元测试"""

    @pytest.fixture
    def service(self, api_keys):
        """创建 DigitalHumanService 实例"""
        from py.services.digital_human_service import DigitalHumanService
        svc = DigitalHumanService(
            wavespeed_key=api_keys["wavespeed"],
            minimax_key=api_keys["minimax"]
        )
        svc._safe_fetch_balance = AsyncMock(return_value=None)  # type: ignore[attr-defined]
        return svc

    def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service is not None
        assert hasattr(service, "avatar_client")
        assert hasattr(service, "voice_client")
        assert hasattr(service, "infinitetalk_client")
        assert hasattr(service, "task_manager")

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_digital_human_prompt_mode(
        self,
        service,
        test_output_dir,
        mock_seedream_response,
        mock_minimax_response,
        mock_infinitetalk_status_response
    ):
        """测试 prompt 模式生成数字人"""
        job_id = "test-job-001"

        # Mock 各个客户端的方法
        with patch.object(service.avatar_client, 'generate_images', new_callable=AsyncMock) as mock_avatar, \
             patch.object(service.voice_client, 'generate_voice', new_callable=AsyncMock) as mock_voice, \
             patch.object(service.infinitetalk_client, 'generate_video', new_callable=AsyncMock) as mock_video, \
             patch.object(service.task_manager, 'update_status') as mock_update_status:

            # 设置 mock 返回值
            mock_avatar.return_value = [{
                "url": "https://example.com/avatar.png",
                "width": 1024,
                "height": 1024
            }]

            mock_voice.return_value = {
                "audio_url": "https://example.com/speech.mp3",
                "audio_path": str(test_output_dir / "speech.mp3"),
                "duration": 12.5,
                "cost": 0.025
            }

            mock_video.return_value = {
                "task_id": "infinitetalk-task-789",
                "video_url": "https://example.com/digital_human.mp4",
                "video_path": str(test_output_dir / "digital_human.mp4"),
                "duration": 12.5,
                "cost": 0.75
            }

            # 调用生成方法
            result = await service.generate_digital_human(
                job_id=job_id,
                avatar_mode="prompt",
                avatar_prompt="专业女性播音员，微笑，正面照",
                speech_text="大家好，欢迎收看今天的节目。",
                voice_id="female-shaonv",
                resolution="720p",
                speed=1.0,
                pitch=0,
                emotion="neutral"
            )

            # 验证结果
            assert result["job_id"] == job_id
            assert result["status"] == "finished"
            assert_valid_url(result["avatar_url"])
            assert_valid_url(result["audio_url"])
            assert_valid_url(result["video_url"])
            assert_valid_cost(result["cost"])
            assert result["cost"] > 0
            assert "trace_id" in result and result["trace_id"].startswith("trace-")
            assert "logs" in result and result["logs"]

            # 验证 avatar_client 被调用
            mock_avatar.assert_called_once()
            call_args = mock_avatar.call_args
            assert "专业女性播音员" in call_args[1]["prompts"][0]

            # 验证 voice_client 被调用
            mock_voice.assert_called_once()
            call_args = mock_voice.call_args
            assert call_args[1]["text"] == "大家好，欢迎收看今天的节目。"
            assert call_args[1]["voice_id"] == "female-shaonv"

            # 验证 infinitetalk_client 被调用
            mock_video.assert_called_once()
            call_args = mock_video.call_args
            assert call_args[1]["image_url"] == "https://example.com/avatar.png"
            assert call_args[1]["audio_url"] == "https://example.com/speech.mp3"
            assert call_args[1]["resolution"] == "720p"

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_digital_human_upload_mode(self, service, test_output_dir):
        """测试 upload 模式生成数字人"""
        job_id = "test-job-002"
        upload_path = str(test_output_dir / "uploaded_avatar.png")

        # 创建测试文件
        (test_output_dir / "uploaded_avatar.png").write_bytes(b"fake image data")

        with patch.object(service, '_handle_avatar_upload', new_callable=AsyncMock) as mock_upload, \
             patch.object(service.voice_client, 'generate_voice', new_callable=AsyncMock) as mock_voice, \
             patch.object(service.infinitetalk_client, 'generate_video', new_callable=AsyncMock) as mock_video, \
             patch.object(service.task_manager, 'update_status'):

            mock_upload.return_value = "https://example.com/uploaded_avatar.png"
            mock_voice.return_value = {
                "audio_url": "https://example.com/speech.mp3",
                "audio_path": str(test_output_dir / "speech.mp3"),
                "duration": 10.0,
                "cost": 0.02
            }
            mock_video.return_value = {
                "task_id": "video-task",
                "video_url": "https://example.com/video.mp4",
                "video_path": str(test_output_dir / "video.mp4"),
                "duration": 10.0,
                "cost": 0.60
            }

            result = await service.generate_digital_human(
                job_id=job_id,
                avatar_mode="upload",
                avatar_upload_path=upload_path,
                speech_text="测试文本",
                voice_id="female-shaonv"
            )

            # 验证 upload 被调用
            mock_upload.assert_called_once()
            upload_call = mock_upload.call_args
            assert upload_call[0][0] == job_id
            assert upload_call[0][1] == upload_path
            # upload 模式下不应该调用头像生成 API（因为直接使用上传的文件）

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_digital_human_with_optional_params(self, service, test_output_dir):
        """测试带可选参数的生成"""
        job_id = "test-job-003"

        with patch.object(service.avatar_client, 'generate_images', new_callable=AsyncMock) as mock_avatar, \
             patch.object(service.voice_client, 'generate_voice', new_callable=AsyncMock) as mock_voice, \
             patch.object(service.infinitetalk_client, 'generate_video', new_callable=AsyncMock) as mock_video, \
             patch.object(service.task_manager, 'update_status'):

            mock_avatar.return_value = [{"url": "https://example.com/avatar.png"}]
            mock_voice.return_value = {
                "audio_url": "https://example.com/speech.mp3",
                "duration": 15.0,
                "cost": 0.03
            }
            mock_video.return_value = {
                "task_id": "video-task",
                "video_url": "https://example.com/video.mp4",
                "video_path": str(test_output_dir / "video.mp4"),
                "duration": 15.0,
                "cost": 1.80
            }

            result = await service.generate_digital_human(
                job_id=job_id,
                avatar_mode="prompt",
                avatar_prompt="测试头像",
                speech_text="测试文本",
                voice_id="male-qn-jingying",
                resolution="1080p",
                speed=1.2,
                pitch=2,
                emotion="happy",
                seed=100,
                mask_image="https://example.com/mask.png"
            )

            # 验证可选参数被传递
            voice_call = mock_voice.call_args[1]
            assert voice_call["speed"] == 1.2
            assert voice_call["pitch"] == 2
            assert voice_call["emotion"] == "happy"

            video_call = mock_video.call_args[1]
            assert video_call["resolution"] == "1080p"
            assert video_call["seed"] == 100
            assert video_call["mask_image"] == "https://example.com/mask.png"

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_generate_digital_human_error_handling(self, service):
        """测试错误处理"""
        job_id = "test-job-error"

        with patch.object(service.avatar_client, 'generate_images', new_callable=AsyncMock) as mock_avatar, \
             patch.object(service.task_manager, 'update_status') as mock_update_status:

            # 模拟头像生成失败
            mock_avatar.side_effect = Exception("头像生成失败")

            with pytest.raises(Exception) as exc_info:
                await service.generate_digital_human(
                    job_id=job_id,
                    avatar_mode="prompt",
                    avatar_prompt="测试",
                    speech_text="测试"
                )

            assert "头像生成失败" in str(exc_info.value)

            # 验证任务状态更新为失败
            update_calls = mock_update_status.call_args_list
            assert any("failed" in str(call) for call in update_calls)

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_cost_calculation(self, service, test_output_dir):
        """测试成本计算"""
        job_id = "test-job-cost"

        with patch.object(service.avatar_client, 'generate_images', new_callable=AsyncMock) as mock_avatar, \
             patch.object(service.voice_client, 'generate_voice', new_callable=AsyncMock) as mock_voice, \
             patch.object(service.infinitetalk_client, 'generate_video', new_callable=AsyncMock) as mock_video, \
             patch.object(service.task_manager, 'update_status'):

            mock_avatar.return_value = [{"url": "https://example.com/avatar.png"}]
            mock_voice.return_value = {
                "audio_url": "https://example.com/speech.mp3",
                "duration": 60.0,
                "cost": 0.02  # MiniMax: $0.02/分钟
            }
            mock_video.return_value = {
                "task_id": "video-task",
                "video_url": "https://example.com/video.mp4",
                "video_path": str(test_output_dir / "video.mp4"),
                "duration": 60.0,
                "cost": 3.60  # Infinitetalk 720p: $0.06/秒 * 60秒
            }

            result = await service.generate_digital_human(
                job_id=job_id,
                avatar_mode="prompt",
                avatar_prompt="测试",
                speech_text="测试文本" * 100  # 长文本
            )

            # 总成本 = Seedream($0.03) + MiniMax($0.02) + Infinitetalk($3.60)
            expected_cost = 0.03 + 0.02 + 3.60
            assert result["cost"] == pytest.approx(expected_cost, rel=0.01)

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_actual_cost_uses_balance_difference(self, service, test_output_dir):
        """测试余额差额作为实际成本写入"""
        job_id = "test-job-billing"
        service._safe_fetch_balance = AsyncMock(side_effect=[120.0, 118.4])  # type: ignore[attr-defined]

        with patch.object(service.avatar_client, 'generate_images', new_callable=AsyncMock) as mock_avatar, \
             patch.object(service.voice_client, 'generate_voice', new_callable=AsyncMock) as mock_voice, \
             patch.object(service.infinitetalk_client, 'generate_video', new_callable=AsyncMock) as mock_video, \
             patch.object(service.task_manager, 'update_status'):

            mock_avatar.return_value = [{"url": "https://example.com/avatar.png"}]
            mock_voice.return_value = {
                "audio_url": "https://example.com/speech.mp3",
                "duration": 10.0,
                "cost": 0.02
            }
            mock_video.return_value = {
                "task_id": "video-task",
                "video_url": "https://example.com/video.mp4",
                "video_path": str(test_output_dir / "video.mp4"),
                "duration": 10.0,
                "cost": 0.60
            }

            result = await service.generate_digital_human(
                job_id=job_id,
                avatar_mode="prompt",
                avatar_prompt="测试",
                speech_text="测试文本"
            )

        billing = result.get("billing") or {}
        assert billing.get("balance_before") == pytest.approx(120.0)
        assert billing.get("balance_after") == pytest.approx(118.4)
        assert billing.get("actual_cost") == pytest.approx(1.6, rel=0.01)
        assert result["cost"] == pytest.approx(1.6, rel=0.01)

    @pytest.mark.asyncio
    async def test_handle_avatar_upload_with_local_file(self, api_keys, tmp_path):
        from py.services.digital_human_service import DigitalHumanService
        from py.services.storage_service import StorageService

        storage = StorageService(output_root=tmp_path)
        service = DigitalHumanService(
            wavespeed_key=api_keys['wavespeed'],
            minimax_key=api_keys['minimax'],
            storage_service=storage,
        )

        source = tmp_path / 'source.png'
        source.write_bytes(b'avatar-data')
        target = storage.prepare_task_paths('aka-test-upload-local').avatar_path

        url = await service._handle_avatar_upload("aka-test-upload-local", str(source), target)

        assert target.exists()
        assert target.read_bytes() == b'avatar-data'
        assert url.endswith('/output/aka-test-upload-local/avatar.png')

    @pytest.mark.asyncio
    async def test_handle_avatar_upload_with_remote_url(self, api_keys, tmp_path):
        from py.services.digital_human_service import DigitalHumanService
        from py.services.storage_service import StorageService

        storage = StorageService(output_root=tmp_path)
        service = DigitalHumanService(
            wavespeed_key=api_keys['wavespeed'],
            minimax_key=api_keys['minimax'],
            storage_service=storage,
        )

        target = storage.prepare_task_paths('aka-test-upload-remote').avatar_path
        fake_content = b'remote-avatar'

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.content = fake_content
        mock_response.status_code = 200

        client_mock = AsyncMock()
        client_mock.get.return_value = mock_response

        ctx_mock = AsyncMock()
        ctx_mock.__aenter__.return_value = client_mock

        with patch('py.services.digital_human_service.httpx.AsyncClient', return_value=ctx_mock):
            url = await service._handle_avatar_upload(
                'aka-test-upload-remote',
                'https://cdn.example.com/avatar.png',
                target,
            )

        assert target.read_bytes() == fake_content
        client_mock.get.assert_called_once()
        assert client_mock.get.call_args[0][0] == 'https://cdn.example.com/avatar.png'
        assert url.endswith('/output/aka-test-upload-remote/avatar.png')



@pytest.mark.digital_human
@pytest.mark.integration
class TestDigitalHumanServiceIntegration:
    """DigitalHumanService 集成测试"""

    @pytest.mark.asyncio
    @pytest.mark.mock
    async def test_full_pipeline_flow(self, api_keys, test_output_dir):
        """测试完整流程"""
        from py.services.digital_human_service import DigitalHumanService

        service = DigitalHumanService(
            wavespeed_key=api_keys["wavespeed"],
            minimax_key=api_keys["minimax"]
        )
        service._safe_fetch_balance = AsyncMock(return_value=None)  # type: ignore[attr-defined]

        job_id = "integration-test-001"

        with patch.object(service.avatar_client, 'generate_images', new_callable=AsyncMock) as mock_avatar, \
             patch.object(service.voice_client, 'generate_voice', new_callable=AsyncMock) as mock_voice, \
             patch.object(service.infinitetalk_client, 'generate_video', new_callable=AsyncMock) as mock_video, \
             patch.object(service.task_manager, 'update_status') as mock_update_status:

            mock_avatar.return_value = [{"url": "https://example.com/avatar.png"}]
            mock_voice.return_value = {
                "audio_url": "https://example.com/speech.mp3",
                "audio_path": str(test_output_dir / "speech.mp3"),
                "duration": 10.0,
                "cost": 0.02
            }
            mock_video.return_value = {
                "task_id": "video-task",
                "video_url": "https://example.com/video.mp4",
                "video_path": str(test_output_dir / "video.mp4"),
                "duration": 10.0,
                "cost": 0.60
            }

            result = await service.generate_digital_human(
                job_id=job_id,
                avatar_mode="prompt",
                avatar_prompt="测试头像",
                speech_text="这是一段测试文本。"
            )

            # 验证完整流程
            assert result["status"] == "finished"
            assert "avatar_url" in result
            assert "audio_url" in result
            assert "video_url" in result

            # 验证状态更新顺序
            status_updates = [call[0][1] for call in mock_update_status.call_args_list]
            assert "avatar_generating" in status_updates
            assert "avatar_ready" in status_updates
            assert "speech_generating" in status_updates
            assert "speech_ready" in status_updates
            assert "video_rendering" in status_updates
            assert "finished" in status_updates
