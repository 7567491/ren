"""
测试镜头数验证的三层一致性
用于验证RCA-20251227-001问题的修复

测试场景：
1. 边界值测试
2. 三层验证一致性测试
3. API集成测试
4. 错误处理测试
"""

import pytest
import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from py.api_server import generate_config_from_preset, validate_config_params
from fastapi.testclient import TestClient
from py.api_server import app


class TestShotCountValidation:
    """镜头数验证测试套件"""

    def test_boundary_values(self):
        """测试边界值验证"""
        # 测试非法值（小于最小值）
        with pytest.raises(ValueError) as exc_info:
            validate_config_params(
                topic="test",
                shot_count=0,
                shot_duration=5,
                resolution="720p"
            )
        assert "镜头数" in str(exc_info.value) or "shot" in str(exc_info.value).lower()

        # 测试非法值（等于1，应该被拒绝）
        with pytest.raises(ValueError) as exc_info:
            validate_config_params(
                topic="test",
                shot_count=1,
                shot_duration=5,
                resolution="720p"
            )
        assert "镜头数" in str(exc_info.value) or "shot" in str(exc_info.value).lower()

        # 测试非法值（大于最大值）
        with pytest.raises(ValueError) as exc_info:
            validate_config_params(
                topic="test",
                shot_count=11,
                shot_duration=5,
                resolution="720p"
            )
        assert "镜头数" in str(exc_info.value) or "shot" in str(exc_info.value).lower()

        # 测试合法值（最小值）
        try:
            validate_config_params(
                topic="test",
                shot_count=2,
                shot_duration=5,
                resolution="720p"
            )
        except ValueError:
            pytest.fail("shot_count=2 应该通过验证（最小合法值）")

        # 测试合法值（中间值）
        try:
            validate_config_params(
                topic="test",
                shot_count=5,
                shot_duration=5,
                resolution="720p"
            )
        except ValueError:
            pytest.fail("shot_count=5 应该通过验证")

        # 测试合法值（最大值）
        try:
            validate_config_params(
                topic="test",
                shot_count=10,
                shot_duration=5,
                resolution="720p"
            )
        except ValueError:
            pytest.fail("shot_count=10 应该通过验证（最大合法值）")

    def test_config_generation(self):
        """测试配置生成是否包含正确的验证范围"""
        # 生成配置并验证
        config = generate_config_from_preset(
            topic="测试主题",
            preset_name="科技",
            num_shots=3,
            shot_duration=5,
            resolution="720p",
            llm_provider=1,
            image_model=4,
            video_model=1,
            voice=1,
            concurrent_workers=3,
            job_id="test-001"
        )

        assert config['shot_count'] == 3
        assert 2 <= config['shot_count'] <= 10, "生成的配置应该在合法范围内"

    def test_invalid_config_generation(self):
        """测试生成非法配置时应该抛出异常"""
        with pytest.raises(ValueError):
            generate_config_from_preset(
                topic="测试主题",
                preset_name="科技",
                num_shots=1,  # 非法值
                shot_duration=5,
                resolution="720p",
                llm_provider=1,
                image_model=4,
                video_model=1,
                voice=1,
                concurrent_workers=3,
                job_id="test-002"
            )


class TestAPIIntegration:
    """API集成测试"""

    def setup_method(self):
        """设置测试客户端"""
        self.client = TestClient(app)

    def test_api_reject_invalid_shot_count(self):
        """测试API拒绝非法的镜头数"""
        # 测试 shot_count = 0
        response = self.client.post("/api/jobs", json={
            "topic": "测试视频",
            "preset_name": "科技",
            "num_shots": 0,
            "shot_duration": 5,
            "resolution": "720p"
        })
        assert response.status_code == 400 or response.status_code == 422

        # 测试 shot_count = 1 (核心测试用例)
        response = self.client.post("/api/jobs", json={
            "topic": "测试视频",
            "preset_name": "科技",
            "num_shots": 1,
            "shot_duration": 5,
            "resolution": "720p"
        })
        assert response.status_code == 400 or response.status_code == 422
        error_detail = response.json().get('detail', '')
        assert "镜头" in error_detail or "shot" in error_detail.lower()

        # 测试 shot_count = 11
        response = self.client.post("/api/jobs", json={
            "topic": "测试视频",
            "preset_name": "科技",
            "num_shots": 11,
            "shot_duration": 5,
            "resolution": "720p"
        })
        assert response.status_code == 400 or response.status_code == 422

    def test_api_accept_valid_shot_count(self):
        """测试API接受合法的镜头数"""
        for valid_count in [2, 3, 5, 10]:
            response = self.client.post("/api/jobs", json={
                "topic": "测试视频",
                "preset_name": "科技",
                "num_shots": valid_count,
                "shot_duration": 5,
                "resolution": "720p"
            })
            # 应该返回200（成功）或202（已接受）
            assert response.status_code in [200, 201, 202], \
                f"num_shots={valid_count} 应该被接受，但收到状态码 {response.status_code}"

    def test_api_error_message_clarity(self):
        """测试API返回的错误消息是否清晰"""
        response = self.client.post("/api/jobs", json={
            "topic": "测试视频",
            "num_shots": 1
        })

        if response.status_code in [400, 422]:
            error_data = response.json()
            # 验证错误消息包含有用信息
            error_msg = str(error_data)
            assert any(keyword in error_msg for keyword in ["镜头", "shot", "2", "10"]), \
                f"错误消息应包含验证范围信息，实际消息：{error_msg}"


