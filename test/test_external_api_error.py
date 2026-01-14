"""
测试 ExternalAPIError 异常类
遵循 TDD 原则：先写测试，后写实现
"""

import pytest
from py.exceptions.external_api_error import ExternalAPIError


class TestExternalAPIError:
    """测试 ExternalAPIError 异常类"""

    def test_basic_creation(self):
        """测试基本的异常创建"""
        error = ExternalAPIError(
            provider="wavespeed",
            message="API request failed",
            status_code=500
        )

        assert error.provider == "wavespeed"
        assert error.message == "API request failed"
        assert error.status_code == 500
        assert error.trace_id is None
        assert str(error) == "[wavespeed] API request failed (status: 500)"

    def test_with_trace_id(self):
        """测试带 trace_id 的异常"""
        error = ExternalAPIError(
            provider="minimax",
            message="TTS generation failed",
            status_code=429,
            trace_id="trace-12345"
        )

        assert error.provider == "minimax"
        assert error.trace_id == "trace-12345"
        assert "trace-12345" in str(error)

    def test_with_response_data(self):
        """测试带响应数据的异常"""
        response_data = {
            "error": "rate_limit_exceeded",
            "message": "Too many requests"
        }

        error = ExternalAPIError(
            provider="infinitetalk",
            message="Rate limit exceeded",
            status_code=429,
            response_data=response_data
        )

        assert error.response_data == response_data
        assert error.response_data["error"] == "rate_limit_exceeded"

    def test_with_original_exception(self):
        """测试带原始异常的错误"""
        original = ValueError("Invalid parameter")

        error = ExternalAPIError(
            provider="seedream",
            message="Parameter validation failed",
            status_code=400,
            original_exception=original
        )

        assert error.original_exception == original
        assert isinstance(error.original_exception, ValueError)

    def test_is_retryable_5xx(self):
        """测试 5xx 错误是否可重试"""
        error = ExternalAPIError(
            provider="test",
            message="Server error",
            status_code=500
        )

        assert error.is_retryable() is True

    def test_is_retryable_429(self):
        """测试 429 错误是否可重试"""
        error = ExternalAPIError(
            provider="test",
            message="Rate limited",
            status_code=429
        )

        assert error.is_retryable() is True

    def test_is_not_retryable_4xx(self):
        """测试其他 4xx 错误不可重试"""
        error = ExternalAPIError(
            provider="test",
            message="Bad request",
            status_code=400
        )

        assert error.is_retryable() is False

    def test_to_dict(self):
        """测试转换为字典"""
        error = ExternalAPIError(
            provider="wavespeed",
            message="API error",
            status_code=503,
            trace_id="trace-abc",
            response_data={"detail": "Service unavailable"}
        )

        error_dict = error.to_dict()

        assert error_dict["provider"] == "wavespeed"
        assert error_dict["message"] == "API error"
        assert error_dict["status_code"] == 503
        assert error_dict["trace_id"] == "trace-abc"
        assert error_dict["response_data"]["detail"] == "Service unavailable"
        assert error_dict["retryable"] is True

    def test_from_response(self):
        """测试从 HTTP 响应创建异常"""
        # 模拟一个 HTTP 响应对象
        class MockResponse:
            status_code = 500
            text = '{"error": "internal_error"}'
            headers = {"x-trace-id": "trace-xyz"}

            def json(self):
                return {"error": "internal_error"}

        response = MockResponse()

        error = ExternalAPIError.from_response(
            provider="test",
            response=response,
            message="Request failed"
        )

        assert error.provider == "test"
        assert error.status_code == 500
        assert error.trace_id == "trace-xyz"
        assert error.response_data["error"] == "internal_error"

    def test_inheritance_from_exception(self):
        """测试异常继承关系"""
        error = ExternalAPIError(
            provider="test",
            message="Test error",
            status_code=500
        )

        assert isinstance(error, Exception)

        # 测试可以被 try-except 捕获
        with pytest.raises(ExternalAPIError) as exc_info:
            raise error

        assert exc_info.value.provider == "test"
