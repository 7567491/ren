#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 调用封装。"""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from .config_loader import LoadedConfig


def _get_nested(cfg: Dict[str, Any], path: str) -> Any:
    value: Any = cfg
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value.get(part)
    return value


class LLMClient:
    def __init__(self, config: LoadedConfig, logger: Any, provider_choice: Any | None = None, dry_run: bool = False):
        self.config = config
        self.logger = logger
        self.dry_run = dry_run

        llm_cfg = config.merged.get("llm", {})
        providers = llm_cfg.get("providers", {})
        number_map = llm_cfg.get("number_map", {})
        default_provider = llm_cfg.get("default")

        if provider_choice is None:
            provider_choice = (config.user_config.get("llm", {}) or {}).get("provider")

        self.provider_key = self._resolve_provider(provider_choice, providers, number_map, default_provider)
        self.provider_cfg = providers.get(self.provider_key, {})
        self.api_key = self._resolve_api_key(self.provider_cfg)
        self.endpoint = self.provider_cfg.get("endpoint")
        self.model = self.provider_cfg.get("model")
        self.temperature = self.provider_cfg.get("temperature", 0.7)
        self.max_tokens = self.provider_cfg.get("max_tokens")
        self.timeout = self.provider_cfg.get("timeout_seconds", 60)

    def _resolve_provider(self, choice: Any, providers: Dict[str, Dict[str, Any]], number_map: Dict[Any, str], default_provider: str | None) -> str:
        if isinstance(choice, int) and choice in number_map:
            return number_map[choice]
        if isinstance(choice, str):
            if choice in providers:
                return choice
            if choice.isdigit() and int(choice) in number_map:
                return number_map[int(choice)]
        if default_provider and default_provider in providers:
            return default_provider
        if providers:
            return list(providers.keys())[0]
        raise ValueError("未配置可用的 LLM provider")

    def _resolve_api_key(self, provider_cfg: Dict[str, Any]) -> str:
        env_name = provider_cfg.get("api_key_env")
        if env_name:
            env_value = os.getenv(env_name)
            if env_value:
                return env_value

        config_path = provider_cfg.get("api_key_config")
        if config_path:
            nested = _get_nested(self.config.merged, config_path)
            if isinstance(nested, str) and nested.strip():
                return nested

        direct = provider_cfg.get("api_key")
        if isinstance(direct, str) and direct.strip():
            return direct

        raise ValueError(f"缺少 {provider_cfg.get('name', self.provider_key)} 的 API 密钥")

    async def generate(self, prompt: str, **kwargs) -> str:
        if self.dry_run:
            self.logger.info("LLM dry-run，返回占位文本")
            return f"[DRY RUN]\n{prompt}"

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.temperature),
        }
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        if "messages" in kwargs and isinstance(kwargs["messages"], list):
            payload["messages"] = kwargs["messages"]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            raise ValueError("LLM 响应缺少 choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not content:
            raise ValueError("LLM 响应缺少内容")

        self.logger.info(f"LLM({self.provider_key}) 调用成功")
        return content

    @staticmethod
    def fill_template(template: str, **kwargs) -> str:
        try:
            return template.format(**kwargs)
        except KeyError as exc:  # noqa: BLE001
            missing = exc.args[0]
            raise ValueError(f"提示词缺少变量: {missing}") from exc


__all__ = ["LLMClient"]