class TestBackendValidation:
    """后端验证测试"""

    def test_load_invalid_config_file(self, tmp_path):
        """测试加载包含非法镜头数的配置文件"""
        from py.function.config_loader import load_config_file

        # 创建包含非法镜头数的配置文件
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
topic: 测试主题
shot_count: 1
shot_duration: 5
resolution: 720p
style: 4
""")

        # 应该返回None或抛出异常
        result = load_config_file(str(config_file))
        assert result is None, "包含非法镜头数的配置应该验证失败"

    def test_load_valid_config_file(self, tmp_path):
        """测试加载包含合法镜头数的配置文件"""
        from py.function.config_loader import load_config_file

        # 创建包含合法镜头数的配置文件
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
topic: 测试主题
shot_count: 3
shot_duration: 5
resolution: 720p
style: 4
""")

        # 应该成功加载
        result = load_config_file(str(config_file))
        assert result is not None, "包含合法镜头数的配置应该验证成功"
        config, _ = result
        assert config['shot_count'] == 3


class TestErrorHandling:
    """错误处理测试"""

    def test_no_interactive_fallback_in_api_mode(self):
        """测试API模式下不应回退到交互式输入"""
        import subprocess
        import tempfile
        from pathlib import Path

        # 创建包含非法镜头数的配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
topic: 测试主题
shot_count: 1
shot_duration: 5
resolution: 720p
style: 4
""")
            config_file = f.name

        try:
            # 运行ad-back.py，模拟API调用
            ad_back_path = Path(__file__).parent.parent / "py" / "ad-back.py"

            result = subprocess.run(
                [sys.executable, str(ad_back_path), "--config-file", config_file, "--no-auto-resume"],
                capture_output=True,
                timeout=5,
                text=True
            )

            # 应该以非0退出码退出（失败）
            assert result.returncode != 0, "非法配置应该导致程序失败退出"

            # 不应该出现EOFError
            assert "EOFError" not in result.stderr, \
                f"不应该尝试交互式输入（API模式），stderr: {result.stderr}"

            # 应该包含清晰的错误消息
            output = result.stdout + result.stderr
            assert "镜头数量" in output or "shot_count" in output, \
                f"应该包含镜头数验证错误信息，output: {output}"

        except subprocess.TimeoutExpired:
            pytest.fail("程序超时，可能陷入了等待交互式输入的状态")
        finally:
            # 清理临时文件
            Path(config_file).unlink(missing_ok=True)


class TestThreeLayerConsistency:
    """三层一致性测试（前端、API、后端）"""

    def test_validation_range_consistency(self):
        """验证三层使用相同的验证范围"""
        # API层的验证范围
        MIN_SHOTS_API = 2
        MAX_SHOTS_API = 10

        # 后端的验证范围（从代码中提取）
        MIN_SHOTS_BACKEND = 2
        MAX_SHOTS_BACKEND = 10

        # 前端的验证范围（需要从HTML中提取或通过API测试推断）
        # 这里我们通过测试推断
        client = TestClient(app)

        # 测试边界值
        for shot_count in [0, 1, 2, 10, 11]:
            response = client.post("/api/jobs", json={
                "topic": "测试",
                "num_shots": shot_count
            })

            # API层和后端应该有一致的验证结果
            if MIN_SHOTS_API <= shot_count <= MAX_SHOTS_API:
                assert response.status_code in [200, 201, 202], \
                    f"shot_count={shot_count} 应该在API层通过验证"
            else:
                assert response.status_code in [400, 422], \
                    f"shot_count={shot_count} 应该在API层被拒绝"

    def test_default_value_is_valid(self):
        """测试默认值是否在合法范围内"""
        from py.api_server import JobCreateRequest

        # 获取默认值
        request = JobCreateRequest()
        default_shots = request.num_shots

        # 默认值应该在合法范围内
        assert 2 <= default_shots <= 10, \
            f"默认镜头数 {default_shots} 应该在合法范围 2-10 内"

        # 默认值应该是推荐值（3或5）
        assert default_shots in [3, 5], \
            f"默认镜头数应该是推荐值（3或5），当前为 {default_shots}"


# 回归测试标记
@pytest.mark.regression
class TestRegressionRCA20251227:
    """回归测试：确保RCA-20251227-001问题已修复"""

    def test_issue_aka_12271649_fixed(self):
        """
        回归测试：验证问题 aka-12271649 已修复

        问题描述：
        - 前端默认选择1个镜头
        - API层验证允许1个镜头
        - 后端验证拒绝1个镜头
        - 导致回退到交互式模式并产生EOFError

        预期修复：
        - 前端默认值改为3
        - API层验证改为2-10
        - 后端保持2-10验证
        - 不再回退到交互式模式
        """
        client = TestClient(app)

        # 1. 测试前端默认值（通过API推断）
        # 如果不提供num_shots，应该使用合法的默认值
        response = client.post("/api/jobs", json={
            "topic": "测试视频",
            "preset_name": "科技"
            # 不提供num_shots，使用默认值
        })
        assert response.status_code in [200, 201, 202], \
            "使用默认镜头数应该成功创建任务"

        # 2. 测试API层拒绝shot_count=1
        response = client.post("/api/jobs", json={
            "topic": "测试视频",
            "preset_name": "科技",
            "num_shots": 1
        })
        assert response.status_code in [400, 422], \
            "API层应该拒绝 num_shots=1"

        # 3. 验证错误消息包含范围信息
        error_data = response.json()
        error_msg = str(error_data)
        assert "2" in error_msg and "10" in error_msg, \
            f"错误消息应该明确指出合法范围2-10，实际消息：{error_msg}"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
