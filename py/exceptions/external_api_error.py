"""
统一的外部 API 错误异常类
用于封装所有外部 API 调用的错误信息
"""

from typing import Optional, Dict, Any


class ExternalAPIError(Exception):
    """
    外部 API 错误异常

    用于统一处理所有外部 API（WaveSpeed、MiniMax、Infinitetalk 等）的错误
    """

    def __init__(
        self,
        provider: str,
        message: str,
        status_code: int,
        trace_id: Optional[str] = None,
        response_data: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        初始化外部 API 错误

        Args:
            provider: API 提供商名称（如 "wavespeed", "minimax", "infinitetalk"）
            message: 错误消息
            status_code: HTTP 状态码
            trace_id: 追踪 ID（用于日志关联）
            response_data: API 返回的响应数据
            original_exception: 原始异常对象（如有）
        """
        self.provider = provider
        self.message = message
        self.status_code = status_code
        self.trace_id = trace_id
        self.response_data = response_data or {}
        self.original_exception = original_exception

        # 构建异常消息
        error_msg = f"[{provider}] {message} (status: {status_code})"
        if trace_id:
            error_msg += f" [trace: {trace_id}]"

        super().__init__(error_msg)

    def is_retryable(self) -> bool:
        """
        判断该错误是否可重试

        Returns:
            True: 5xx 服务器错误或 429 限流错误可重试
            False: 其他 4xx 客户端错误不可重试
        """
        # 5xx 服务器错误可重试
        if 500 <= self.status_code < 600:
            return True

        # 429 限流错误可重试
        if self.status_code == 429:
            return True

        # 其他错误不可重试
        return False

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（用于 JSON 响应）

        Returns:
            包含错误信息的字典
        """
        return {
            "provider": self.provider,
            "message": self.message,
            "status_code": self.status_code,
            "trace_id": self.trace_id,
            "response_data": self.response_data,
            "retryable": self.is_retryable()
        }

    @classmethod
    def from_response(
        cls,
        provider: str,
        response: Any,
        message: str
    ) -> "ExternalAPIError":
        """
        从 HTTP 响应对象创建异常

        Args:
            provider: API 提供商
            response: HTTP 响应对象（需有 status_code, text, headers, json() 方法）
            message: 自定义错误消息

        Returns:
            ExternalAPIError 实例
        """
        status_code = response.status_code

        # 尝试从响应头获取 trace_id
        trace_id = None
        if hasattr(response, 'headers'):
            trace_id = response.headers.get('x-trace-id') or \
                      response.headers.get('X-Trace-Id') or \
                      response.headers.get('trace-id')

        # 尝试解析响应体为 JSON
        response_data = {}
        try:
            if hasattr(response, 'json'):
                response_data = response.json()
        except Exception:
            # JSON 解析失败，使用原始文本
            if hasattr(response, 'text'):
                response_data = {"raw_response": response.text}

        return cls(
            provider=provider,
            message=message,
            status_code=status_code,
            trace_id=trace_id,
            response_data=response_data
        )

    def __repr__(self) -> str:
        """开发调试时的字符串表示"""
        return (
            f"ExternalAPIError(provider={self.provider!r}, "
            f"status_code={self.status_code}, "
            f"trace_id={self.trace_id!r})"
        )
